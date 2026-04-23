import { useState, useRef, useCallback } from 'react'
import * as api from '../api/client'

export interface PwnTermLine {
  type: 'info' | 'error' | 'output' | 'cmd'
  text: string
}

export interface BinaryInfo {
  path: string
  arch: string
  bits: number
  endian: string
  entry: string
  type: string
}

export interface ChecksecInfo {
  relro: string
  canary: boolean
  nx: boolean
  pie: boolean
  rpath: boolean
  runpath: boolean
  fortify: boolean
  arch: string
  bits: number
}

export interface SymbolEntry { name: string; address: string }

export function usePwnSession() {
  const sessionId = useRef<string | null>(null)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  // Binary state
  const [binaryPath, setBinaryPath] = useState<string | null>(null)
  const [binaryInfo, setBinaryInfo] = useState<BinaryInfo | null>(null)
  const [checksecData, setChecksecData] = useState<ChecksecInfo | null>(null)
  const [symbols, setSymbols] = useState<SymbolEntry[]>([])
  const [gotEntries, setGotEntries] = useState<SymbolEntry[]>([])
  const [pltEntries, setPltEntries] = useState<SymbolEntry[]>([])
  const [elfStrings, _setElfStrings] = useState<{ offset: string; string: string }[]>([])

  // Source code (when a source file is loaded)
  const [sourceCode, setSourceCode] = useState<string | null>(null)
  const [sourceLang, setSourceLang] = useState<string | null>(null)

  // Editor + terminal
  const [exploitCode, setExploitCode] = useState(EXPLOIT_TEMPLATE)
  const [lines, setLines] = useState<PwnTermLine[]>([])
  const [loading, setLoading] = useState(false)

  const log = useCallback((type: PwnTermLine['type'], text: string) => {
    setLines(prev => [...prev, { type, text }])
  }, [])

  const clearTerminal = useCallback(() => setLines([]), [])

  // ── Session management ──────────────────────────────────

  async function ensureSession(): Promise<string> {
    if (sessionId.current) return sessionId.current
    const s = await api.createSession('pwn')
    sessionId.current = s.id
    setCurrentSessionId(s.id)
    return s.id
  }

  async function destroySession() {
    if (sessionId.current) {
      await api.deleteSession(sessionId.current).catch(() => {})
      sessionId.current = null
      setCurrentSessionId(null)
    }
  }

  // ── Source detection ──────────────────────────────────────

  const SOURCE_EXTENSIONS: Record<string, string> = {
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp',
    '.asm': 'asm', '.s': 's',
    '.rs': 'rs',
    '.go': 'go',
  }

  function detectLanguage(filename: string): string | null {
    const dot = filename.lastIndexOf('.')
    if (dot === -1) return null
    const ext = filename.slice(dot).toLowerCase()
    return SOURCE_EXTENSIONS[ext] ?? null
  }

  function isElf(bytes: Uint8Array): boolean {
    return bytes.length >= 4 && bytes[0] === 0x7f && bytes[1] === 0x45 && bytes[2] === 0x4c && bytes[3] === 0x46
  }

  // ── Binary loading ──────────────────────────────────────

  async function loadBinary(file: File) {
    setLoading(true)
    log('cmd', `Loading ${file.name}...`)

    try {
      const sid = await ensureSession()

      // Read file as ArrayBuffer and encode to base64
      const buffer = await file.arrayBuffer()
      const bytes = new Uint8Array(buffer)

      let binary = ''
      for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i])
      const dataB64 = btoa(binary)

      // Upload file to workspace
      const { path } = await api.pwnUploadBinary(sid, file.name, dataB64)
      log('info', `Uploaded ${file.name} (${bytes.length} bytes)`)

      let elfPath = path

      // If not ELF → try to compile it
      if (!isElf(bytes)) {
        const lang = detectLanguage(file.name)
        if (!lang) {
          log('error', `"${file.name}" n'est pas un ELF et l'extension n'est pas reconnue (.c, .cpp, .rs, .go, .asm, .s)`)
          setLoading(false)
          return
        }

        // Store source code for the SourceViewer
        const decoder = new TextDecoder('utf-8', { fatal: false })
        setSourceCode(decoder.decode(bytes))
        setSourceLang(lang)

        log('info', `Source ${lang.toUpperCase()} détecté — compilation en cours...`)
        try {
          const compiled = await api.pwnCompile(sid, path, lang)
          elfPath = compiled.binary_path
          log('info', `Compilé → ${elfPath.split('/').pop()} (${compiled.size} bytes)`)
        } catch (e) {
          log('error', `Compilation échouée: ${(e as Error).message}`)
          setLoading(false)
          return
        }
      }

      // Load ELF info
      try {
        const elf = await api.pwnLoadElf(sid, elfPath)
        setBinaryInfo(elf)
        setBinaryPath(elfPath)
        log('info', `ELF loaded: ${elf.arch} ${elf.bits}-bit ${elf.type} (entry: ${elf.entry})`)

        // Fetch all analysis data in parallel
        await Promise.allSettled([
          fetchChecksec(sid, elfPath),
          fetchSymbols(sid, elfPath),
          fetchGot(sid, elfPath),
          fetchPlt(sid, elfPath),
        ])
      } catch (e) {
        log('error', `ELF parse: ${(e as Error).message}`)
      }
    } catch (e) {
      log('error', `Load failed: ${(e as Error).message}`)
    } finally {
      setLoading(false)
    }
  }

  async function fetchChecksec(sid: string, path: string) {
    try {
      const resp = await api.pwnChecksec(sid, path)
      // API wraps in {data: {...}} via PwnDictResponse
      const data = (resp as any).data ?? resp
      setChecksecData(data)
    } catch (e) {
      log('error', `Checksec: ${(e as Error).message}`)
    }
  }

  async function fetchSymbols(sid: string, path: string) {
    try {
      const resp = await api.pwnSymbols(sid, path)
      const raw = (resp as any).data ?? resp.symbols ?? {}
      const entries = Object.entries(raw).map(([name, address]) => ({ name, address: String(address) }))
      setSymbols(entries)
    } catch { /* optional */ }
  }

  async function fetchGot(sid: string, path: string) {
    try {
      const resp = await api.pwnGot(sid, path)
      const raw = (resp as any).data ?? resp.got ?? {}
      const entries = Object.entries(raw).map(([name, address]) => ({ name, address: String(address) }))
      setGotEntries(entries)
    } catch { /* optional */ }
  }

  async function fetchPlt(sid: string, path: string) {
    try {
      const resp = await api.pwnPlt(sid, path)
      const raw = (resp as any).data ?? resp.plt ?? {}
      const entries = Object.entries(raw).map(([name, address]) => ({ name, address: String(address) }))
      setPltEntries(entries)
    } catch { /* optional */ }
  }

  // ── Pwn tools ───────────────────────────────────────────

  async function cyclicGenerate(length: number): Promise<string | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnCyclic(sid, length)
      log('output', `cyclic(${length}) = ${res.hex.slice(0, 80)}${res.hex.length > 80 ? '...' : ''}`)
      return res.hex
    } catch (e) {
      log('error', `Cyclic: ${(e as Error).message}`)
      return null
    }
  }

  async function cyclicFind(value: string): Promise<number | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnCyclicFind(sid, value)
      log('output', `cyclic_find("${value}") = ${res.offset}`)
      return res.offset
    } catch (e) {
      log('error', `Cyclic find: ${(e as Error).message}`)
      return null
    }
  }

  async function shellcraftGenerate(template: string): Promise<string | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnShellcraftAsm(sid, template)
      log('output', `shellcraft.${template}() = ${res.hex.slice(0, 80)}${res.hex.length > 80 ? '...' : ''}`)
      return res.hex
    } catch (e) {
      log('error', `Shellcraft: ${(e as Error).message}`)
      return null
    }
  }

  async function ropFindGadgets(instructions: string[]): Promise<string | null> {
    if (!binaryPath) { log('error', 'No binary loaded'); return null }
    try {
      const sid = await ensureSession()
      const { rop_id } = await api.pwnRopCreate(sid, binaryPath)
      const res = await api.pwnRopGadget(sid, rop_id, instructions)
      log('output', `gadget [${instructions.join('; ')}] @ ${res.address}`)
      return res.address
    } catch (e) {
      log('error', `ROP: ${(e as Error).message}`)
      return null
    }
  }

  async function fmtstrPayload(offset: number, writes: Record<string, number>): Promise<string | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnFmtstr(sid, offset, writes)
      log('output', `fmtstr payload (${Object.keys(writes).length} writes) = ${res.hex.slice(0, 60)}...`)
      return res.hex
    } catch (e) {
      log('error', `Fmtstr: ${(e as Error).message}`)
      return null
    }
  }

  async function assembleCode(source: string): Promise<string | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnAsm(sid, source)
      log('output', `asm = ${res.hex}`)
      return res.hex
    } catch (e) {
      log('error', `Asm: ${(e as Error).message}`)
      return null
    }
  }

  async function disassembleHex(hex: string): Promise<string | null> {
    try {
      const sid = await ensureSession()
      const res = await api.pwnDisasm(sid, hex)
      log('output', res.assembly)
      return res.assembly
    } catch (e) {
      log('error', `Disasm: ${(e as Error).message}`)
      return null
    }
  }

  return {
    sessionId: currentSessionId,
    binaryPath,
    binaryInfo,
    checksecData,
    symbols,
    gotEntries,
    pltEntries,
    elfStrings,
    sourceCode,
    sourceLang,
    exploitCode,
    setExploitCode,
    lines,
    loading,
    log,
    clearTerminal,
    loadBinary,
    destroySession,
    cyclicGenerate,
    cyclicFind,
    shellcraftGenerate,
    ropFindGadgets,
    fmtstrPayload,
    assembleCode,
    disassembleHex,
  }
}

const EXPLOIT_TEMPLATE = `#!/usr/bin/env python3
from pwn import *

# ── Configuration ──────────────────────────────────────
context.arch = 'amd64'
context.os = 'linux'
context.log_level = 'info'

binary = './vuln'
elf = ELF(binary)

# ── Exploit ────────────────────────────────────────────
def exploit():
    # p = process(binary)
    # p = remote('host', port)
    p = gdb.debug(binary, '''
        break main
        continue
    ''')

    # 1. Find offset
    # payload = cyclic(200)
    # p.sendline(payload)

    # 2. Build payload
    offset = 72  # cyclic_find(value)
    payload = b'A' * offset
    payload += p64(elf.symbols['win'])  # or ROP chain

    p.sendline(payload)
    p.interactive()

if __name__ == '__main__':
    exploit()
`
