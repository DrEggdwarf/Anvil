// Sprint 17-E: useAnvilSession is the orchestrator for the ASM-mode GDB session.
// Memory-response parsing lives in hooks/gdb/parseGdbMemory.ts; pure GDB/MI
// parsers live in hooks/gdb/parseGdbResponse.ts. Every public function is wrapped
// in useCallback so consumers (RegistersPane, StackPanel, MemoryPanel, exec
// toolbar) can safely use React.memo without busting on every render.

import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client'
import type { GdbRawResponse } from '../api/client'
import {
  parseExitReason,
  parseFrameLine,
  parseInfoLine,
  parseProgramOutput,
} from './gdb/parseGdbResponse'
import {
  parseMemoryBlock,
  parseMemoryMap,
  parseRegisters,
  type MemoryRegion,
  type RegMap,
} from './gdb/parseGdbMemory'

export interface TermLine {
  type: 'info' | 'error' | 'step' | 'output'
  text: string
}

export interface StackData {
  baseAddr: number
  bytes: number[]
}

export interface MemoryData {
  baseAddr: number
  bytes: number[]
}

export type { RegMap, MemoryRegion }

const STACK_BYTES = 64       // 8 rows × 8 bytes — enough for a typical frame
const MEMORY_DEFAULT = 256   // bytes read by readMemory() if size omitted
const AUTOSTEP_DEFAULT_MS = 500

