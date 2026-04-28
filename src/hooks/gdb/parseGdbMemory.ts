// Sprint 17-E: pure parsers for GDB/MI memory responses, extracted from
// useAnvilSession to keep the hook focused on lifecycle. No React deps.

import type { GdbRawResponse } from '../../api/client'

export interface MemoryBlock {
  baseAddr: number
  bytes: number[]
}

export interface MemoryRegion {
  start: string
  end: string
  size: string
  offset: string
  perms: string
  name: string
}

export type RegMap = Record<string, string>

/** Decode a hex stream "DEADBEEF…" into a byte array. */
function hexToBytes(hex: string): number[] {
  const bytes: number[] = []
  for (let i = 0; i + 2 <= hex.length; i += 2) {
    bytes.push(parseInt(hex.slice(i, i + 2), 16))
  }
  return bytes
}

/** Extract the first {begin, contents} memory block from a GDB/MI -data-read-memory response. */
export function parseMemoryBlock(res: GdbRawResponse): MemoryBlock | null {
  for (const r of (res.responses || [])) {
    const payload = r.payload as Record<string, unknown> | undefined
    if (!payload) continue
    const memory = payload.memory as Array<{ begin: string; contents: string }> | undefined
    if (!Array.isArray(memory) || memory.length === 0) continue
    const block = memory[0]
    return { baseAddr: parseInt(block.begin, 16), bytes: hexToBytes(block.contents) }
  }
  return null
}

/** Parse `info proc mappings` console output into structured regions.
 *  Format: 0xSTART 0xEND 0xSIZE 0xOFFSET PERMS NAME */
const _MAPPING_LINE = /\s*(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S*)?\s*(.*)/

export function parseMemoryMap(res: GdbRawResponse): MemoryRegion[] {
  const regions: MemoryRegion[] = []
  for (const r of (res.responses || [])) {
    const payload = r.payload
    if (typeof payload !== 'string') continue
    const lines = payload.replace(/\\n/g, '\n').split('\n')
    for (const line of lines) {
      const m = line.match(_MAPPING_LINE)
      if (m) {
        regions.push({
          start: m[1],
          end: m[2],
          size: m[3],
          offset: m[4],
          perms: m[5] || '',
          name: m[6]?.trim() || m[5] || '',
        })
      }
    }
  }
  return regions
}

/** Normalise the various GDB register list shapes into a {name → value} map.
 *  Some endpoints return [{name, value}, …], some {name: value, …}. */
export function parseRegisters(raw: unknown): RegMap {
  const map: RegMap = {}
  if (Array.isArray(raw)) {
    for (const r of raw) {
      const entry = r as { name?: string; value?: string }
      if (entry.name && entry.value) map[entry.name] = entry.value
    }
  } else if (raw && typeof raw === 'object') {
    Object.assign(map, raw)
  }
  return map
}
