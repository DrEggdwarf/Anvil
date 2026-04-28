// Sprint 18 e2e — Pwn mode is lazy-loaded (Sprint 15 React.lazy). This spec
// proves the dynamic import resolves and the layout mounts without errors.

import { test, expect } from '../fixtures/anvil'

test.describe('Pwn mode switch', () => {
  test('clicking Pwn loads the lazy chunk and mounts the layout', async ({ app, page }) => {
    await app.switchMode('Pwn')

    // Either the loading fallback flashes briefly, or the dropzone is already up.
    // After a beat, the dropzone must be visible.
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })
  })

  test('topbar exposes the inline tool buttons', async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })

    // Five inline tools live in the topbar.
    await expect(app.pwnToolButton('Cyclic')).toBeAttached()
    await expect(app.pwnToolButton('ROP')).toBeAttached()
    await expect(app.pwnToolButton('Format String')).toBeAttached()
    await expect(app.pwnToolButton('Shellcraft')).toBeAttached()
  })

  test('bottom panel exposes the data tabs', async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })

    await expect(app.pwnBottomTab('Terminal')).toBeAttached()
    await expect(app.pwnBottomTab('Symbols')).toBeAttached()
    await expect(app.pwnBottomTab('GOT')).toBeAttached()
    await expect(app.pwnBottomTab('PLT')).toBeAttached()
    await expect(app.pwnBottomTab('Strings')).toBeAttached()
  })

  test('returning to ASM keeps Pwn state isolated', async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })
    await app.switchMode('ASM')

    // ASM toolbar buttons are visible; the Pwn dropzone is not.
    await expect(app.runButton).toBeVisible()
    await expect(app.pwnDropZone).not.toBeVisible()
  })
})
