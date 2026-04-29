// Sprint 18: Playwright fixture extending the base test with Anvil-specific
// helpers. Centralises selectors so a UI rename only touches this file, and
// resets backend state between tests so they stay independent.

import { test as base, type Page, type Locator } from '@playwright/test'

const BACKEND = 'http://127.0.0.1:8000'

export interface AnvilFixtures {
  /** Page-scoped helper exposing every Anvil locator used in specs. */
  app: AnvilApp
}

/** Wraps a Page with the Anvil-specific selectors and small workflow helpers. */
export class AnvilApp {
  constructor(public readonly page: Page) {}

  // ── Navigation / mode switching ──────────────────────────
  modeButton(mode: 'ASM' | 'RE' | 'Pwn' | 'Debug' | 'Firmware' | 'Protocols'): Locator {
    return this.page.getByRole('button', { name: new RegExp(`^${mode}$`) })
  }
  async switchMode(mode: 'ASM' | 'RE' | 'Pwn' | 'Debug' | 'Firmware' | 'Protocols') {
    await this.modeButton(mode).click()
  }

  // ── ASM toolbar ──────────────────────────────────────────
  get runButton(): Locator { return this.page.getByRole('button', { name: /Run/ }) }
  get stepIntoButton(): Locator { return this.page.getByRole('button', { name: /Into/ }) }
  get stepOverButton(): Locator { return this.page.getByRole('button', { name: /Over/ }) }
  get stepOutButton(): Locator { return this.page.getByRole('button', { name: /Out/ }) }
  get stepBackButton(): Locator { return this.page.getByRole('button', { name: /Back/ }) }
  get stepNextButton(): Locator { return this.page.getByRole('button', { name: /Next/ }) }
  get assemblerSelect(): Locator { return this.page.locator('select.anvil-asm-select') }

  // ── ASM editor (custom textarea overlay) ─────────────────
  get editorTextarea(): Locator { return this.page.locator('.anvil-ed-textarea') }
  async setEditorContent(code: string) {
    // Playwright's fill() doesn't reliably trigger React's synthetic onChange on
    // controlled textareas in headless Chrome. Use the native setter hack to
    // properly dispatch the input event and force a React re-render.
    await this.page.evaluate((newCode) => {
      const el = document.querySelector('.anvil-ed-textarea') as HTMLTextAreaElement
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!
      setter.call(el, newCode)
      el.dispatchEvent(new Event('input', { bubbles: true }))
    }, code)
    // Wait for the custom editor to re-render gutter lines after React state update.
    await this.page.locator('.anvil-ed-gutter-line').first().waitFor({ timeout: 15_000 })
  }

  // ── Panels ───────────────────────────────────────────────
  get registersPane(): Locator { return this.page.locator('.anvil-registers-pane, .anvil-registers') }
  get terminal(): Locator { return this.page.locator('.anvil-terminal') }
  get stackPanel(): Locator { return this.page.locator('.anvil-stack-panel') }
  get memoryPanel(): Locator { return this.page.locator('.anvil-memory-panel') }
  registerCard(name: string): Locator {
    return this.page.locator(`.anvil-reg-card`, { has: this.page.getByText(new RegExp(`^${name}$`)) })
  }

  // ── Pwn mode ─────────────────────────────────────────────
  get pwnDropZone(): Locator { return this.page.locator('.anvil-pwn-dropzone, .anvil-pwn-binary-zone') }
  pwnBottomTab(name: 'Terminal' | 'Symbols' | 'GOT' | 'PLT' | 'Strings'): Locator {
    return this.page.getByRole('button', { name: new RegExp(name, 'i') })
  }
  pwnToolButton(name: 'Cyclic' | 'ROP' | 'Format String' | 'Shellcraft' | 'Asm'): Locator {
    return this.page.getByRole('button', { name: new RegExp(name, 'i') })
  }
  get pwnFilterInput(): Locator { return this.page.locator('input.anvil-pwn-filter') }

  // ── Workflow helpers (compose multiple steps) ────────────

  /** Waits until the terminal contains a line matching `pattern`. */
  async waitForTerminalLine(pattern: string | RegExp, timeoutMs = 15_000) {
    await this.terminal.getByText(pattern).first().waitFor({ timeout: timeoutMs })
  }

  /** Waits until the active step counter reaches `n` (visible in status bar). */
  async waitForStepCount(n: number, timeoutMs = 10_000) {
    await this.page.getByText(new RegExp(`Step:\\s*${n}\\b`)).waitFor({ timeout: timeoutMs })
  }
}

/** Ask the backend to forget every active session — keeps tests independent. */
async function resetBackendState(): Promise<void> {
  try {
    const list = await fetch(`${BACKEND}/api/sessions`).then(r => r.json()).catch(() => null)
    const sessions: { id: string }[] = list?.sessions ?? []
    await Promise.all(
      sessions.map(s =>
        fetch(`${BACKEND}/api/sessions/${s.id}`, { method: 'DELETE' }).catch(() => undefined),
      ),
    )
  } catch { /* backend unreachable — webServer fixture will report it */ }
}

export const test = base.extend<AnvilFixtures>({
  app: async ({ page }, use) => {
    await resetBackendState()
    await page.goto('/')
    // Wait for the ASM editor textarea to be mounted before handing off to tests.
    // In CI the React app takes longer to hydrate than locally.
    await page.locator('.anvil-ed-textarea').waitFor({ timeout: 30_000 })
    await use(new AnvilApp(page))
  },
})

export { expect } from '@playwright/test'
