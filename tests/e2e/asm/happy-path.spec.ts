// Sprint 18 e2e — ASM mode: the canonical "compile → run → step → registers
// update" loop. If this spec breaks, the ASM mode is unusable.

import { test, expect } from '../fixtures/anvil'
import { ASM_NASM_HELLO } from '../fixtures/samples'

test.describe('ASM happy path', () => {
  test('compile NASM, run to _start, registers populated', async ({ app }) => {
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()

    await app.waitForTerminalLine(/Compilation OK/)
    await app.waitForTerminalLine(/Arrete a _start/, 20_000)

    // Once stopped at _start, the GP-register pane must be populated.
    await expect(app.registerCard('rax')).toBeVisible()
    await expect(app.registerCard('rip')).toBeVisible()
  })

  test('step into advances the step counter', async ({ app }) => {
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Arrete a _start/, 20_000)

    await app.stepIntoButton.click()
    await app.waitForStepCount(1)
    await app.stepIntoButton.click()
    await app.waitForStepCount(2)
  })

  test('terminal captures program stdout', async ({ app }) => {
    await app.setEditorContent(ASM_NASM_HELLO)
    await app.runButton.click()
    await app.waitForTerminalLine(/Arrete a _start/, 20_000)

    // Continue past _start so the write syscall fires and "Hello, e2e!" lands in the terminal.
    // Step a handful of times rather than `continue` because the sample does not
    // install a final breakpoint; stepping is the safe path.
    for (let i = 0; i < 8; i++) await app.stepIntoButton.click()

    // The exact wording lives in samples.ts — assert it shows up at least once.
    await expect(app.terminal).toContainText(/Hello, e2e!/, { timeout: 10_000 })
  })
})
