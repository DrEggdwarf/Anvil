// Sprint 17-A: dedicated vitest config to avoid polluting vite.config.ts
// (which targets Tauri dev/build). Uses jsdom for component tests.

import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    // Sprint 18: keep Playwright's tests/e2e/ out of vitest — they need a live
    // backend + browser, run via `npm run e2e` instead.
    exclude: ['node_modules', 'tests/e2e/**', 'dist/**'],
  },
})
