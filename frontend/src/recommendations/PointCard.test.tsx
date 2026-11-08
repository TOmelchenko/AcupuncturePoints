import { render, screen, within } from '@testing-library/react'
import type { RecommendedPoint } from '@/lib/types'
import { PointCard } from './PointCard'

const base: RecommendedPoint = {
  point_id: 'LI4', rank: 1, name: 'Hegu (Union Valley)', location_text: 'Between thumb and index finger.',
  image_url: null, image_attribution: null, instructions: ['Relax your hand.', 'Press firmly.'],
  duration: null, pressure: null,
}

test('shows the curated image with attribution when available', () => {
  render(<PointCard index={0} point={{ ...base, image_url: 'http://img.test/li4.svg', image_attribution: 'Diagram by A. Author' }} />)
  const image = screen.getByRole('img', { name: 'Location of Hegu (Union Valley)' })
  expect(image).toHaveAttribute('src', 'http://img.test/li4.svg')
  expect(screen.getByText('Diagram by A. Author')).toBeInTheDocument()
})

test('falls back to the text location when there is no image', () => {
  render(<PointCard index={0} point={base} />)
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  expect(screen.getByText('Between thumb and index finger.')).toBeInTheDocument()
})

test('lists the instructions as ordered steps', () => {
  render(<PointCard index={0} point={base} />)
  const steps = within(screen.getByRole('list')).getAllByRole('listitem')
  expect(steps.map((s) => s.textContent)).toEqual(['Relax your hand.', 'Press firmly.'])
})

test('omits duration and pressure when the curated record has none', () => {
  render(<PointCard index={0} point={base} />)
  expect(screen.queryByText(/Duration/)).not.toBeInTheDocument()
  expect(screen.queryByText(/Pressure:/)).not.toBeInTheDocument()
})

test('shows only the guidance that is present', () => {
  render(<PointCard index={0} point={{ ...base, pressure: 'Gentle' }} />)
  expect(screen.getByText('Gentle')).toBeInTheDocument()
  expect(screen.queryByText(/Duration/)).not.toBeInTheDocument()

  render(<PointCard index={1} point={{ ...base, point_id: 'PC6', duration: '2–3 minutes' }} />)
  expect(screen.getByText('2–3 minutes')).toBeInTheDocument()
})

test('the card is labelled by the point name', () => {
  render(<PointCard index={0} point={base} />)
  expect(screen.getByRole('article', { name: 'Hegu (Union Valley)' })).toBeInTheDocument()
})
