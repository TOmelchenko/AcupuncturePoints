import { expect, test } from '@playwright/test'
import { createUser, deleteUserByEmail, signIn } from './helpers'

let email: string

test.beforeEach(async () => {
  email = (await createUser()).email
})

test.afterEach(async () => {
  await deleteUserByEmail(email)
})

test('submit a symptom, see three recommendations and rate one', async ({ page }) => {
  await signIn(page, email)
  await page.getByLabel('Describe your symptom').fill('I have a headache')
  await page.getByRole('button', { name: 'Find points' }).click()

  const cards = page.getByRole('article')
  await expect(cards).toHaveCount(3)
  const hegu = page.getByRole('article', { name: 'Hegu (Union Valley)' })
  await expect(hegu.getByRole('img', { name: 'Location of Hegu (Union Valley)' })).toBeVisible()
  await expect(page.getByRole('article', { name: 'Yintang (Hall of Impression)' })).toContainText('Midway between')

  await hegu.getByText('★').nth(3).click() // fourth star
  await expect(hegu.getByText('Thanks — saved')).toBeVisible()
  await expect(hegu.getByRole('radio', { name: '4 stars' })).toBeChecked()
})

test('a vague symptom asks a question before recommending', async ({ page }) => {
  await signIn(page, email)
  await page.getByLabel('Describe your symptom').fill('I feel off today')
  await page.getByRole('button', { name: 'Find points' }).click()

  await expect(page.getByText('One more question')).toBeVisible()
  await page.getByLabel('Your answer').fill('I am stressed and cannot sleep')
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page.getByRole('article')).toHaveCount(3)
})

test('an AI failure shows a generic error with retry', async ({ page }) => {
  await signIn(page, email)
  await page.getByLabel('Describe your symptom').fill('headache [demo:fail]')
  await page.getByRole('button', { name: 'Find points' }).click()

  await expect(page.getByRole('alert')).toContainText('Please try again')
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible()
})
