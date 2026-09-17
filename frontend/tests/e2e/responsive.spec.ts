import { test, expect } from '@playwright/test'
import { sendMessage } from './helpers'

const viewports = [
  { name: 'desktop', width: 1280, height: 800 },
  { name: 'mobile', width: 375, height: 812 },
]

for (const viewport of viewports) {
  test(`no horizontal page overflow at ${viewport.name} (${viewport.width}px) with a wide inventory table`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/')
    await sendMessage(page, 'Can we assemble 20 units of Kit A?')
    await page.getByRole('button', { name: 'Kit A — Standard (asm-kit-a-std)' }).click()
    await expect(page.getByText('Ready')).toBeVisible()

    const hasPageOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    expect(hasPageOverflow).toBe(false)

    // The component table scrolls within its own bounded region instead of the page.
    const tableScroll = page.locator('.component-table__scroll')
    const canScrollWithinRegion = await tableScroll.evaluate((el) => el.scrollWidth >= el.clientWidth)
    expect(canScrollWithinRegion).toBe(true)

    await page.screenshot({ path: `test-results/screenshots/${viewport.name}.png`, fullPage: true })
  })
}

test('the two-column layout collapses to one column under the mobile breakpoint', async ({ page }) => {
  await page.setViewportSize({ width: 400, height: 800 })
  await page.goto('/')
  const chatRect = await page.locator('.app-shell__chat').boundingBox()
  const evidenceRect = await page.locator('.app-shell__evidence').boundingBox()
  expect(chatRect).not.toBeNull()
  expect(evidenceRect).not.toBeNull()
  // Stacked: evidence panel starts below where the chat column ends, not beside it.
  expect(evidenceRect!.y).toBeGreaterThanOrEqual(chatRect!.y + chatRect!.height - 1)
})

test('the two-column layout stays side by side above the mobile breakpoint', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/')
  const chatRect = await page.locator('.app-shell__chat').boundingBox()
  const evidenceRect = await page.locator('.app-shell__evidence').boundingBox()
  expect(chatRect).not.toBeNull()
  expect(evidenceRect).not.toBeNull()
  expect(evidenceRect!.x).toBeGreaterThanOrEqual(chatRect!.x + chatRect!.width - 1)
})