export function useAnvilSession() {
  const sessionId = useRef<string | null>(null)
  const autoRef = useRef(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  const [registers, setRegisters] = useState<RegMap>({})
  const registersRef = useRef<RegMap>({})
  const [prevRegisters, setPrevRegisters] = useState<RegMap>({})
  const [lines, setLines] = useState<TermLine[]>([
    { type: 'info', text: 'Pret. Compilez du code pour commencer...' },
  ])
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

  const freshSession = useCallback(async () => {
    if (sessionId.current) {
      await api.deleteSession(sessionId.current).catch(() => {})
      sessionId.current = null
      setCurrentSessionId(null)
    }
    const s = await api.createSession('gdb')
    sessionId.current = s.id
    setCurrentSessionId(s.id)
    return s.id
  }, [])

  const ensureSession = useCallback(async () => {
    if (sessionId.current) return sessionId.current
    const s = await api.createSession('gdb')
    sessionId.current = s.id
    setCurrentSessionId(s.id)
    return s.id
  }, [])

  // ── Refresh state from GDB ─────────────────────────────────

  const refreshRegisters = useCallback(async () => {
    if (!sessionId.current) return
    try {
      const res = await api.gdbRegisters(sessionId.current)
      const map = parseRegisters(res.registers)
      setPrevRegisters(registersRef.current)
      registersRef.current = map
      setRegisters(map)
    } catch { /* ignore — a transient failure shouldn't blank the panel */ }
  }, [])

  const refreshStack = useCallback(async () => {
    if (!sessionId.current) return
    try {
      const res = await api.gdbMemory(sessionId.current, '$rsp', STACK_BYTES)
      const block = parseMemoryBlock(res)
      if (block) setStackData(block)
    } catch { /* ignore */ }
  }, [])

  // ── Memory viewer ──────────────────────────────────────────

  const readMemory = useCallback(async (address: string, size = MEMORY_DEFAULT) => {
    if (!sessionId.current) return
    try {
      const res = await api.gdbMemory(sessionId.current, address, size)
      const block = parseMemoryBlock(res)
      if (block) setMemoryData(block)
    } catch (e) {
      log('error', `Memory read: ${(e as Error).message}`)
    }
  }, [log])

  const writeMemory = useCallback(async (address: string, hexData: string) => {
    if (!sessionId.current) return
    try {
      await api.gdbWriteMemory(sessionId.current, address, hexData)
      log('info', `Memory write OK: ${address}`)
    } catch (e) {
      log('error', `Memory write: ${(e as Error).message}`)
    }
  }, [log])

  const fetchMemoryMap = useCallback(async () => {
    if (!sessionId.current) return
    try {
      const res = await api.gdbMemoryMap(sessionId.current)
      setMemoryRegions(parseMemoryMap(res))
    } catch { /* ignore */ }
  }, [])

  // Resolve the source line of the current PC. Tries 3 sources in priority order:
  //   1. *stopped frame.line from the step response
  //   2. -stack-list-frames result
  //   3. console output of `info line *$pc`
  const resolveActiveLine = useCallback(async (stepRes?: GdbRawResponse): Promise<number> => {
    if (!sessionId.current) return 0

    if (stepRes) {
      const frameLine = parseFrameLine(stepRes)
      if (frameLine > 0) return frameLine
    }
    try {
      const stack = await api.gdbStack(sessionId.current, 1)
      const stackLine = parseFrameLine(stack)
      if (stackLine > 0) return stackLine
    } catch { /* ignore */ }
    try {
      const infoRes = await api.gdbCurrentLine(sessionId.current)
      const infoLine = parseInfoLine(infoRes)
      if (infoLine > 0) return infoLine
    } catch { /* ignore */ }
    return 0
  }, [])

  // ── Compile ────────────────────────────────────────────────

  const compile = useCallback(async (
    sourceCode: string,
    assembler: 'nasm' | 'gas' | 'fasm' = 'nasm',
  ) => {
    setCompiling(true)
    log('info', '> Compilation...')
    try {
      const sid = await ensureSession()
      const res = await api.compileAsm(sid, {
        source_code: sourceCode,
        assembler,
        debug: true,
        link: true,
      })
      if (res.success) {
        log('info', `Compilation OK${res.binary_path ? ` : ${res.binary_path}` : ''}`)
        if (res.stdout) log('output', res.stdout)
        setBinaryPath(res.binary_path)
        setErrorLine(0)
        setActiveLine(0)
      } else {
        log('error', `Compilation echouee (stage: ${res.stage})`)
        const firstErr = res.errors.find(e => e.line > 0)
        setErrorLine(firstErr?.line || 0)
        setActiveLine(0)
        for (const e of res.errors) log('error', `  L${e.line}: ${e.message}`)
        if (res.stderr) log('error', res.stderr)
      }
      return res
    } catch (e) {
      log('error', `Erreur: ${(e as Error).message}`)
      return null
    } finally {
      setCompiling(false)
    }
  }, [ensureSession, log])

  // ── Build & Run ────────────────────────────────────────────

  const buildAndRun = useCallback(async (
    sourceCode: string,
    assembler: 'nasm' | 'gas' | 'fasm' = 'nasm',
  ) => {
    let sid: string
    try {
      sid = await freshSession()
    } catch (e) {
      log('error', `Session: ${(e as Error).message}`)
      return
    }

    setCompiling(true)
    log('info', '> Compilation...')
    let binPath: string | null = null
    try {
      const res = await api.compileAsm(sid, {
        source_code: sourceCode,
        assembler,
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

      // Enable execution recording so the Back button can reverse-step.
      // Some targets don't support it — log only the failure that matters.
      try {
        await api.gdbEnableRecord(sid)
      } catch { /* recording optional */ }
    } catch (e) {
      log('error', `GDB run: ${(e as Error).message}`)
    } finally {
      setRunning(false)
    }
  }, [freshSession, log, refreshRegisters, refreshStack])

  // ── Step operations ────────────────────────────────────────

  const doStep = useCallback(async (
    stepFn: (sid: string) => Promise<GdbRawResponse>,
    label: string,
  ) => {
    if (!sessionId.current) return
    setRunning(true)
    try {
      const res = await stepFn(sessionId.current)

      const exitReason = parseExitReason(res)
      if (exitReason) {
        for (const line of parseProgramOutput(res)) {
          if (line.trim()) log('output', line)
        }
        setActiveLine(0)
        log('info', `Programme termine (${exitReason})`)
        return
      }

      for (const line of parseProgramOutput(res)) {
        if (line.trim()) log('output', line)
      }

      const frameLine = await resolveActiveLine(res)
      if (frameLine > 0) setActiveLine(frameLine)

      // setStepCount + log outside the same updater to avoid double-invoke under StrictMode.
      setStepCount(c => c + 1)
      log('step', label)

      await refreshRegisters()
      await refreshStack()
    } catch (e) {
      const msg = (e as Error).message
      if (msg.includes('BRIDGE_CRASH') || msg.includes('BRIDGE_NOT_READY')) {
        log('error', 'GDB a crashe. Relancez avec Run.')
        sessionId.current = null
      } else {
        log('error', `Step: ${msg}`)
      }
    } finally {
      setRunning(false)
    }
  }, [log, refreshRegisters, refreshStack, resolveActiveLine])

  const stepInto = useCallback(() => doStep(api.gdbStepInto, 'Step into'), [doStep])
  const stepOver = useCallback(() => doStep(api.gdbStepOver, 'Step over'), [doStep])
  const stepOut = useCallback(() => doStep(api.gdbStepOut, 'Step out'), [doStep])
  const stepBack = useCallback(() => doStep(api.gdbStepBack, 'Step back'), [doStep])

  const continueExec = useCallback(async () => {
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
  }, [log, refreshRegisters, refreshStack, resolveActiveLine])

  const stop = useCallback(async () => {
    if (!sessionId.current) return
    try {
      await api.gdbInterrupt(sessionId.current)
      log('info', 'Interrompu.')
    } catch { /* ignore */ }
    setRunning(false)
  }, [log])

  // ── Auto-step (play/pause) ─────────────────────────────────

  const startAutoStep = useCallback(async (delayMs = AUTOSTEP_DEFAULT_MS) => {
    if (!sessionId.current) return
    autoRef.current = true
    setAutoStepping(true)
    log('info', '> Auto-step demarre')

    while (autoRef.current && sessionId.current) {
      try {
        const res = await api.gdbStepInto(sessionId.current)
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
  }, [log, refreshRegisters, refreshStack, resolveActiveLine])

  const stopAutoStep = useCallback(() => {
    autoRef.current = false
  }, [])

  // ── Breakpoints ────────────────────────────────────────────

  const setBreakpoint = useCallback(async (line: number) => {
    if (!sessionId.current) return
    try {
      await api.gdbSetBreakpoint(sessionId.current, `program.asm:${line}`)
    } catch (e) {
      log('error', `BP: ${(e as Error).message}`)
    }
  }, [log])

  // ── Cleanup ────────────────────────────────────────────────

  const destroySessions = useCallback(async () => {
    autoRef.current = false
    if (sessionId.current) {
      await api.deleteSession(sessionId.current).catch(() => {})
      sessionId.current = null
    }
  }, [])

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
