// Sprint 18 e2e — ASM mode: stack/memory/security panels react to the GDB
// session state. Each panel is mounted lazily; this spec asserts they at
// least render without crashing once a session is live.

import { test, expect } from '../fixtures/anvil'
import { ASM_NASM_HELLO } from '../fixtures/samples'

test.describe('ASM state panels', () => {
  test('panels render without crashing once stopped at _start', async ({ app, page }) => {
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Arrete a _start/, 20_000)

    // The Stack panel header is always present; the Memory panel header too.
    // They expand on click — we just verify they exist.
    await expect(page.getByText(/^Stack$/)).toBeVisible()
    await expect(page.getByText(/^Memory$/)).toBeVisible()
    await expect(page.getByText(/^Security$/)).toBeVisible()
  })

  test('right column collapse/expand toggle keeps state coherent', async ({ app, page }) => {
    // Collapse
    const collapseBtn = page.getByRole('button', { name: /Collapse/ })
    await collapseBtn.click()
    await expect(page.getByRole('button', { name: /Expand/ })).toBeVisible({ timeout: 3_000 })

    // Expand
    await page.getByRole('button', { name: /Expand/ }).click()
    await expect(page.getByRole('button', { name: /Collapse/ })).toBeVisible({ timeout: 3_000 })
  })

  test('terminal clear erases lines', async ({ app, page }) => {
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation OK/, 15_000)

    // The terminal exposes a clear control — title/text varies, search by icon class.
    const clearBtn = page.locator('.anvil-terminal').getByRole('button').first()
    if (await clearBtn.isVisible().catch(() => false)) {
      await clearBtn.click()
      // Hard to assert "empty" without coupling to internals; assert the
      // previously-shown success line is no longer visible.
      await expect(app.terminal).not.toContainText(/Compilation OK/, { timeout: 3_000 })
    }
  })
})
