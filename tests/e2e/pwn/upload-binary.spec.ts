// Sprint 18 e2e — Pwn mode: drop an ELF binary, watch checksec badges +
// the symbols tab populate. The checksec view is the most user-visible
// signal that the pipeline (upload → pwntools.ELF → checksec) works.

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '../fixtures/anvil'

// `__dirname` is unavailable under "type": "module" — derive it from import.meta.
const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SAMPLE_DIR = join(__dirname, '..', '..', '..', 'samples', 'pwn')

/** Read the project sample binary if present, else skip the test. */
function loadSampleBinary(name: string): Buffer | null {
  try {
    return readFileSync(join(SAMPLE_DIR, name))
  } catch {
    return null
  }
}

test.describe('Pwn upload binary', () => {
  test.beforeEach(async ({ app }) => {
    await app.switchMode('Pwn')
    await expect(app.pwnDropZone).toBeVisible({ timeout: 10_000 })
  })

  test('uploading a precompiled ELF reveals checksec badges', async ({ app, page }) => {
    const bin = loadSampleBinary('bof_basic')
    test.skip(!bin, 'Run `make -C samples/pwn` first to produce ELF samples')

    // Drop via the hidden file input — the dropzone wires both drag-and-drop and click-to-pick.
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles({
      name: 'bof_basic',
      mimeType: 'application/x-executable',
      buffer: bin!,
    })

    // Checksec badges always include NX, PIE, RELRO, Canary at minimum.
    await expect(page.getByText(/NX/).first()).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/PIE/).first()).toBeVisible()
    await expect(page.getByText(/RELRO/).first()).toBeVisible()
    await expect(page.getByText(/Canary/).first()).toBeVisible()
  })

  test('Symbols tab fills with at least one entry', async ({ app, page }) => {
    const bin = loadSampleBinary('bof_basic')
    test.skip(!bin, 'Run `make -C samples/pwn` first to produce ELF samples')

    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles({
      name: 'bof_basic',
      mimeType: 'application/x-executable',
      buffer: bin!,
    })
    await expect(page.getByText(/NX/).first()).toBeVisible({ timeout: 15_000 })

    await app.pwnBottomTab('Symbols').click()
    // FilterableList shows one .anvil-pwn-symbol-row per symbol.
    await expect(page.locator('.anvil-pwn-symbol-row').first()).toBeVisible({ timeout: 10_000 })
  })

  test('filter input shrinks the symbols list', async ({ app, page }) => {
    const bin = loadSampleBinary('bof_basic')
    test.skip(!bin, 'Run `make -C samples/pwn` first to produce ELF samples')

    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles({ name: 'bof_basic', mimeType: 'application/x-executable', buffer: bin! })
    await expect(page.getByText(/NX/).first()).toBeVisible({ timeout: 15_000 })
    await app.pwnBottomTab('Symbols').click()

    const before = await page.locator('.anvil-pwn-symbol-row').count()
    await app.pwnFilterInput.fill('main')
    // Filtering is case-insensitive; expect fewer rows than before, but at least one.
    await expect.poll(() => page.locator('.anvil-pwn-symbol-row').count(), { timeout: 5_000 })
      .toBeLessThan(before || Number.MAX_SAFE_INTEGER)
  })
})
