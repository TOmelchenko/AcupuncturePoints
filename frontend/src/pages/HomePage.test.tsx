import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiError } from '@/lib/api'
import type { RecommendedPoint } from '@/lib/types'
import { renderWithProviders } from '@/test/utils'
import { HomePage } from './HomePage'

const api = vi.hoisted(() => ({ recommend: vi.fn(), clarify: vi.fn(), rate: vi.fn() }))
vi.mock('@/lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api')>()),
  api,
}))
vi.mock('@/lib/supabase', () => ({ supabase: { auth: {} } }))

const point = (id: string, rank: number): RecommendedPoint => ({
  point_id: id, rank, name: `Point ${id}`, location_text: `Where ${id}`, image_url: null,
  image_attribution: null, instructions: ['Press gently.'], duration: null, pressure: null,
})
const RESULT = { outcome: 'recommended', attempt_id: 'a1', points: [point('LI4', 1), point('PC6', 2), point('HT7', 3)] }

beforeEach(() => vi.clearAllMocks())

async function submit(text: string) {
  await userEvent.type(screen.getByLabelText('Describe your symptom'), text)
  await userEvent.click(screen.getByRole('button', { name: 'Find points' }))
}

test('shows the introduction, disclaimer and symptom form', () => {
  renderWithProviders(<HomePage />)
  expect(screen.getByRole('heading', { name: 'How are you feeling today?' })).toBeInTheDocument()
  expect(screen.getByText(/not a diagnosis/)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Three points to try' })).toBeInTheDocument()
})

test('validates the symptom before sending', async () => {
  renderWithProviders(<HomePage />)
  await submit('ok')
  expect(await screen.findByText('Please describe your symptom in a few words.')).toBeInTheDocument()
  expect(api.recommend).not.toHaveBeenCalled()
})

test('shows a loading state, then three recommendations with the disclaimer', async () => {
  let resolve: (value: unknown) => void = () => {}
  api.recommend.mockReturnValue(new Promise((r) => (resolve = r)))
  renderWithProviders(<HomePage />)

  await submit('tension headache')

  expect(await screen.findByRole('status')).toHaveTextContent('Finding points')
  expect(screen.getByRole('button', { name: 'Finding points…' })).toBeDisabled()
  resolve(RESULT)
  expect(await screen.findByRole('heading', { name: 'For “tension headache”' })).toBeInTheDocument()
  expect(screen.getByText('Point LI4')).toBeInTheDocument()
  expect(screen.getAllByText(/not a diagnosis/)).toHaveLength(2)
  expect(api.recommend).toHaveBeenCalledWith('tension headache')
})

test('asks the clarifying question and continues with the answer', async () => {
  api.recommend.mockResolvedValue({ outcome: 'clarification_needed', attempt_id: 'a1', question: 'Where is the pain?' })
  api.clarify.mockResolvedValue(RESULT)
  renderWithProviders(<HomePage />)

  await submit('it hurts')
  expect(await screen.findByRole('heading', { name: 'Where is the pain?' })).toBeInTheDocument()
  await userEvent.type(screen.getByLabelText('Your answer'), 'behind my eyes')
  await userEvent.click(screen.getByRole('button', { name: 'Continue' }))

  expect(api.clarify).toHaveBeenCalledWith('a1', 'behind my eyes')
  expect(await screen.findByText('Point PC6')).toBeInTheDocument()
})

test('shows a no-match result and lets the user start over', async () => {
  api.recommend.mockResolvedValue({ outcome: 'no_match', attempt_id: 'a1', message: 'Sorry, nothing suitable.' })
  renderWithProviders(<HomePage />)

  await submit('my knee clicks')
  expect(await screen.findByRole('heading', { name: 'No suitable points found' })).toBeInTheDocument()
  expect(screen.getByText('Sorry, nothing suitable.')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Try a different description' }))
  expect(screen.getByRole('heading', { name: 'Three points to try' })).toBeInTheDocument()
})

test('shows a generic error with a retry that repeats the request', async () => {
  api.recommend
    .mockRejectedValueOnce(new ApiError(502, { code: 'recommendation_failed', message: 'Please try again later.', retryable: true }))
    .mockResolvedValueOnce(RESULT)
  renderWithProviders(<HomePage />)

  await submit('tension headache')
  expect(await screen.findByRole('alert')).toHaveTextContent('Please try again later.')
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))

  expect(await screen.findByText('Point HT7')).toBeInTheDocument()
  expect(api.recommend).toHaveBeenNthCalledWith(2, 'tension headache')
})
