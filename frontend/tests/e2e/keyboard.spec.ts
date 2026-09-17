import { test, expect } from '@playwright/test'

test('keyboard-only pass: input -> send -> citation chip -> Evidence panel -> Escape returns focus', async ({
  page,
}) => {
  await page.goto('/')

  const textbox = page.getByRole('textbox', { name: /ask a question/i })
  await textbox.click()
  await textbox.fill('How do I receive a delivery?')
  await textbox.press('Enter')

  // Sending moves focus to the new answer; Tab from there reaches its first citation chip.
  await expect(page.locator('.message-bubble--assistant').first()).toBeFocused()
  await page.keyboard.press('Tab')
  const chip = page.getByRole('button', { name: /dock intake/i }).first()
  await expect(chip).toBeFocused()

  await page.keyboard.press('Enter')
  await expect(page.getByRole('region', { name: 'Evidence' })).toBeFocused()

  await page.keyboard.press('Escape')
  await expect(chip).toBeFocused()
})

test('Shift+Enter inserts a newline instead of sending', async ({ page }) => {
  await page.goto('/')
  const textbox = page.getByRole('textbox', { name: /ask a question/i })
  await textbox.click()
  await textbox.type('line one')
  await textbox.press('Shift+Enter')
  await textbox.type('line two')

  await expect(textbox).toHaveValue('line one\nline two')
  await expect(page.locator('.message-bubble--user')).toHaveCount(0)
})
