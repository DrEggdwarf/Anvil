// Sprint 17-A: vitest setup — runs once before all tests.
// Adds jest-dom matchers and clears DOM between tests.

import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})
