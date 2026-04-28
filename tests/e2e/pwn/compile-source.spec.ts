// Sprint 18 e2e — Pwn mode: drop a .c source, watch the auto-compile pipeline
// route through CompilationBridge (Sprint 14 #3 unification) and produce an ELF.

import { test, expect } from '../fixtures/anvil'
import { C_BOF_BASIC } from '../fixtures/samples'

test.describe('Pwn compile source', () => {
  test.beforeEach(async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })
  })

  test('dropping a .c source triggers auto-compile + ELF analysis', async ({ app, page }) => {
    test.skip(!process.env.E2E_HAS_GCC, 'set E2E_HAS_GCC=1 if gcc is installed on the host')

    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles({
      name: 'bof_basic.c',
      mimeType: 'text/x-csrc',
      buffer: Buffer.from(C_BOF_BASIC, 'utf8'),
    })

    // Pipeline: write_source → compile_source → elf_load → checksec.
    await expect(page.getByText(/NX/).first()).toBeVisible({ timeout: 30_000 })
    await expect(page.getByText(/RELRO/).first()).toBeVisible()
  })

  test('source viewer shows the dropped C code', async ({ app, page }) => {
    test.skip(!process.env.E2E_HAS_GCC, 'set E2E_HAS_GCC=1 if gcc is installed on the host')

    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles({
      name: 'bof_basic.c',
      mimeType: 'text/x-csrc',
      buffer: Buffer.from(C_BOF_BASIC, 'utf8'),
    })

    // SourceViewer is a Monaco editor — `strcpy` is one of the highlighted vuln patterns.
    await expect(page.getByText(/strcpy/).first()).toBeVisible({ timeout: 30_000 })
  })
})
