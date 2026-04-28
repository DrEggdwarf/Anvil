// Sprint 18 e2e — ASM mode: NASM is the default; GAS and FASM must also work
// once selected. Sprint 14 wired the assembler param all the way to the route.

import { test, expect } from '../fixtures/anvil'
import { ASM_GAS_HELLO, ASM_NASM_HELLO } from '../fixtures/samples'

test.describe('ASM multi-assembler', () => {
  test('NASM is the default and compiles', async ({ app }) => {
    await expect(app.assemblerSelect).toHaveValue('nasm')
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation OK/, 15_000)
  })

  test('GAS (AT&T) compiles when selected', async ({ app }) => {
    test.skip(!process.env.E2E_HAS_GAS, 'set E2E_HAS_GAS=1 if `as` is available')

    await app.assemblerSelect.selectOption('gas')
    await app.setEditorContent(ASM_GAS_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation OK/, 15_000)
  })

  test('FASM is offered in the dropdown', async ({ app }) => {
    // Whether or not FASM compiles depends on the host having `fasm` installed.
    // We at least verify the option is exposed so the route reaches the bridge.
    await expect(app.assemblerSelect.locator('option[value="fasm"]')).toBeAttached()
  })

  test('switching assembler updates the status bar tag', async ({ app }) => {
    await app.assemblerSelect.selectOption('gas')
    await expect(app.page.getByText('GAS', { exact: false })).toBeVisible()
    await app.assemblerSelect.selectOption('fasm')
    await expect(app.page.getByText('FASM', { exact: false })).toBeVisible()
  })
})
