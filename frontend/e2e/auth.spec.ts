import { expect, test } from '@playwright/test'
import { deleteUserByEmail, emailLink, PASSWORD, uniqueEmail } from './helpers'

test('register, confirm the email and land signed in, then sign out', async ({ page }) => {
  const email = uniqueEmail('register')
  try {
    await page.goto('/register')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password', { exact: true }).fill(PASSWORD)
    await page.getByLabel('Confirm password').fill(PASSWORD)
    await page.getByRole('button', { name: 'Create account' }).click()
    await expect(page.getByRole('status')).toContainText('Check your email')

    await page.goto(await emailLink(email))
    await expect(page.getByRole('heading', { name: 'How are you feeling today?' })).toBeVisible()

    await page.getByRole('button', { name: 'Sign out' }).click()
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
  } finally {
    await deleteUserByEmail(email)
  }
})

test('protected pages send signed-out visitors to sign in', async ({ page }) => {
  await page.goto('/account')
  await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible()
})

test('wrong password shows an error', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('nobody@example.test')
  await page.getByLabel('Password').fill('wrong-password')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('alert')).toContainText(/invalid/i)
})
