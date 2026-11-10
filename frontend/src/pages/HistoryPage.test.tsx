import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiError } from '@/lib/api'
import type { HistoryItem } from '@/lib/types'
import { renderWithProviders } from '@/test/utils'
import { HistoryPage } from './HistoryPage'

const api = vi.hoisted(() => ({ history: vi.fn() }))
vi.mock('@/lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api')>()),
  api,
}))
vi.mock('@/lib/supabase', () => ({ supabase: { auth: {} } }))

const item = (id: string, overrides: Partial<HistoryItem> = {}): HistoryItem => ({
  attempt_id: id, created_at: '2026-11-01T09:30:00Z', symptom: `Invented symptom ${id}`,
  outcome: 'no_match', points: [], ...overrides,
})

beforeEach(() => vi.clearAllMocks())

test('lists past attempts with outcome, points and ratings, linking to the detail', async () => {
  api.history.mockResolvedValue({
    has_more: false,
    items: [
      item('a1', {
        outcome: 'recommended',
        points: [
          { point_id: 'LI4', name: 'Hegu', rating: 4 },
          { point_id: 'PC6', name: 'Neiguan', rating: null },
          { point_id: 'HT7', name: 'Shenmen', rating: null },
        ],
      }),
      item('a2', { outcome: 'clarification_needed' }),
    ],
  })
  renderWithProviders(<HistoryPage />, { route: '/history' })

  const first = (await screen.findByText('“Invented symptom a1”')).closest('a')!
  expect(first).toHaveAttribute('href', '/history/a1')
  expect(within(first).getByText('Three points')).toBeInTheDocument()
  const points = within(first).getAllByRole('listitem').map((li) => li.textContent)
  expect(points).toEqual(['Hegu★ 4 of 5', 'Neiguan· not rated', 'Shenmen· not rated'])
  expect(screen.getByText('Needed more detail')).toBeInTheDocument()
  expect(api.history).toHaveBeenCalledWith(0, 20)
})

test('loads more pages on request', async () => {
  api.history
    .mockResolvedValueOnce({ has_more: true, items: [item('a1')] })
    .mockResolvedValueOnce({ has_more: false, items: [item('a2')] })
  renderWithProviders(<HistoryPage />, { route: '/history' })

  await userEvent.click(await screen.findByRole('button', { name: 'Show more' }))
  expect(await screen.findByText('“Invented symptom a2”')).toBeInTheDocument()
  expect(api.history).toHaveBeenLastCalledWith(20, 20)
  expect(screen.queryByRole('button', { name: 'Show more' })).not.toBeInTheDocument()
})

test('shows an empty state with a way to find points', async () => {
  api.history.mockResolvedValue({ has_more: false, items: [] })
  renderWithProviders(<HistoryPage />, { route: '/history' })
  expect(await screen.findByRole('heading', { name: 'Nothing here yet' })).toBeInTheDocument()
  expect(screen.getAllByRole('link', { name: 'Find points' }).length).toBeGreaterThan(0)
})

test('shows the error with a retry', async () => {
  api.history
    .mockRejectedValueOnce(new ApiError(502, { code: 'internal_error', message: 'Something went wrong.', retryable: true }))
    .mockResolvedValueOnce({ has_more: false, items: [item('a1')] })
  renderWithProviders(<HistoryPage />, { route: '/history' })

  expect(await screen.findByText('Something went wrong.')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByText('“Invented symptom a1”')).toBeInTheDocument()
})
