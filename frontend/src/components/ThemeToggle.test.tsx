import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeToggle } from './ThemeToggle'

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove('dark')
})

test('light is the default and the toggle switches to dark and back', async () => {
  render(<ThemeToggle />)
  expect(document.documentElement).not.toHaveClass('dark')

  await userEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }))
  expect(document.documentElement).toHaveClass('dark')
  expect(localStorage.getItem('theme')).toBe('dark')

  await userEvent.click(screen.getByRole('button', { name: 'Switch to light theme' }))
  expect(document.documentElement).not.toHaveClass('dark')
  expect(localStorage.getItem('theme')).toBe('light')
})

test('a saved dark choice is remembered', () => {
  localStorage.setItem('theme', 'dark')
  render(<ThemeToggle />)
  expect(screen.getByRole('button', { name: 'Switch to light theme' })).toBeInTheDocument()
})
