import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client'
import type { RizinFunction, RizinString, RizinImport, RizinExport, RizinBinaryInfo } from '../types/re'

export interface ReLogLine {
  type: 'info' | 'error' | 'ok'
  text: string
}

export interface LoadingStep {
  id: string
  label: string
  status: 'pending' | 'running' | 'done' | 'error'
}

export function useRizinSession() {
  const sessionIdRef = useRef<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  // Binary state
  const [binaryPath, setBinaryPath] = useState<string | null>(null)
  const [opening, setOpening] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState<string | null>(null)
  const [analyzed, setAnalyzed] = useState(false)
  const [binaryInfo, setBinaryInfo] = useState<RizinBinaryInfo | null>(null)

  // Loading steps (shown during openBinary pipeline)
  const [loadingSteps, setLoadingSteps] = useState<LoadingStep[]>([])

  // Sidebar data
  const [functions, setFunctions] = useState<RizinFunction[]>([])
  const [strings, setStrings] = useState<RizinString[]>([])
  const [imports, setImports] = useState<RizinImport[]>([])
  const [exports, setExports] = useState<RizinExport[]>([])

  // Navigation state
  const [currentAddress, setCurrentAddress] = useState<string | null>(null)
  const [currentFunction, setCurrentFunction] = useState<RizinFunction | null>(null)

  // Log
  const [log, setLog] = useState<ReLogLine[]>([])

  const pushLog = useCallback((type: ReLogLine['type'], text: string) => {
    setLog(prev => [...prev.slice(-99), { type, text }])
  }, [])

  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionIdRef.current) return sessionIdRef.current
    const s = await api.createSession('rizin')
    sessionIdRef.current = s.id
    setSessionId(s.id)
    return s.id
  }, [])

  const destroySession = useCallback(async () => {
    if (!sessionIdRef.current) return
    try { await api.deleteSession(sessionIdRef.current) } catch { /* ignore */ }
    sessionIdRef.current = null
    setSessionId(null)
    setBinaryPath(null)
    setOpening(false)
    setOpenError(null)
    setAnalyzeError(null)
    setAnalyzed(false)
    setFunctions([])
    setStrings([])
    setImports([])
    setExports([])
    setBinaryInfo(null)
    setCurrentAddress(null)
    setCurrentFunction(null)
    setLoadingSteps([])
    setLog([])
  }, [])

  // Full pipeline: open + auto-analyze + load symbols
  const openBinary = useCallback(async (path: string) => {
    setOpening(true)
    setOpenError(null)
    setAnalyzeError(null)
    setBinaryPath(null)
    setAnalyzed(false)
    setFunctions([])
    setBinaryInfo(null)
    setCurrentAddress(null)
    setCurrentFunction(null)

    const mark = (id: string, status: LoadingStep['status']) =>
      setLoadingSteps(prev => prev.map(s => s.id === id ? { ...s, status } : s))

    setLoadingSteps([
      { id: 'session',  label: 'Initialisation de la session', status: 'pending' },
      { id: 'load',     label: 'Chargement du binaire',         status: 'pending' },
      { id: 'analyze',  label: 'Analyse des fonctions (aaa)',   status: 'pending' },
      { id: 'symbols',  label: 'Extraction des symboles',       status: 'pending' },
    ])

    try {
      mark('session', 'running')
      const sid = await ensureSession()
      mark('session', 'done')

      mark('load', 'running')
      await api.reOpenBinary(sid, path)
      setBinaryPath(path)
      mark('load', 'done')

      mark('analyze', 'running')
      setAnalyzing(true)
      await api.reAnalyze(sid, 'aaa')
      setAnalyzed(true)
      setAnalyzing(false)
      mark('analyze', 'done')

      mark('symbols', 'running')
      const [funcs, info] = await Promise.all([
        api.reFunctions(sid),
        api.reBinaryInfo(sid),
      ])
      setFunctions(funcs)
      setBinaryInfo(info)
      mark('symbols', 'done')

      if (funcs.length > 0) {
        const main = funcs.find(f => f.name === 'main' || f.name === 'dbg.main') ?? funcs[0]
        const addr = `0x${main.offset.toString(16)}`
        setCurrentAddress(addr)
        setCurrentFunction(main)
      }

      pushLog('ok', `${path.split('/').pop()} — ${funcs.length} fonctions`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setOpenError(msg)
      setLoadingSteps(prev => prev.map(s => s.status === 'running' ? { ...s, status: 'error' } : s))
      pushLog('error', `Échec: ${msg}`)
    } finally {
      setOpening(false)
      setAnalyzing(false)
    }
  }, [ensureSession, pushLog])

  // Re-analysis (called from topbar, doesn't show full loading overlay)
  const analyze = useCallback(async (level = 'aaa') => {
    const sid = sessionIdRef.current
    if (!sid) return
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      await api.reAnalyze(sid, level)
      setAnalyzed(true)
      const [funcs, info] = await Promise.all([
        api.reFunctions(sid),
        api.reBinaryInfo(sid),
      ])
      setFunctions(funcs)
      setBinaryInfo(info)
      pushLog('ok', `Réanalyse terminée — ${funcs.length} fonctions`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setAnalyzeError(msg)
      pushLog('error', `Réanalyse échouée: ${msg}`)
    } finally {
      setAnalyzing(false)
    }
  }, [pushLog])

  const navigate = useCallback(async (address: string, fn?: RizinFunction) => {
    setCurrentAddress(address)
    if (fn) {
      setCurrentFunction(fn)
      return
    }
    const sid = sessionIdRef.current
    if (!sid) return
    try {
      const info = await api.reFunctionInfo(sid, address)
      setCurrentFunction(info)
    } catch { /* address may not be a function entry */ }
  }, [])

  const loadSidebarData = useCallback(async () => {
    const sid = sessionIdRef.current
    if (!sid) return
    const [strs, imps, exps] = await Promise.all([
      api.reStringsAll(sid).catch(() => [] as RizinString[]),
      api.reImports(sid).catch(() => [] as RizinImport[]),
      api.reExports(sid).catch(() => [] as RizinExport[]),
    ])
    setStrings(strs)
    setImports(imps)
    setExports(exps)
  }, [])

  const renameFunction = useCallback(async (address: string, newName: string) => {
    const sid = sessionIdRef.current
    if (!sid) return
    await api.reRenameFunction(sid, address, newName)
    setFunctions(prev => prev.map(f =>
      `0x${f.offset.toString(16)}` === address ? { ...f, name: newName } : f
    ))
    setCurrentFunction(prev => prev && `0x${prev.offset.toString(16)}` === address
      ? { ...prev, name: newName } : prev)
    pushLog('ok', `Renommé → ${newName}`)
  }, [pushLog])

  return {
    sessionId,
    binaryPath,
    opening,
    openError,
    analyzing,
    analyzeError,
    analyzed,
    binaryInfo,
    loadingSteps,
    functions,
    strings,
    imports,
    exports,
    currentAddress,
    currentFunction,
    log,
    ensureSession,
    destroySession,
    openBinary,
    analyze,
    navigate,
    loadSidebarData,
    renameFunction,
  }
}

export type RizinSession = ReturnType<typeof useRizinSession>
