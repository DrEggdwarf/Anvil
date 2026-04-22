import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client'
import type { GdbRawResponse } from '../api/client'

export interface TermLine {
  type: 'info' | 'error' | 'step' | 'output'
  text: string
}

export interface RegMap {
  [name: string]: string
}

export interface StackData {
  baseAddr: number
  bytes: number[]
}

export interface MemoryData {
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

// Parse source line number from GDB raw responses (*stopped frame info)
function parseFrameLine(res: GdbRawResponse): number {
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

// Detect if the program has exited from GDB *stopped event
function parseExitReason(res: GdbRawResponse): string | null {
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

// Extract ONLY program stdout (@target records from GDB/MI)
// This filters out GDB internal console messages (register dumps, breakpoint info, etc.)
// Extract program stdout from GDB/MI responses.
// "target" = remote target stdout (@), "output" = local inferior stdout (raw non-MI data).
// Inferior stdout and GDB/MI notifications share the same pipe, so we must
// strip any GDB/MI protocol text that gets concatenated with program output.
function parseProgramOutput(res: GdbRawResponse): string[] {
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
      // Strip GDB/MI protocol data that may be appended to program output
      // (happens when inferior stdout and GDB notification arrive on same line)
      const stripped = part
        .replace(/\*stopped,.*$/, '')
        .replace(/\^done.*$/, '')
        .replace(/\^running.*$/, '')
        .replace(/\^error.*$/, '')
        .replace(/=thread-.*$/, '')
        .replace(/=library-.*$/, '')
        .trim()
      // Skip lines that are entirely GDB/MI protocol or empty after stripping
      if (!stripped) continue
      if (/^\*|^\^|^=|^~|^&|^@/.test(stripped)) continue
      out.push(stripped)
    }
  }
  return out
}

// Parse source line from "info line *$pc" console output
// Example: 'Line 25 of "program.asm" starts at address 0x401020...'
function parseInfoLine(res: GdbRawResponse): number {
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

export function useAnvilSession() {
  const sessionId = useRef<string | null>(null)
  const autoRef = useRef(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const [registers, setRegisters] = useState<RegMap>({})
  const registersRef = useRef<RegMap>({})
  const [prevRegisters, setPrevRegisters] = useState<RegMap>({})
  const [lines, setLines] = useState<TermLine[]>([{ type: 'info', text: 'Pret. Compilez du code pour commencer...' }])
  const [activeLine, setActiveLine] = useState(0)
  const [errorLine, setErrorLine] = useState(0)
  const [stepCount, setStepCount] = useState(0)
  const [compiling, setCompiling] = useState(false)
  const [running, setRunning] = useState(false)
  const [autoStepping, setAutoStepping] = useState(false)
  const [binaryPath, setBinaryPath] = useState<string | null>(null)
  const [stackData, setStackData] = useState<StackData | null>(null)
  const [memoryData, setMemoryData] = useState<MemoryData | null>(null)
  const [memoryRegions, setMemoryRegions] = useState<MemoryRegion[]>([])

  const log = useCallback((type: TermLine['type'], text: string) => {
    setLines(prev => [...prev, { type, text }])
  }, [])

  const clearTerminal = useCallback(() => {
    setLines([])
  }, [])

  // ── Session ────────────────────────────────────────────────

  async function freshSession() {
    // Kill old session if any
    if (sessionId.current) {
      await api.deleteSession(sessionId.current).catch(() => {})
      sessionId.current = null
      setCurrentSessionId(null)
    }
    const s = await api.createSession('gdb')
    sessionId.current = s.id
    setCurrentSessionId(s.id)
    return s.id
  }

  async function ensureSession() {
    if (sessionId.current) return sessionId.current
    const s = await api.createSession('gdb')
    sessionId.current = s.id
    setCurrentSessionId(s.id)
    return s.id
  }

  // ── Compile ────────────────────────────────────────────────

  async function compile(sourceCode: string) {
    setCompiling(true)
    log('info', '> Compilation...')
    try {
      const sid = await ensureSession()
      const res = await api.compileAsm(sid, {
        source_code: sourceCode,
        debug: true,
        link: true,
      })
      if (res.success) {
        log('info', `Compilation OK${res.binary_path ? ` : ${res.binary_path}` : ''}`)
        if (res.stdout) log('output', res.stdout)
        setBinaryPath(res.binary_path)
        setErrorLine(0)
        setActiveLine(0)
        return res
      } else {
        log('error', `Compilation echouee (stage: ${res.stage})`)
        const firstErr = res.errors.find(e => e.line > 0)
        setErrorLine(firstErr?.line || 0)
        setActiveLine(0)
        for (const e of res.errors) {
          log('error', `  L${e.line}: ${e.message}`)
        }
        if (res.stderr) log('error', res.stderr)
        return res
      }
    } catch (e) {
      log('error', `Erreur: ${(e as Error).message}`)
      return null
    } finally {
      setCompiling(false)
    }
  }

  // ── Refresh state from GDB ─────────────────────────────────

  async function refreshRegisters() {
    if (!sessionId.current) return
    try {
      const res = await api.gdbRegisters(sessionId.current)
      const map: RegMap = {}
      if (Array.isArray(res.registers)) {
        for (const r of res.registers) {
          const entry = r as { name?: string; value?: string }
          if (entry.name && entry.value) map[entry.name] = entry.value
        }
      } else if (typeof res.registers === 'object') {
        Object.assign(map, res.registers)
      }
      setPrevRegisters(registersRef.current)
      registersRef.current = map
      setRegisters(map)
    } catch { /* ignore */ }
  }

  async function refreshStack() {
    if (!sessionId.current) return
    try {
      // Read 64 bytes (8 rows of 8) starting at $rsp
      const res = await api.gdbMemory(sessionId.current, '$rsp', 64)
      for (const r of (res.responses || [])) {
        const payload = r.payload as Record<string, unknown> | undefined
        if (!payload) continue
        const memory = payload.memory as Array<{ begin: string; contents: string }> | undefined
        if (!Array.isArray(memory)) continue
        for (const block of memory) {
          const baseAddr = parseInt(block.begin, 16)
          const hex = block.contents
          const bytes: number[] = []
          for (let i = 0; i + 2 <= hex.length; i += 2) {
            bytes.push(parseInt(hex.slice(i, i + 2), 16))
          }
          setStackData({ baseAddr, bytes })
          return
        }
      }
    } catch { /* ignore */ }
  }

  // ── Memory viewer ──────────────────────────────────────────

  async function readMemory(address: string, size = 256) {
    if (!sessionId.current) return
    try {
      const res = await api.gdbMemory(sessionId.current, address, size)
      for (const r of (res.responses || [])) {
        const payload = r.payload as Record<string, unknown> | undefined
        if (!payload) continue
        const memory = payload.memory as Array<{ begin: string; contents: string }> | undefined
        if (!Array.isArray(memory)) continue
        for (const block of memory) {
          const baseAddr = parseInt(block.begin, 16)
          const hex = block.contents
          const bytes: number[] = []
          for (let i = 0; i + 2 <= hex.length; i += 2) {
            bytes.push(parseInt(hex.slice(i, i + 2), 16))
          }
          setMemoryData({ baseAddr, bytes })
          return
        }
      }
    } catch (e) {
      log('error', `Memory read: ${(e as Error).message}`)
    }
  }

  async function writeMemory(address: string, hexData: string) {
    if (!sessionId.current) return
    try {
      await api.gdbWriteMemory(sessionId.current, address, hexData)
      log('info', `Memory write OK: ${address}`)
    } catch (e) {
      log('error', `Memory write: ${(e as Error).message}`)
    }
  }

  async function fetchMemoryMap() {
    if (!sessionId.current) return
    try {
      const res = await api.gdbMemoryMap(sessionId.current)
      const regions: MemoryRegion[] = []
      for (const r of (res.responses || [])) {
        const payload = r.payload
        if (typeof payload !== 'string') continue
        // Parse "info proc mappings" output lines
        // Format: 0x400000 0x401000 0x1000 0x0 /path/to/binary
        const lines = payload.replace(/\\n/g, '\n').split('\n')
        for (const line of lines) {
          const m = line.match(/\s*(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(\S*)?\s*(.*)/)
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
      setMemoryRegions(regions)
    } catch { /* ignore */ }
  }

  // Resolve source line from GDB — tries 3 methods in order
  async function resolveActiveLine(stepRes?: GdbRawResponse): Promise<number> {
    if (!sessionId.current) return 0

    // 1. From step response (*stopped frame.line)
    if (stepRes) {
      const frameLine = parseFrameLine(stepRes)
      if (frameLine > 0) return frameLine
    }

    // 2. From stack-list-frames
    try {
      const stack = await api.gdbStack(sessionId.current, 1)
      const stackLine = parseFrameLine(stack)
      if (stackLine > 0) return stackLine
    } catch { /* ignore */ }

    // 3. From info line *$pc (most reliable for calls/rets)
    try {
      const infoRes = await api.gdbCurrentLine(sessionId.current)
      const infoLine = parseInfoLine(infoRes)
      if (infoLine > 0) return infoLine
    } catch { /* ignore */ }

    return 0
  }

  // ── Build & Run ────────────────────────────────────────────

  async function buildAndRun(sourceCode: string) {
    // Fresh session each run (clean GDB state)
    let sid: string
    try {
      sid = await freshSession()
    } catch (e) {
      log('error', `Session: ${(e as Error).message}`)
      return
    }

    // Compile
    setCompiling(true)
    log('info', '> Compilation...')
    let binPath: string | null = null
    try {
      const res = await api.compileAsm(sid, {
        source_code: sourceCode,
        debug: true,
        link: true,
      })
      if (!res.success) {
        log('error', `Compilation echouee (stage: ${res.stage})`)
        const firstErr = res.errors.find(e => e.line > 0)
        setErrorLine(firstErr?.line || 0)
        setActiveLine(0)
        for (const e of res.errors) log('error', `  L${e.line}: ${e.message}`)
        if (res.stderr) log('error', res.stderr)
        return
      }
      binPath = res.binary_path
      log('info', 'Compilation OK')
      setBinaryPath(binPath)
      setErrorLine(0)
    } catch (e) {
      log('error', `Erreur: ${(e as Error).message}`)
      return
    } finally {
      setCompiling(false)
    }

    if (!binPath) return

    // Load + run to _start
    setRunning(true)
    setStepCount(0)
    setActiveLine(0)
    log('info', '> Chargement GDB...')
    try {
      await api.gdbLoad(sid, binPath)
    } catch (e) {
      log('error', `GDB load: ${(e as Error).message}`)
      setRunning(false)
      return
    }

    try {
      await api.gdbSetBreakpoint(sid, '_start')
    } catch (e) {
      log('error', `Breakpoint _start: ${(e as Error).message}`)
      setRunning(false)
      return
    }

    try {
      log('info', '> Lancement (arret a _start)...')
      const runRes = await api.gdbRun(sid)

      for (const line of parseProgramOutput(runRes)) {
        if (line.trim()) log('output', line)
      }

      // Check if program exited immediately (e.g., crash on syscall)
      const exitReason = parseExitReason(runRes)
      if (exitReason) {
        setActiveLine(0)
        log('info', `Programme termine immediatement (${exitReason})`)
        setRunning(false)
        return
      }

      const frameLine = parseFrameLine(runRes)
      if (frameLine > 0) setActiveLine(frameLine)

      await refreshRegisters()
      await refreshStack()
      log('info', 'Arrete a _start. Utilisez les boutons step pour avancer.')

      // Enable GDB execution recording for reverse stepping (Back button)
      try {
        await api.gdbEnableRecord(sid)
      } catch {
        // Recording may fail (e.g., target doesn't support it) — Back won't work but stepping still does
      }
    } catch (e) {
      log('error', `GDB run: ${(e as Error).message}`)
    } finally {
      setRunning(false)
    }
  }

  // ── Step operations ────────────────────────────────────────

  async function doStep(stepFn: (sid: string) => Promise<GdbRawResponse>, label: string) {
    if (!sessionId.current) return
    setRunning(true)
    try {
      const res = await stepFn(sessionId.current)

      // Check if program exited
      const exitReason = parseExitReason(res)
      if (exitReason) {
        for (const line of parseProgramOutput(res)) {
          if (line.trim()) log('output', line)
        }
        setActiveLine(0)
        log('info', `Programme termine (${exitReason})`)
        setRunning(false)
        return
      }

      // Extract program output (only actual program stdout, not GDB messages)
      for (const line of parseProgramOutput(res)) {
        if (line.trim()) log('output', line)
      }

      // Resolve source line (triple fallback: frame → stack → info line *$pc)
      const frameLine = await resolveActiveLine(res)
      if (frameLine > 0) setActiveLine(frameLine)

      // Log step OUTSIDE state updater to avoid React StrictMode double-invoke
      setStepCount(c => c + 1)
      log('step', label)

      await refreshRegisters()
      await refreshStack()
    } catch (e) {
      const msg = (e as Error).message
      // Detect bridge crash / session gone
      if (msg.includes('BRIDGE_CRASH') || msg.includes('BRIDGE_NOT_READY')) {
        log('error', 'GDB a crashe. Relancez avec Run.')
        sessionId.current = null
      } else {
        log('error', `Step: ${msg}`)
      }
    } finally {
      setRunning(false)
    }
  }

  async function stepInto() { return doStep(api.gdbStepInto, 'Step into') }
  async function stepOver() { return doStep(api.gdbStepOver, 'Step over') }
  async function stepOut() { return doStep(api.gdbStepOut, 'Step out') }
  async function stepBack() { return doStep(api.gdbStepBack, 'Step back') }

  async function continueExec() {
    if (!sessionId.current) return
    setRunning(true)
    try {
      const res = await api.gdbContinue(sessionId.current)
      for (const line of parseProgramOutput(res)) {
        if (line.trim()) log('output', line)
      }
      const exitReason = parseExitReason(res)
      if (exitReason) {
        setActiveLine(0)
        log('info', `Programme termine (${exitReason})`)
        setRunning(false)
        return
      }
      const frameLine = await resolveActiveLine(res)
      if (frameLine > 0) setActiveLine(frameLine)
      await refreshRegisters()
      await refreshStack()
      log('info', 'Continue')
    } catch (e) {
      log('error', `Continue: ${(e as Error).message}`)
    } finally {
      setRunning(false)
    }
  }

  async function stop() {
    if (!sessionId.current) return
    try {
      await api.gdbInterrupt(sessionId.current)
      log('info', 'Interrompu.')
    } catch { /* ignore */ }
    setRunning(false)
  }

  // ── Auto-step (play/pause) ─────────────────────────────────

  async function startAutoStep(delayMs = 500) {
    if (!sessionId.current) return
    autoRef.current = true
    setAutoStepping(true)
    log('info', '> Auto-step demarre')

    while (autoRef.current && sessionId.current) {
      try {
        const res = await api.gdbStepInto(sessionId.current)
        // Check for program exit
        const exitReason = parseExitReason(res)
        if (exitReason) {
          for (const line of parseProgramOutput(res)) {
            if (line.trim()) log('output', line)
          }
          setActiveLine(0)
          log('info', `Programme termine (${exitReason})`)
          autoRef.current = false
          break
        }
        for (const line of parseProgramOutput(res)) {
          if (line.trim()) log('output', line)
        }
        const frameLine = await resolveActiveLine(res)
        if (frameLine > 0) setActiveLine(frameLine)
        setStepCount(c => c + 1)
        await refreshRegisters()
        await refreshStack()
      } catch {
        autoRef.current = false
        break
      }
      await new Promise(r => setTimeout(r, delayMs))
    }

    setAutoStepping(false)
    log('info', 'Auto-step arrete')
  }

  function stopAutoStep() {
    autoRef.current = false
  }

  // ── Breakpoints ────────────────────────────────────────────

  async function setBreakpoint(line: number) {
    if (!sessionId.current) return
    try {
      // Use source line breakpoint format (file:line)
      await api.gdbSetBreakpoint(sessionId.current, `program.asm:${line}`)
    } catch (e) {
      log('error', `BP: ${(e as Error).message}`)
    }
  }

  // ── Cleanup ────────────────────────────────────────────────

  async function destroySessions() {
    autoRef.current = false
    if (sessionId.current) {
      await api.deleteSession(sessionId.current).catch(() => {})
      sessionId.current = null
    }
  }

  return {
    sessionId: currentSessionId,
    registers,
    prevRegisters,
    stackData,
    memoryData,
    memoryRegions,
    lines,
    activeLine,
    errorLine,
    stepCount,
    compiling,
    running,
    autoStepping,
    binaryPath,
    compile,
    buildAndRun,
    stepInto,
    stepOver,
    stepOut,
    stepBack,
    continueExec,
    stop,
    startAutoStep,
    stopAutoStep,
    setBreakpoint,
    clearTerminal,
    destroySessions,
    readMemory,
    writeMemory,
    fetchMemoryMap,
    log,
  }
}
