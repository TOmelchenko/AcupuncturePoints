import { screen } from '@testing-library/react'
import { AppRoutes } from './App'
import { renderWithProviders } from './test/utils'

vi.mock('@/lib/supabase', () => ({ supabase: { auth: {} } }))

test('signed-out users are sent to the login page', () => {
  renderWithProviders(<AppRoutes />, { session: null })
  expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
})

test('signed-in users see the home page', () => {
  renderWithProviders(<AppRoutes />)
  expect(screen.getByRole('heading', { name: 'How are you feeling today?' })).toBeInTheDocument()
})

test('a loading session shows a status message', () => {
  renderWithProviders(<AppRoutes />, { session: null, loading: true })
  expect(screen.getByRole('status')).toHaveTextContent('Loading')
})

test('unknown routes show a not-found page', () => {
  renderWithProviders(<AppRoutes />, { route: '/nope' })
  expect(screen.getByRole('heading', { name: '404' })).toBeInTheDocument()
})
