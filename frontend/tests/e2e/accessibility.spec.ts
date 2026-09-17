import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { sendMessage } from './helpers'

// Automated scan is supporting evidence, not an accessibility certification
// (per .agents/skills/warehouse-interface/SKILL.md) — it catches machine-
// checkable issues (contrast, name/role/value, landmarks) and nothing more.
async function scanAndReport(page: import('@playwright/test').Page, testInfo: import('@playwright/test').TestInfo) {
  const results = await new AxeBuilder({ page }).analyze()
  await testInfo.attach('axe-results', { body: JSON.stringify(results, null, 2), contentType: 'application/json' })
  const seriousOrWorse = results.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  expect(seriousOrWorse, JSON.stringify(seriousOrWorse, null, 2)).toEqual([])
}

test('no serious/critical axe violations on the empty app shell', async ({ page }, testInfo) => {
  await page.goto('/')
  await scanAndReport(page, testInfo)
})

test('no serious/critical axe violations on a rendered procedure answer', async ({ page }, testInfo) => {
  await page.goto('/')
  await sendMessage(page, 'How do I receive a delivery?')
  await page.getByRole('button', { name: /dock intake/i }).first().click()
  await scanAndReport(page, testInfo)
})

test('no serious/critical axe violations on the clarification prompt', async ({ page }, testInfo) => {
  await page.goto('/')
  await sendMessage(page, 'Can we assemble 20 units of Kit A?')
  await scanAndReport(page, testInfo)
})
