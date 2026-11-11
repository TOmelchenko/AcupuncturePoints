import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { renderWithProviders } from '@/test/utils'
import { SignOutButton } from '@/auth/SignOutButton'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { LoginPage } from './LoginPage'
import { RegisterPage } from './RegisterPage'
import { ResetPasswordPage } from './ResetPasswordPage'

const auth = vi.hoisted(() => ({
  signInWithPassword: vi.fn(),
  signUp: vi.fn(),
  resetPasswordForEmail: vi.fn(),
  updateUser: vi.fn(),
  signOut: vi.fn(),
}))
vi.mock('@/lib/supabase', () => ({ supabase: { auth } }))

beforeEach(() => vi.clearAllMocks())

function withHome(page: React.ReactElement, path: string) {
  return (
    <Routes>
      <Route path={path} element={page} />
      <Route path="/" element={<h1>Home</h1>} />
    </Routes>
  )
}

describe('login', () => {
  test('describes the app', () => {
    renderWithProviders(<LoginPage />, { session: null })
    expect(screen.getByRole('region', { name: 'About this app' })).toHaveTextContent(/acupressure self-care guide/)
  })

  test('validates fields before calling Supabase', async () => {
    renderWithProviders(<LoginPage />, { session: null })
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
    expect(auth.signInWithPassword).not.toHaveBeenCalled()
  })

  test('signs in and goes home', async () => {
    auth.signInWithPassword.mockResolvedValue({ error: null })
    renderWithProviders(withHome(<LoginPage />, '/login'), { session: null, route: '/login' })
    await userEvent.type(screen.getByLabelText('Email'), 'user@example.test')
    await userEvent.type(screen.getByLabelText('Password'), 'secret-pass')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(auth.signInWithPassword).toHaveBeenCalledWith({ email: 'user@example.test', password: 'secret-pass' })
    expect(await screen.findByRole('heading', { name: 'Home' })).toBeInTheDocument()
  })

  test('shows the Supabase error message', async () => {
    auth.signInWithPassword.mockResolvedValue({ error: { message: 'Invalid login credentials' } })
    renderWithProviders(<LoginPage />, { session: null })
    await userEvent.type(screen.getByLabelText('Email'), 'user@example.test')
    await userEvent.type(screen.getByLabelText('Password'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials')
  })
})

describe('register', () => {
  test('tells the user the password rule before they type', async () => {
    renderWithProviders(<RegisterPage />, { session: null })
    expect(screen.getByLabelText('Password')).toHaveAccessibleDescription('At least 8 characters.')
    await userEvent.type(screen.getByLabelText('Password'), 'short')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('Use at least 8 characters.')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toHaveAccessibleDescription(
      'At least 8 characters. Use at least 8 characters.',
    )
  })

  test('requires matching passwords of at least 8 characters', async () => {
    renderWithProviders(<RegisterPage />, { session: null })
    await userEvent.type(screen.getByLabelText('Email'), 'not-an-email')
    await userEvent.type(screen.getByLabelText('Password'), 'short')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'different')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Use at least 8 characters.')).toBeInTheDocument()
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument()
    expect(auth.signUp).not.toHaveBeenCalled()
  })

  test('asks the user to confirm their email when verification is required', async () => {
    auth.signUp.mockResolvedValue({ data: { session: null }, error: null })
    renderWithProviders(<RegisterPage />, { session: null })
    await userEvent.type(screen.getByLabelText('Email'), 'new@example.test')
    await userEvent.type(screen.getByLabelText('Password'), 'long-enough')
    await userEvent.type(screen.getByLabelText('Confirm password'), 'long-enough')
    await userEvent.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Check your email')
    expect(auth.signUp).toHaveBeenCalledWith(
      expect.objectContaining({ email: 'new@example.test', password: 'long-enough' }),
    )
  })
})

describe('password reset', () => {
  test('requests a reset link that returns to /reset-password', async () => {
    auth.resetPasswordForEmail.mockResolvedValue({ error: null })
    renderWithProviders(<ForgotPasswordPage />, { session: null })
    await userEvent.type(screen.getByLabelText('Email'), 'user@example.test')
    await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }))
    expect(await screen.findByRole('status')).toHaveTextContent('reset link is on its way')
    expect(auth.resetPasswordForEmail).toHaveBeenCalledWith('user@example.test', {
      redirectTo: `${window.location.origin}/reset-password`,
    })
  })

  test.each([
    { code: 'over_email_send_rate_limit', message: 'email rate limit exceeded' },
    { message: 'Email rate limit exceeded' },
  ])('explains the hourly email limit instead of showing the raw error: %o', async (error) => {
    auth.resetPasswordForEmail.mockResolvedValue({ error })
    renderWithProviders(<ForgotPasswordPage />, { session: null })
    await userEvent.type(screen.getByLabelText('Email'), 'user@example.test')
    await userEvent.click(screen.getByRole('button', { name: 'Send reset link' }))
    expect(await screen.findByText('Too many emails were requested. Please try again in an hour.')).toBeInTheDocument()
    expect(screen.queryByText(/rate limit/i)).not.toBeInTheDocument()
  })

  test('the reset link page saves a new password', async () => {
    auth.updateUser.mockResolvedValue({ error: null })
    renderWithProviders(withHome(<ResetPasswordPage />, '/reset-password'), { route: '/reset-password' })
    await userEvent.type(screen.getByLabelText('New password'), 'brand-new-pass')
    await userEvent.type(screen.getByLabelText('Confirm new password'), 'brand-new-pass')
    await userEvent.click(screen.getByRole('button', { name: 'Save new password' }))
    expect(auth.updateUser).toHaveBeenCalledWith({ password: 'brand-new-pass' })
    expect(await screen.findByRole('heading', { name: 'Home' })).toBeInTheDocument()
  })

  test('an invalid or expired link explains what to do', () => {
    renderWithProviders(<ResetPasswordPage />, { session: null })
    expect(screen.getByRole('alert')).toHaveTextContent('invalid or has expired')
    expect(screen.getByRole('link', { name: 'Request a new link' })).toBeInTheDocument()
  })
})

test('sign out calls Supabase', async () => {
  auth.signOut.mockResolvedValue({ error: null })
  renderWithProviders(<SignOutButton />)
  await userEvent.click(screen.getByRole('button', { name: 'Sign out' }))
  await waitFor(() => expect(auth.signOut).toHaveBeenCalled())
})
