// Sprint 17-A: smoke tests on the GDB/MI response parsers extracted in Sprint 15.
// Pure functions, no React deps — easiest place to validate the vitest stack works.

import { describe, expect, it } from 'vitest'
import {
  parseExitReason,
  parseFrameLine,
  parseInfoLine,
  parseProgramOutput,
} from './parseGdbResponse'
import type { GdbRawResponse } from '../../api/client'

const wrap = (responses: unknown[]): GdbRawResponse =>
  ({ responses } as unknown as GdbRawResponse)

describe('parseFrameLine', () => {
  it('extracts the line number from a *stopped frame', () => {
    const res = wrap([{ payload: { frame: { line: '42', addr: '0x401000' } } }])
    expect(parseFrameLine(res)).toBe(42)
  })

  it('falls back to stack[0].frame.line', () => {
    const res = wrap([{ payload: { stack: [{ frame: { line: '17' } }] } }])
    expect(parseFrameLine(res)).toBe(17)
  })

  it('falls back to top-level payload.line', () => {
    const res = wrap([{ payload: { line: '5' } }])
    expect(parseFrameLine(res)).toBe(5)
  })

  it('returns 0 when nothing matches', () => {
    expect(parseFrameLine(wrap([]))).toBe(0)
    expect(parseFrameLine(wrap([{ payload: {} }]))).toBe(0)
  })
})

describe('parseExitReason', () => {
  it('detects program exit', () => {
    const res = wrap([{ message: 'stopped', payload: { reason: 'exited-normally' } }])
    expect(parseExitReason(res)).toBe('exited-normally')
  })

  it('detects fatal signal', () => {
    const res = wrap([
      { message: 'stopped', payload: { reason: 'signal-received', 'signal-name': 'SIGSEGV' } },
    ])
    expect(parseExitReason(res)).toBe('signal SIGSEGV')
  })

  it('returns null when running', () => {
    const res = wrap([{ message: 'running', payload: {} }])
    expect(parseExitReason(res)).toBeNull()
  })
})

describe('parseProgramOutput', () => {
  it('strips MI protocol noise from inferior stdout', () => {
    const res = wrap([
      { type: 'target', payload: 'Hello, World!\\n' },
      { type: 'output', payload: 'value=42\\n*stopped,reason="end-stepping-range"' },
    ])
    expect(parseProgramOutput(res)).toEqual(['Hello, World!', 'value=42'])
  })

  it('drops protocol-only lines', () => {
    const res = wrap([{ type: 'target', payload: '*stopped,reason="exited"' }])
    expect(parseProgramOutput(res)).toEqual([])
  })
})

describe('parseInfoLine', () => {
  it('extracts the line from `info line *$pc` console output', () => {
    const res = wrap([
      { type: 'console', payload: 'Line 25 of "program.asm" starts at address 0x401020' },
    ])
    expect(parseInfoLine(res)).toBe(25)
  })

  it('returns 0 if no Line N pattern is present', () => {
    const res = wrap([{ type: 'console', payload: 'No active line.' }])
    expect(parseInfoLine(res)).toBe(0)
  })
})
