// Sprint 17-E: tests for parseMemoryBlock / parseMemoryMap / parseRegisters
// extracted from useAnvilSession.

import { describe, expect, it } from 'vitest'
import {
  parseMemoryBlock,
  parseMemoryMap,
  parseRegisters,
} from './parseGdbMemory'
import type { GdbRawResponse } from '../../api/client'

const wrap = (responses: unknown[]): GdbRawResponse =>
  ({ responses } as unknown as GdbRawResponse)

describe('parseMemoryBlock', () => {
  it('decodes a single memory block', () => {
    const res = wrap([
      { payload: { memory: [{ begin: '0x7fff1000', contents: 'deadbeef' }] } },
    ])
    expect(parseMemoryBlock(res)).toEqual({
      baseAddr: 0x7fff1000,
      bytes: [0xde, 0xad, 0xbe, 0xef],
    })
  })

  it('returns null when no memory payload is present', () => {
    expect(parseMemoryBlock(wrap([{ payload: {} }]))).toBeNull()
    expect(parseMemoryBlock(wrap([]))).toBeNull()
  })
})

describe('parseMemoryMap', () => {
  it('extracts regions from `info proc mappings` console output', () => {
    const res = wrap([
      {
        type: 'console',
        payload:
          '0x400000 0x401000 0x1000 0x0 r-xp /usr/bin/test\\n' +
          '0x401000 0x402000 0x1000 0x1000 r--p /usr/bin/test',
      },
    ])
    const regions = parseMemoryMap(res)
    expect(regions).toHaveLength(2)
    expect(regions[0]).toMatchObject({ start: '0x400000', end: '0x401000', perms: 'r-xp' })
    expect(regions[1]).toMatchObject({ start: '0x401000', perms: 'r--p' })
  })

  it('returns empty when no mapping lines are matched', () => {
    expect(parseMemoryMap(wrap([{ payload: 'No mappings.' }]))).toEqual([])
  })
})

describe('parseRegisters', () => {
  it('handles array shape [{name, value}, …]', () => {
    const map = parseRegisters([
      { name: 'rax', value: '0x42' },
      { name: 'rip', value: '0x401000' },
    ])
    expect(map).toEqual({ rax: '0x42', rip: '0x401000' })
  })

  it('handles object shape {name: value, …}', () => {
    const map = parseRegisters({ rbx: '0xff', rsp: '0x7fff1000' })
    expect(map).toEqual({ rbx: '0xff', rsp: '0x7fff1000' })
  })

  it('skips array entries without name or value', () => {
    const map = parseRegisters([
      { name: 'rax', value: '0x42' },
      { name: 'rbx' },           // missing value
      { value: '0xff' },         // missing name
    ])
    expect(map).toEqual({ rax: '0x42' })
  })

  it('returns an empty map for null/undefined input', () => {
    expect(parseRegisters(null)).toEqual({})
    expect(parseRegisters(undefined)).toEqual({})
  })
})
