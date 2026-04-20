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

// Parse source line number from GDB raw responses (*stopped frame info)
function parseFrameLine(res: GdbRawResponse): number {
  for (const r of (res.responses || [])) {
    // GDB/MI *stopped event includes payload with frame.line
    const payload = r.payload as Record<string, unknown> | undefined
    if (payload?.frame) {
      const frame = payload.frame as Record<string, unknown>
      if (frame.line) return parseInt(String(frame.line), 10)
    }
    // Also check top-level line field
    if (payload?.line) return parseInt(String(payload.line), 10)
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

// Extract console + program output from GDB raw responses
// pygdbmi types: "console" = GDB messages, "target" = program stdout, "output" = GDB output
function parseConsoleOutput(res: GdbRawResponse): string[] {
  const out: string[] = []
  for (const r of (res.responses || [])) {
    const type = r.type as string | undefined
    const payload = r.payload as string | undefined
    if ((type === 'console' || type === 'output' || type === 'target') && payload) {
      out.push(payload.replace(/\\n$/, '').replace(/\\n/g, '\n'))
    }
  }
  return out
}

export function useAnvilSession() {
  const sessionId = useRef<string | null>(null)
  const autoRef = useRef(false)

  const [registers, setRegisters] = useState<RegMap>({})
  const [lines, setLines] = useState<TermLine[]>([{ type: 'info', text: 'Pret. Compilez du code pour commencer...' }])
  const [activeLine, setActiveLine] = useState(0)
  const [errorLine, setErrorLine] = useState(0)
  const [stepCount, setStepCount] = useState(0)
  const [compiling, setCompiling] = useState(false)
  const [running, setRunning] = useState(false)
  const [autoStepping, setAutoStepping] = useState(false)
  const [binaryPath, setBinaryPath] = useState<string | null>(null)

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
    }
    const s = await api.createSession('gdb')
    sessionId.current = s.id
    return s.id
  }

  async function ensureSession() {
    if (sessionId.current) return sessionId.current
    const s = await api.createSession('gdb')
    sessionId.current = s.id
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

  async function refreshState() {
    if (!sessionId.current) return
    // Get registers
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
      setRegisters(map)
    } catch { /* ignore */ }

    // Get current frame to find source line
    try {
      const stack = await api.gdbStack(sessionId.current, 1)
      for (const r of (stack.responses || [])) {
        const payload = r.payload as Record<string, unknown> | undefined
        const stackFrames = payload?.stack as Array<Record<string, unknown>> | undefined
        if (stackFrames?.[0]) {
          const frame = stackFrames[0].frame
            ? (stackFrames[0].frame as Record<string, unknown>)
            : stackFrames[0]
          if (frame?.line) {
            setActiveLine(parseInt(String(frame.line), 10))
            return
          }
        }
      }
    } catch { /* ignore */ }
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

      for (const line of parseConsoleOutput(runRes)) {
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

      await refreshState()
      log('info', 'Arrete a _start. Utilisez les boutons step pour avancer.')
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
        for (const line of parseConsoleOutput(res)) {
          if (line.trim()) log('output', line)
        }
        setActiveLine(0)
        log('info', `Programme termine (${exitReason})`)
        setRunning(false)
        return
      }

      // Extract console output (program prints)
      for (const line of parseConsoleOutput(res)) {
        if (line.trim()) log('output', line)
      }

      // Parse frame line
      const frameLine = parseFrameLine(res)
      if (frameLine > 0) setActiveLine(frameLine)

      setStepCount(c => {
        log('step', `${label} (${c + 1})`)
        return c + 1
      })
      await refreshState()
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

  async function continueExec() {
    if (!sessionId.current) return
    setRunning(true)
    try {
      const res = await api.gdbContinue(sessionId.current)
      for (const line of parseConsoleOutput(res)) {
        if (line.trim()) log('output', line)
      }
      const exitReason = parseExitReason(res)
      if (exitReason) {
        setActiveLine(0)
        log('info', `Programme termine (${exitReason})`)
        setRunning(false)
        return
      }
      const frameLine = parseFrameLine(res)
      if (frameLine > 0) setActiveLine(frameLine)
      await refreshState()
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
          for (const line of parseConsoleOutput(res)) {
            if (line.trim()) log('output', line)
          }
          setActiveLine(0)
          log('info', `Programme termine (${exitReason})`)
          autoRef.current = false
          break
        }
        for (const line of parseConsoleOutput(res)) {
          if (line.trim()) log('output', line)
        }
        const frameLine = parseFrameLine(res)
        if (frameLine > 0) setActiveLine(frameLine)
        setStepCount(c => c + 1)
        await refreshState()
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
    registers,
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
    continueExec,
    stop,
    startAutoStep,
    stopAutoStep,
    setBreakpoint,
    clearTerminal,
    destroySessions,
    log,
  }
}
