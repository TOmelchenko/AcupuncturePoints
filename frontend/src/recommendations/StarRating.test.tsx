import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import { RecommendationList } from './RecommendationList'
import { StarRating } from './StarRating'

const api = vi.hoisted(() => ({ rate: vi.fn() }))
vi.mock('@/lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api')>()),
  api,
}))

beforeEach(() => vi.clearAllMocks())

function renderRating() {
  return renderWithProviders(<StarRating attemptId="a1" pointId="LI4" pointName="Hegu" />)
}

test('offers five labelled stars in an accessible group', () => {
  renderRating()
  const group = screen.getByRole('group', { name: /how helpful was Hegu/ })
  expect(within(group).getAllByRole('radio')).toHaveLength(5)
  expect(within(group).getByRole('radio', { name: '1 star' })).toBeInTheDocument()
  expect(within(group).getByRole('radio', { name: '5 stars' })).toBeInTheDocument()
})

test('clicking a star saves that rating for the point', async () => {
  api.rate.mockResolvedValue({ attempt_id: 'a1', point_id: 'LI4', rating: 4 })
  renderRating()
  await userEvent.click(screen.getByRole('radio', { name: '4 stars' }))
  expect(api.rate).toHaveBeenCalledWith('a1', 'LI4', 4)
  expect(await screen.findByText('Thanks — saved')).toBeInTheDocument()
  expect(screen.getByRole('radio', { name: '4 stars' })).toBeChecked()
})

test('works with the keyboard', async () => {
  api.rate.mockResolvedValue({})
  renderRating()
  await userEvent.tab()
  expect(screen.getByRole('radio', { name: '1 star' })).toHaveFocus()
  await userEvent.keyboard('{ArrowRight}{ArrowRight}')
  expect(api.rate).toHaveBeenLastCalledWith('a1', 'LI4', 3)
})

test('a failed save shows an error with retry', async () => {
  api.rate.mockRejectedValueOnce(new Error('down')).mockResolvedValueOnce({})
  renderRating()
  await userEvent.click(screen.getByRole('radio', { name: '2 stars' }))
  expect(await screen.findByText(/Couldn't save your rating/)).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(api.rate).toHaveBeenLastCalledWith('a1', 'LI4', 2)
  expect(await screen.findByText('Thanks — saved')).toBeInTheDocument()
})

test('each recommended point is rated independently', async () => {
  api.rate.mockResolvedValue({})
  const point = (id: string, rank: number) => ({
    point_id: id, rank, name: `Point ${id}`, location_text: 'x', image_url: null,
    image_attribution: null, instructions: ['x'], duration: null, pressure: null,
  })
  renderWithProviders(<RecommendationList attemptId="a1" points={[point('LI4', 1), point('PC6', 2), point('HT7', 3)]} />)

  const pc6 = screen.getByRole('article', { name: 'Point PC6' })
  await userEvent.click(within(pc6).getByRole('radio', { name: '5 stars' }))
  const ht7 = screen.getByRole('article', { name: 'Point HT7' })
  await userEvent.click(within(ht7).getByRole('radio', { name: '1 star' }))

  expect(api.rate).toHaveBeenCalledWith('a1', 'PC6', 5)
  expect(api.rate).toHaveBeenCalledWith('a1', 'HT7', 1)
  expect(within(screen.getByRole('article', { name: 'Point LI4' })).queryByText('Thanks — saved')).toBeNull()
})
