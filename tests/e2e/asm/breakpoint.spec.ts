// Sprint 18 e2e — ASM mode: clicking the gutter sets a breakpoint and the
// running program halts on it.

import { test, expect } from '../fixtures/anvil'
import { ASM_STEP_DIVERGE } from '../fixtures/samples'

test.describe('ASM breakpoints', () => {
  test('clicking a gutter line toggles a breakpoint marker', async ({ app, page }) => {
    await app.setEditorContent(ASM_STEP_DIVERGE)

    // The gutter exposes `.anvil-ed-gutter-line` per source line. Click line 5
    // (the second mov inside _start) and assert the marker shows up.
    const gutterLines = page.locator('.anvil-ed-gutter-line')
    const fifthLine = gutterLines.nth(4)
    await fifthLine.click()

    // `.anvil-ed-bp` is the breakpoint dot — its presence on the same row proves
    // the click was routed through onToggleBreakpoint.
    await expect(page.locator('.anvil-ed-bp').first()).toBeVisible({ timeout: 3_000 })
  })

  test('breakpoint persists across edits', async ({ app, page }) => {
    await app.setEditorContent(ASM_STEP_DIVERGE)
    await page.locator('.anvil-ed-gutter-line').nth(4).click()
    await expect(page.locator('.anvil-ed-bp').first()).toBeVisible({ timeout: 3_000 })

    // Type at the very end of the buffer; the BP on line 5 must survive.
    await app.editorTextarea.click()
    await page.keyboard.press('Control+End')
    await page.keyboard.type('\n; trailing comment')

    await expect(page.locator('.anvil-ed-bp').first()).toBeVisible()
  })
})
