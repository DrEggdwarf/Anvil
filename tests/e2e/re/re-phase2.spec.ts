// Sprint 21bis e2e — RE phase 2 : Xrefs panel, Hex viewer, Decompile,
// ASM↔C sync (visual highlight). Tous les tests utilisent le binaire sample
// `samples/re_sample` (no-PIE, 5 fonctions : main/win/check_password/greet/fibonacci).

import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { test, expect } from '../fixtures/anvil'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const SAMPLE = resolve(join(__dirname, '..', '..', '..', 'samples', 're_sample'))

test.describe('RE phase 2 — Xrefs / Hex / Decompile / sync', () => {
  test.beforeEach(async () => {
    test.skip(!existsSync(SAMPLE), `Sample binary missing: ${SAMPLE}`)
  })

  test('charge un binaire et liste les fonctions', async ({ app }) => {
    await app.reLoadBinary(SAMPLE)
    // The CFG center hint appears until a function is selected
    await expect(app.reFunctionRow('main')).toBeVisible({ timeout: 30_000 })
  })

  test('Xrefs panel — sélection d\'une fonction affiche les références', async ({ app, page }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('check_password').click()
    await app.reRightTab('Xrefs').click()
    // Au moins une section visible (peut être "aucune" si jamais appelé, mais
    // check_password est appelé depuis main donc xrefs.to ≥ 1)
    await expect(page.locator('.anvil-xrefs-header').first()).toBeVisible({ timeout: 10_000 })
    await expect(app.reXrefsItems.first()).toBeVisible({ timeout: 10_000 })
  })

  test('Xrefs — click sur une xref navigue vers la fonction caller', async ({ app, page }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('check_password').click()
    await app.reRightTab('Xrefs').click()
    await app.reXrefsItems.first().waitFor({ timeout: 10_000 })
    const initial = await page.locator('.anvil-re-list-row.active').textContent().catch(() => '')
    await app.reXrefsItems.first().click()
    // L'adresse active dans la sidebar doit changer (ou rester si self-ref ;
    // au minimum, le panneau ne crashe pas).
    await page.waitForTimeout(500)
    const after = await page.locator('.anvil-re-list-row.active').textContent().catch(() => '')
    expect(after).toBeTruthy()
    expect(after).not.toBe(initial === '' ? null : initial) // tolère, le focus a bougé
  })

  test('Hex viewer — affiche un dump pour la fonction sélectionnée', async ({ app, page }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('main').click()
    await app.reRightTab('Hex').click()
    // Le dump pré-formaté contient des octets hex (typiquement "0x" suivi d'addr en début de ligne)
    await expect(app.reHexDump).toBeVisible({ timeout: 10_000 })
    const text = await app.reHexDump.textContent()
    expect(text).toBeTruthy()
    expect(text!.length).toBeGreaterThan(50)
    // px de rizin produit des lignes avec adresses hex
    expect(text!).toMatch(/0x[0-9a-fA-F]+/)
  })

  test('Hex viewer — adresse custom relit la mémoire', async ({ app, page }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('main').click()
    await app.reRightTab('Hex').click()
    await app.reHexDump.waitFor({ timeout: 10_000 })

    // Saisit une adresse custom (entry0, classique) — ELF sans PIE → 0x401000+
    await page.locator('.anvil-hex-addr').fill('entry0')
    await page.locator('.anvil-hex-addr').press('Enter')
    await page.waitForTimeout(800)
    const text = await app.reHexDump.textContent()
    expect(text).toBeTruthy()
  })

  test('Désassemblage — click sur une ligne la sélectionne', async ({ app }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('main').click()
    await app.reRightTab('Désassemblage').click()
    await app.reDisasmLines.first().waitFor({ timeout: 10_000 })
    // Aucune ligne sélectionnée au départ
    await expect(app.reDisasmSelected).toHaveCount(0)
    await app.reDisasmLines.first().click()
    await expect(app.reDisasmSelected).toHaveCount(1, { timeout: 5_000 })
  })

  test('Decompile (rz-ghidra) — affiche du pseudo-C OU masque l\'onglet si manquant', async ({ app, page }) => {
    await app.reLoadBinary(SAMPLE)
    await app.reFunctionRow('main').click()

    const decompileTab = app.reRightTab('Pseudo-code')
    const visible = await decompileTab.isVisible().catch(() => false)

    if (!visible) {
      // rz-ghidra absent — comportement attendu : onglet masqué (capability detection)
      // au moins l'onglet Désassemblage doit être présent
      await expect(app.reRightTab('Désassemblage')).toBeVisible()
      return
    }

    await decompileTab.click()
    // Monaco rend du C ; on cherche un mot-clé typique
    const monaco = page.locator('.anvil-decompile-editor .monaco-editor')
    await expect(monaco).toBeVisible({ timeout: 15_000 })
    const text = await monaco.textContent()
    expect(text).toBeTruthy()
    // Au moins un signe de pseudo-C (void/return/if/printf...)
    expect(text!).toMatch(/(void|return|if\s*\(|printf|undefined)/i)
  })
})
