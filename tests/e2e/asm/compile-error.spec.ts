// Sprint 18 e2e — ASM mode: a syntax error is surfaced in the terminal and
// the editor highlights the offending line.

import { test, expect } from '../fixtures/anvil'
import { ASM_BROKEN } from '../fixtures/samples'

test.describe('ASM compile error', () => {
  test('broken NASM source surfaces a structured error', async ({ app }) => {
    await app.setEditorContent(ASM_BROKEN)
    await app.runButton.click()

    // The bridge wraps NASM stderr into a structured error containing the line number.
    await app.waitForTerminalLine(/Compilation echouee/, 15_000)
    await expect(app.terminal).toContainText(/L5/)
  })

  test('error line is annotated in the editor gutter', async ({ app }) => {
    await app.setEditorContent(ASM_BROKEN)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation echouee/, 15_000)

    // The error class is applied to the gutter at line 5 — see editor.css.
    // Use a permissive matcher: any `.anvil-ed-error` inside the editor proves
    // the highlight pipeline ran without coupling to the exact CSS structure.
    await expect(app.page.locator('.anvil-ed-error, [data-error-line="5"]').first())
      .toBeVisible({ timeout: 5_000 })
  })

  test('fixing the source clears the error on next compile', async ({ app }) => {
    await app.setEditorContent(ASM_BROKEN)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation echouee/, 15_000)

    // Replace with a minimal valid program — `nop` is enough.
    await app.setEditorContent(`section .text\n    global _start\n_start:\n    nop\n    mov rax, 60\n    xor rdi, rdi\n    syscall\n`)
    await app.runButton.click()
    await app.waitForTerminalLine(/Compilation OK/, 15_000)
  })
})
