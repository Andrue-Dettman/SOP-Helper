import { test, expect } from '@playwright/test'
import { sendMessage } from './helpers'

test('insufficient_evidence shows an explicit banner with no fabricated citations', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'There is a conflict in the procedures')

  await expect(page.getByText(/not enough evidence/i)).toBeVisible()
  await expect(page.getByRole('button', { name: /^Source \d+:/ })).toHaveCount(0)
})

test('temporarily_unavailable shows a retry action; retrying replaces the turn, not duplicates it', async ({
  page,
}) => {
  await page.goto('/')
  await sendMessage(page, 'The system seems unavailable')

  await expect(page.getByText('The inventory database is temporarily unavailable.')).toBeVisible()
  const input = page.getByRole('textbox', { name: /ask a question/i })
  await expect(input).toBeEnabled()

  await page.getByRole('button', { name: /retry/i }).click()
  await expect(page.getByRole('button', { name: /retry/i })).toHaveCount(1)
})

test('a client-side network failure shows a distinct banner and keeps the input usable', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'simulate a network disconnect')

  await expect(page.getByText(/couldn.t reach/i)).toBeVisible()
  await expect(page.getByRole('textbox', { name: /ask a question/i })).toBeEnabled()
})

test('a delayed response shows the loading indicator without causing horizontal overflow', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'please respond slowly')

  await expect(page.getByRole('status')).toHaveText(/thinking/i)
  const hasOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(hasOverflow).toBe(false)
})
