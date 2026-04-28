// Pure GDB/MI response parsers — extracted from useAnvilSession.ts during Sprint 15
// (ADR-018: hook root must orchestrate, not parse). These have no React deps and
// can be unit-tested in isolation. Keep stateless.

import type { GdbRawResponse } from '../../api/client'

// Parse source line number from GDB raw responses (*stopped frame info).
export function parseFrameLine(res: GdbRawResponse): number {
  for (const r of (res.responses || [])) {
    const payload = r.payload as Record<string, unknown> | undefined
    if (!payload || typeof payload !== 'object') continue

    // 1. Standard *stopped event: payload.frame.line
    if (payload.frame && typeof payload.frame === 'object') {
      const frame = payload.frame as Record<string, unknown>
      if (frame.line) return parseInt(String(frame.line), 10)
    }

    // 2. Stack-list-frames result: payload.stack[0].frame.line
    const stack = payload.stack as unknown[] | undefined
    if (Array.isArray(stack) && stack.length > 0) {
      const entry = stack[0] as Record<string, unknown>
      const frame = (entry?.frame ?? entry) as Record<string, unknown>
      if (frame?.line) return parseInt(String(frame.line), 10)
    }

    // 3. Top-level line field (some GDB versions)
    if (payload.line) return parseInt(String(payload.line), 10)
  }
  return 0
}

// Detect if the program has exited from GDB *stopped event.
export function parseExitReason(res: GdbRawResponse): string | null {
  for (const r of (res.responses || [])) {
    const msg = r.message as string | undefined
    const payload = r.payload as Record<string, unknown> | undefined
    if (msg === 'stopped' && payload?.reason) {
      const reason = String(payload.reason)
      if (reason.startsWith('exited')) return reason
      if (reason === 'signal-received') {
        const sigName = payload['signal-name'] as string | undefined
        return `signal ${sigName || 'unknown'}`
      }
    }
  }
  return null
}

// Extract program stdout from GDB/MI responses.
// "target" = remote target stdout (@), "output" = local inferior stdout (raw non-MI data).
// Inferior stdout and GDB/MI notifications share the same pipe, so we must strip any
// GDB/MI protocol text concatenated with program output.
export function parseProgramOutput(res: GdbRawResponse): string[] {
  const out: string[] = []
  for (const r of (res.responses || [])) {
    const type = r.type as string | undefined
    if (type !== 'target' && type !== 'output') continue
    const payload = r.payload
    if (typeof payload !== 'string' || !payload) continue
    const cleaned = payload
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\"/g, '"')
      .replace(/\n+$/, '')
    if (!cleaned) continue
    for (const part of cleaned.split('\n')) {
      if (!part) continue
      const stripped = part
        .replace(/\*stopped,.*$/, '')
        .replace(/\^done.*$/, '')
        .replace(/\^running.*$/, '')
        .replace(/\^error.*$/, '')
        .replace(/=thread-.*$/, '')
        .replace(/=library-.*$/, '')
        .trim()
      if (!stripped) continue
      if (/^\*|^\^|^=|^~|^&|^@/.test(stripped)) continue
      out.push(stripped)
    }
  }
  return out
}

// Parse source line from "info line *$pc" console output.
// Example: 'Line 25 of "program.asm" starts at address 0x401020...'
export function parseInfoLine(res: GdbRawResponse): number {
  for (const r of (res.responses || [])) {
    const type = r.type as string | undefined
    if (type !== 'console') continue
    const payload = r.payload
    if (typeof payload !== 'string') continue
    const match = payload.match(/Line\s+(\d+)\s+of/)
    if (match) return parseInt(match[1], 10)
  }
  return 0
}
