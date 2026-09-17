import { test, expect } from '@playwright/test'
import { sendMessage } from './helpers'

test('delivery-procedure answer: ordered steps, warning visible, citation opens evidence panel', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'How do I receive a delivery?')

  await expect(page.getByRole('listitem')).toHaveCount(3)
  await expect(page.getByText('Do not stock a pallet with unresolved damage exceptions.')).toBeVisible()

  await page.getByRole('button', { name: /dock intake/i }).first().click()
  await expect(
    page.getByText(
      'Verify the packing slip against the purchase order before opening any pallet. Route confirmed deliveries to the assigned dock lane.',
    ),
  ).toBeVisible()
})

test('term-explanation answer preserves the warning and explanation verbatim', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'What does exception mean?')

  await expect(
    page.getByText(
      "An exception is any damage, shortage, or mismatch you notice. Write it on the receiving form before the pallet goes on the shelf.",
    ),
  ).toBeVisible()
  await expect(page.getByText('Do not stock a pallet with unresolved damage exceptions.')).toBeVisible()
})

test('original-text toggle swaps every step to the source wording and back', async ({ page }) => {
  await page.goto('/')
  await sendMessage(page, 'How do I receive a delivery?')

  const toggle = page.getByRole('button', { name: /show original procedure text/i })
  await toggle.click()
  await expect(page.getByText('Verify the packing slip against the purchase order before opening any pallet.')).toBeVisible()

  await page.getByRole('button', { name: /show plain-language explanation/i }).click()
  await expect(page.getByText("Check that what's on the packing slip matches what was ordered before you break down the pallet.")).toBeVisible()
})
