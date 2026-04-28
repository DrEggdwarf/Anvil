// Sprint 18 e2e — Pwn mode security: when a request escapes the workspace,
// the backend rejects with HTTP 403 PATH_BLOCKED. We exercise that contract
// directly via fetch, since the UI never lets the user reach those payloads.
//
// Pairs with the unit-level test_pwn_api.py — this is the live counterpart.

import { test, expect } from '../fixtures/anvil'

const BACKEND = 'http://127.0.0.1:8000'

interface SessionCreated {
  id: string
  token: string
}

async function createPwnSession(): Promise<SessionCreated> {
  const r = await fetch(`${BACKEND}/api/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ bridge_type: 'pwn' }),
  })
  expect(r.ok).toBe(true)
  return r.json()
}

test.describe('Pwn security guards (live backend)', () => {
  test('elf/checksec rejects an absolute path outside the workspace', async () => {
    const s = await createPwnSession()
    const r = await fetch(
      `${BACKEND}/api/pwn/${s.id}/elf/checksec?path=${encodeURIComponent('/etc/passwd')}`,
    )
    expect(r.status).toBe(403)
    const body = await r.json()
    expect(body.code).toBe('PATH_BLOCKED')
  })

  test('upload rejects a filename with path separators (Pydantic 422)', async () => {
    const s = await createPwnSession()
    const r = await fetch(`${BACKEND}/api/pwn/${s.id}/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: '../escape.bin', data_b64: 'AA==' }),
    })
    expect(r.status).toBe(422)
  })

  test('compile rejects an unsupported language', async () => {
    const s = await createPwnSession()
    const r = await fetch(`${BACKEND}/api/pwn/${s.id}/compile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: 'foo.pl', language: 'perl' }),
    })
    expect(r.status).toBe(400)
    const body = await r.json()
    expect(body.code).toBe('UNSUPPORTED_LANGUAGE')
  })
})
