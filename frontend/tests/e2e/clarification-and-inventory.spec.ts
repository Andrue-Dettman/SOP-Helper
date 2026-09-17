import { test, expect } from '@playwright/test'
import { sendMessage } from './helpers'

test('ambiguous assembly resolves through the clarification prompt into a ready build result', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'Can we assemble 20 units of Kit A?')

  await expect(page.getByText('"Kit A" matches more than one assembly. Which one do you mean?')).toBeVisible()
  const choices = page.getByRole('button', { name: /^Kit A/ })
  await expect(choices).toHaveCount(2)

  await page.getByRole('button', { name: 'Kit A — Standard (asm-kit-a-std)' }).click()

  await expect(page.getByText('Ready')).toBeVisible()
  await expect(page.getByText('snap-2026-09-14')).toBeVisible()
  const row = page.locator('tr', { hasText: 'Side Panel A' })
  await expect(row.locator('td')).toHaveText(['20', '32', '0'])
})

test('a shortage question shows a distinct not-ready banner with matching figures', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'Is there a shortage for Kit A?')

  await expect(page.getByText('Not ready')).toBeVisible()
  const row = page.locator('tr', { hasText: 'Side Panel A' })
  await expect(row.locator('td')).toHaveText(['20', '12', '8'])
})
