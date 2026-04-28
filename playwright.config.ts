// Sprint 18: Playwright config — runs vitest's e2e companion across the live
// frontend + backend. Both servers are spawned via `webServer` so Playwright
// waits for HTTP 200 on /api/health and on the Vite root before starting tests.

import { defineConfig, devices } from '@playwright/test'

const HEADLESS = process.env.PLAYWRIGHT_HEADED !== '1'
const IS_CI = !!process.env.CI

export default defineConfig({
  testDir: './tests/e2e',
  // One browser tab per test → straightforward state isolation.
  fullyParallel: false,
  // CI is unforgiving on flake; locally we tolerate one retry to absorb a
  // late uvicorn boot or a slow gdb spawn.
  retries: IS_CI ? 2 : 1,
  workers: IS_CI ? 1 : undefined,
  // Keep individual specs under 90s — anything longer points to a real bug.
  timeout: 90_000,
  expect: { timeout: 10_000 },

  reporter: IS_CI ? [['github'], ['list']] : [['list'], ['html', { open: 'never' }]],

  use: {
    baseURL: 'http://localhost:1420',
    trace: IS_CI ? 'on-first-retry' : 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: IS_CI ? 'retain-on-failure' : 'off',
    actionTimeout: 8_000,
    navigationTimeout: 20_000,
  },

  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],

  // Backend (8000) and Vite (1420) are both required.
  // `reuseExistingServer: !IS_CI` lets local devs keep their dev servers up
  // and re-run tests without paying the cold-start tax every time.
  webServer: [
    {
      command: 'uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level warning',
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: !IS_CI,
      timeout: 30_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:1420',
      reuseExistingServer: !IS_CI,
      timeout: 30_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],

  // Honour PLAYWRIGHT_HEADED=1 to debug a failing spec interactively.
  ...(HEADLESS ? {} : { use: { ...{ headless: false } } }),
})
