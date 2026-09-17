import type { Page } from '@playwright/test'

export async function sendMessage(page: Page, text: string) {
  const textbox = page.getByRole('textbox', { name: /ask a question/i })
  await textbox.fill(text)
  await textbox.press('Enter')
}
