import { expect, test } from '@playwright/test'
import { createUser, deleteUserByEmail, signIn } from './helpers'

let email: string

test.beforeEach(async () => {
  email = (await createUser()).email
})

test.afterEach(async () => {
  await deleteUserByEmail(email)
})

test('a past recommendation is listed in history and can be re-rated there', async ({ page }) => {
  await signIn(page, email)
  await page.getByLabel('Describe your symptom').fill('I have a headache')
  await page.getByRole('button', { name: 'Find points' }).click()
  const first = page.getByRole('article').first()
  const name = (await first.getByRole('heading').textContent())!
  await first.getByText('★').nth(3).click()
  await expect(first.getByText('Thanks — saved')).toBeVisible()

  await page.getByRole('link', { name: 'History' }).click()
  const entry = page.getByRole('link', { name: /I have a headache/ })
  await expect(entry).toContainText('Three points')
  await expect(entry).toContainText(`${name}★ 4`)
  await page.screenshot({ path: `test-results/history-list-${test.info().project.name}.png`, fullPage: true })

  await entry.click()
  const saved = page.getByRole('article', { name })
  await expect(saved.getByRole('radio', { name: '4 stars' })).toBeChecked()
  await page.screenshot({ path: `test-results/history-detail-${test.info().project.name}.png` })
  await saved.getByText('★').nth(1).click()
  await expect(saved.getByText('Thanks — saved')).toBeVisible()

  await page.getByRole('link', { name: 'All history' }).click()
  await expect(page.getByRole('link', { name: /I have a headache/ })).toContainText(`${name}★ 2`)
})
