import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router'
import { ApiError } from '@/lib/api'
import { renderWithProviders } from '@/test/utils'
import { AccountPage } from './AccountPage'

const auth = vi.hoisted(() => ({ updateUser: vi.fn(), signOut: vi.fn() }))
const deleteAccount = vi.hoisted(() => vi.fn())
vi.mock('@/lib/supabase', () => ({ supabase: { auth } }))
vi.mock('@/lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/api')>()),
  api: { deleteAccount },
}))

beforeEach(() => vi.clearAllMocks())

function renderPage() {
  return renderWithProviders(
    <Routes>
      <Route path="/account" element={<AccountPage />} />
      <Route path="/login" element={<h1>Login</h1>} />
    </Routes>,
    { route: '/account' },
  )
}

test('shows the signed-in email and no email-change option', () => {
  renderPage()
  expect(screen.getByText('Signed in as user@example.test')).toBeInTheDocument()
  expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument()
})

test('validates and changes the password', async () => {
  auth.updateUser.mockResolvedValue({ error: null })
  renderPage()
  await userEvent.type(screen.getByLabelText('New password'), 'short')
  await userEvent.click(screen.getByRole('button', { name: 'Change password' }))
  expect(await screen.findByText('Use at least 8 characters.')).toBeInTheDocument()
  expect(auth.updateUser).not.toHaveBeenCalled()

  await userEvent.clear(screen.getByLabelText('New password'))
  await userEvent.type(screen.getByLabelText('New password'), 'a-better-password')
  await userEvent.type(screen.getByLabelText('Confirm new password'), 'a-better-password')
  await userEvent.click(screen.getByRole('button', { name: 'Change password' }))
  expect(await screen.findByRole('status')).toHaveTextContent('Your password has been changed.')
  expect(auth.updateUser).toHaveBeenCalledWith({ password: 'a-better-password' })
})

test('account is deleted only after explicit confirmation', async () => {
  deleteAccount.mockResolvedValue(undefined)
  auth.signOut.mockResolvedValue({ error: null })
  renderPage()

  await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }))
  const dialog = await screen.findByRole('alertdialog')
  await userEvent.click(within(dialog).getByRole('button', { name: 'Cancel' }))
  expect(deleteAccount).not.toHaveBeenCalled()

  await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }))
  await userEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Yes, delete everything' }))

  await waitFor(() => expect(deleteAccount).toHaveBeenCalledTimes(1))
  expect(auth.signOut).toHaveBeenCalled()
  expect(await screen.findByRole('heading', { name: 'Login' })).toBeInTheDocument()
})

test('a failed deletion shows the error and allows retrying', async () => {
  deleteAccount.mockRejectedValue(
    new ApiError(502, { code: 'internal_error', message: "We couldn't delete your account. Please try again.", retryable: true }),
  )
  renderPage()
  await userEvent.click(screen.getByRole('button', { name: 'Delete my account' }))
  await userEvent.click(within(await screen.findByRole('alertdialog')).getByRole('button', { name: 'Yes, delete everything' }))

  expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't delete your account.")
  expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
  expect(auth.signOut).not.toHaveBeenCalled()
})
