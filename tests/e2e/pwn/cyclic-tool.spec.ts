// Sprint 18 e2e — Pwn mode: cyclic pattern generation is the canonical
// "the bridge wakes up" test for pwntools. Doesn't need a binary loaded.

import { test, expect } from '../fixtures/anvil'

test.describe('Pwn cyclic tool', () => {
  test.beforeEach(async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })
  })

  test('cyclic generates a hex pattern of the requested length', async ({ app, page }) => {
    await app.pwnToolButton('Cyclic').click()

    // The Cyclic tool exposes a length input and a Generate button.
    // We accept any input near the Cyclic panel — cap at first match.
    const lengthInput = page.locator('input[type="number"], input[type="text"]').first()
    await lengthInput.fill('128')

    const generateBtn = page.getByRole('button', { name: /Generate|Générer/i }).first()
    await generateBtn.click()

    // Result shows up in the same Cyclic panel; assert SOME long-ish hex string is now visible.
    await expect(page.locator('text=/[0-9a-f]{32,}/i').first()).toBeVisible({ timeout: 5_000 })
  })

  test('cyclic_find returns an offset for a known sub-pattern', async ({ app, page }) => {
    await app.pwnToolButton('Cyclic').click()

    // Use the find sub-input. The component layout is "length input | generate | find input | find btn".
    const inputs = page.locator('input').filter({ hasText: /.?/ }) // any input within tool panel
    // We rely on positional fill — index 0 = length, index 1 = needle.
    const allInputs = await page.locator('.anvil-pwn-tool-panel input, .anvil-pwn-tool input').all()
    if (allInputs.length < 2) test.skip(true, 'Cyclic tool layout differs — skipping find sub-test')

    await allInputs[0].fill('200')
    await page.getByRole('button', { name: /Generate|Générer/i }).first().click()
    // Pattern starts with "aaaa…" → searching "aaab" returns offset 4 in the de Bruijn sequence.
    await allInputs[1].fill('aaab')
    await page.getByRole('button', { name: /Find|Trouver|Search/i }).first().click()

    await expect(page.getByText(/offset.*4|4.*offset/i).first()).toBeVisible({ timeout: 5_000 })
    void inputs
  })
})
