import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { ApiError } from '@/lib/api'
import type { HistoryDetail, RatedPoint } from '@/lib/types'
import { renderWithProviders } from '@/test/utils'
import { HistoryDetailPage } from './HistoryDetailPage'

const api = vi.hoisted(() => ({ historyItem: vi.fn(), rate: vi.fn() }))
vi.mock('@/lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api')>()),
  api,
}))
vi.mock('@/lib/supabase', () => ({ supabase: { auth: {} } }))

const point = (id: string, rank: number, rating: number | null): RatedPoint => ({
  point_id: id, rank, name: `Point ${id}`, location_text: `Where ${id}`, image_url: null,
  image_attribution: null, instructions: ['Press gently.'], duration: null, pressure: null, rating,
})
const DETAIL: HistoryDetail = {
  attempt_id: 'a1', created_at: '2026-11-01T09:30:00Z', symptom: 'Invented tension',
  outcome: 'recommended', clarification_question: 'Where exactly?', clarification_answer: 'Temples',
  points: [point('LI4', 1, 4), point('PC6', 2, null), point('HT7', 3, null)],
}

function renderAt(id: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/history/:attemptId" element={<HistoryDetailPage />} />
    </Routes>,
    { route: `/history/${id}` },
  )
}

beforeEach(() => vi.clearAllMocks())

test('shows the points with the saved ratings and the clarification', async () => {
  api.historyItem.mockResolvedValue(DETAIL)
  renderAt('a1')

  expect(await screen.findByRole('heading', { name: 'For “Invented tension”' })).toBeInTheDocument()
  expect(api.historyItem).toHaveBeenCalledWith('a1')
  expect(screen.getByText('Where exactly?')).toBeInTheDocument()
  expect(screen.getByText('Temples')).toBeInTheDocument()
  const li4 = screen.getByRole('article', { name: 'Point LI4' })
  expect(within(li4).getByRole('radio', { name: '4 stars' })).toBeChecked()
  const pc6 = screen.getByRole('article', { name: 'Point PC6' })
  expect(within(pc6).queryByRole('radio', { checked: true })).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'All history' })).toHaveAttribute('href', '/history')
})

test('a point can be rated or re-rated from history', async () => {
  api.historyItem.mockResolvedValue(DETAIL)
  api.rate.mockResolvedValue({ attempt_id: 'a1', point_id: 'LI4', rating: 2 })
  renderAt('a1')

  const li4 = await screen.findByRole('article', { name: 'Point LI4' })
  await userEvent.click(within(li4).getByRole('radio', { name: '2 stars' }))
  expect(api.rate).toHaveBeenCalledWith('a1', 'LI4', 2)
  expect(await within(li4).findByText('Thanks — saved')).toBeInTheDocument()
})

test('explains attempts without points', async () => {
  api.historyItem.mockResolvedValue({ ...DETAIL, outcome: 'no_match', points: [] })
  renderAt('a1')
  expect(await screen.findByText(/couldn't find suitable acupressure points/)).toBeInTheDocument()
  expect(screen.queryByRole('article')).not.toBeInTheDocument()
})

test('an unknown attempt shows the message without a retry', async () => {
  api.historyItem.mockRejectedValue(
    new ApiError(404, { code: 'not_found', message: "We couldn't find that recommendation.", retryable: false }),
  )
  renderAt('missing')
  expect(await screen.findByText("We couldn't find that recommendation.")).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
})
