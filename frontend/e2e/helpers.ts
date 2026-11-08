import { expect, type Page } from '@playwright/test'

const SUPABASE_URL = process.env.SUPABASE_URL!
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY!
const MAILPIT_URL = process.env.MAILPIT_URL!
const admin = { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}`, 'Content-Type': 'application/json' }

export const PASSWORD = 'e2e-password-123'

export function uniqueEmail(prefix: string) {
  return `e2e-${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.test`
}

/** A confirmed user created directly through the Supabase Admin API. */
export async function createUser(email = uniqueEmail('user')) {
  const response = await fetch(`${SUPABASE_URL}/auth/v1/admin/users`, {
    method: 'POST',
    headers: admin,
    body: JSON.stringify({ email, password: PASSWORD, email_confirm: true }),
  })
  expect(response.ok).toBe(true)
  const user = (await response.json()) as { id: string }
  return { email, id: user.id }
}

export async function deleteUserByEmail(email: string) {
  const response = await fetch(`${SUPABASE_URL}/auth/v1/admin/users?per_page=1000`, { headers: admin })
  const { users } = (await response.json()) as { users: { id: string; email: string }[] }
  for (const user of users.filter((u) => u.email === email)) {
    await fetch(`${SUPABASE_URL}/auth/v1/admin/users/${user.id}`, { method: 'DELETE', headers: admin })
  }
}

/** The first link in the newest Mailpit email sent to the address. */
export async function emailLink(email: string): Promise<string> {
  for (let i = 0; i < 20; i++) {
    const search = await fetch(`${MAILPIT_URL}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`)
    const { messages } = (await search.json()) as { messages: { ID: string }[] }
    if (messages.length > 0) {
      const message = (await (await fetch(`${MAILPIT_URL}/api/v1/message/${messages[0].ID}`)).json()) as { Text: string }
      const link = /https?:\/\/[^\s"'<>]+/.exec(message.Text)?.[0]
      if (link) return link.replaceAll('&amp;', '&')
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`no email for ${email}`)
}

export async function signIn(page: Page, email: string) {
  await page.goto('/login')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(PASSWORD)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'How are you feeling today?' })).toBeVisible()
}
