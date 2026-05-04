// In dev: Vite proxies /api → http://127.0.0.1:8000 (same-origin, no CORS)
// In prod/Tauri: requests go to the backend directly
const BASE = window.__TAURI__ ? 'http://127.0.0.1:8000' : ''

declare global {
  interface Window { __TAURI__?: unknown }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('Backend injoignable (lancez: cd Anvil && PYTHONPATH=. python -m uvicorn backend.app.main:app --port 8000)')
  }
  if (res.status === 204) return undefined as T
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const error = new Error(err.error || err.detail || err.message || res.statusText) as Error & { code?: string; status?: number }
    error.code = err.code
    error.status = res.status
    throw error
  }
  return res.json()
}

// ── Types ────────────────────────────────────────────────────

export interface SessionInfo {
  id: string
  bridge_type: string
  state: string
  created_at: string
  last_activity: string
}

/** Returned by POST /api/sessions only — the WS auth token is exposed once at creation
 *  (ADR-016). Subsequent GET /api/sessions/{id} calls return the SessionInfo shape. */
export interface SessionCreated extends SessionInfo {
  token: string
}

export interface CompileError {
  file: string
  line: number
  column: number
  severity: string
  message: string
}

export interface CompileResponse {
  success: boolean
  stage: string
  binary_path: string | null
  object_path: string | null
  errors: CompileError[]
  warnings: CompileError[]
  stdout: string
  stderr: string
  returncode: number
}

export interface GdbRawResponse {
  responses: Record<string, unknown>[]
}

export interface RegisterEntry {
  name: string
  number: number
  value: string
}

export interface RegistersResponse {
  registers: Record<string, unknown>[]
}

// ── Sessions ─────────────────────────────────────────────────

export function createSession(bridge_type: string) {
  return request<SessionCreated>('POST', '/api/sessions', { bridge_type })
}

export function deleteSession(id: string) {
  return request<void>('DELETE', `/api/sessions/${id}`)
}

// ── Compile ──────────────────────────────────────────────────

export interface CompileAsmOpts {
  source_code: string
  filename?: string
  assembler?: 'nasm' | 'gas' | 'fasm'
  fmt?: string
  debug?: boolean
  link?: boolean
}

export function compileAsm(sessionId: string, opts: CompileAsmOpts) {
  return request<CompileResponse>('POST', `/api/compile/${sessionId}/asm`, opts)
}

// ── GDB ──────────────────────────────────────────────────────

export function gdbLoad(sessionId: string, binary_path: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/load`, { binary_path })
}

export function gdbRun(sessionId: string, args = '') {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/run`, args ? { args } : undefined)
}

export function gdbContinue(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/continue`)
}

export function gdbStepInto(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/step/into`)
}

export function gdbStepOver(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/step/over`)
}

export function gdbStepOut(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/step/out`)
}

export function gdbEnableRecord(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/record`)
}

export function gdbStepBack(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/step/back`)
}

export function gdbInterrupt(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/interrupt`)
}

export function gdbRegisters(sessionId: string) {
  return request<RegistersResponse>('GET', `/api/gdb/${sessionId}/registers`)
}

export function gdbSetBreakpoint(sessionId: string, location: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/breakpoints`, { location })
}

export function gdbRemoveBreakpoint(sessionId: string, bpNumber: number) {
  return request<GdbRawResponse>('DELETE', `/api/gdb/${sessionId}/breakpoints/${bpNumber}`)
}

export function gdbListBreakpoints(sessionId: string) {
  return request<GdbRawResponse>('GET', `/api/gdb/${sessionId}/breakpoints`)
}

export function gdbStack(sessionId: string, maxFrames = 64) {
  return request<GdbRawResponse>('GET', `/api/gdb/${sessionId}/stack?max_frames=${maxFrames}`)
}

export function gdbMemory(sessionId: string, address: string, size = 256) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/memory`, { address, size })
}

export function gdbWriteMemory(sessionId: string, address: string, hex_data: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/memory/write`, { address, hex_data })
}

export function gdbMemoryMap(sessionId: string) {
  return request<GdbRawResponse>('GET', `/api/gdb/${sessionId}/memory-map`)
}

export function gdbDisassemble(sessionId: string) {
  return request<GdbRawResponse>('POST', `/api/gdb/${sessionId}/disassemble`)
}

export function gdbCurrentLine(sessionId: string) {
  return request<GdbRawResponse>('GET', `/api/gdb/${sessionId}/current-line`)
}

// ── RE / Rizin ────────────────────────────────────────────────

import type {
  RizinFunction, RizinOp, CfgGraph, CfgBlock, RizinString,
  RizinImport, RizinExport, RizinSymbol, RizinXref,
  RizinBinaryInfo, AnalyzeResult, DecompileResult,
} from '../types/re'

export type { RizinFunction, RizinOp, CfgGraph, CfgBlock, RizinString }
export type { RizinImport, RizinExport, RizinSymbol, RizinXref }
export type { RizinBinaryInfo, AnalyzeResult, DecompileResult }

export function reOpenBinary(sessionId: string, binaryPath: string) {
  return request<{ message: string }>('POST', `/api/re/${sessionId}/open`, { binary_path: binaryPath })
}
export function reAnalyze(sessionId: string, level = 'aaa') {
  return request<AnalyzeResult>('POST', `/api/re/${sessionId}/analyze`, { level })
}
export function reBinaryInfo(sessionId: string) {
  return request<RizinBinaryInfo>('GET', `/api/re/${sessionId}/info`)
}
export async function reFunctions(sessionId: string): Promise<RizinFunction[]> {
  const res = await request<{ functions: RizinFunction[] } | RizinFunction[]>('GET', `/api/re/${sessionId}/functions`)
  return Array.isArray(res) ? res : (res as { functions: RizinFunction[] }).functions ?? []
}
export function reFunctionInfo(sessionId: string, address: string) {
  return request<RizinFunction>('GET', `/api/re/${sessionId}/functions/${address}`)
}
export async function reDisasmFunction(sessionId: string, address: string): Promise<RizinOp[]> {
  const res = await request<{ data: RizinOp[] } | RizinOp[]>('POST', `/api/re/${sessionId}/disassemble/function/${address}`, {})
  return Array.isArray(res) ? res : (res as { data: RizinOp[] }).data ?? []
}
export async function reCfg(sessionId: string, address: string): Promise<CfgBlock[]> {
  const res = await request<{ data: CfgBlock[] } | CfgBlock[]>('GET', `/api/re/${sessionId}/cfg/${address}`)
  return Array.isArray(res) ? res : (res as { data: CfgBlock[] }).data ?? []
}
export async function reDecompile(sessionId: string, address: string): Promise<DecompileResult> {
  const res = await request<{ data: DecompileResult } | DecompileResult>('POST', `/api/re/${sessionId}/decompile`, { address })
  return 'data' in (res as object) && (res as { data?: DecompileResult }).data
    ? (res as { data: DecompileResult }).data
    : (res as DecompileResult)
}
export async function reStringsAll(sessionId: string): Promise<RizinString[]> {
  const res = await request<{ strings: RizinString[] } | RizinString[]>('GET', `/api/re/${sessionId}/strings/all`)
  return Array.isArray(res) ? res : (res as { strings: RizinString[] }).strings ?? []
}
export async function reImports(sessionId: string): Promise<RizinImport[]> {
  const res = await request<{ imports: RizinImport[] } | RizinImport[]>('GET', `/api/re/${sessionId}/imports`)
  return Array.isArray(res) ? res : (res as { imports: RizinImport[] }).imports ?? []
}
export async function reExports(sessionId: string): Promise<RizinExport[]> {
  const res = await request<{ exports: RizinExport[] } | RizinExport[]>('GET', `/api/re/${sessionId}/exports`)
  return Array.isArray(res) ? res : (res as { exports: RizinExport[] }).exports ?? []
}
export function reSymbols(sessionId: string) {
  return request<RizinSymbol[]>('GET', `/api/re/${sessionId}/symbols`)
}
export async function reXrefsTo(sessionId: string, address: string): Promise<RizinXref[]> {
  const res = await request<{ xrefs: RizinXref[] } | RizinXref[]>('GET', `/api/re/${sessionId}/xrefs/to/${address}`)
  return Array.isArray(res) ? res : (res as { xrefs: RizinXref[] }).xrefs ?? []
}
export async function reXrefsFrom(sessionId: string, address: string): Promise<RizinXref[]> {
  const res = await request<{ xrefs: RizinXref[] } | RizinXref[]>('GET', `/api/re/${sessionId}/xrefs/from/${address}`)
  return Array.isArray(res) ? res : (res as { xrefs: RizinXref[] }).xrefs ?? []
}
export async function reReadHex(sessionId: string, address: string, length: number): Promise<{ address: string; bytes: string; ascii: string } | unknown> {
  const res = await request<{ data: unknown } | unknown>('POST', `/api/re/${sessionId}/hex/read`, { address, length })
  return (res && typeof res === 'object' && 'data' in res) ? (res as { data: unknown }).data : res
}
export function reReadHexText(sessionId: string, address: string, length: number) {
  return request<{ output: string }>('POST', `/api/re/${sessionId}/hex/read/text`, { address, length })
}
export function reRenameFunction(sessionId: string, address: string, newName: string) {
  return request<{ message: string }>('POST', `/api/re/${sessionId}/functions/rename`, { address, new_name: newName })
}

// ── Binary Analysis ──────────────────────────────────────

export interface ChecksecData {
  path: string
  relro: string
  canary: boolean
  nx: boolean
  pie: boolean
  rpath: boolean
  runpath: boolean
  symbols: boolean
  fortify: boolean
}

export interface SectionInfo {
  name: string
  type: string
  address: string
  offset: string
  size: number
  flags: string
}

export interface StringEntry {
  offset: string
  string: string
}

export interface DependencyEntry {
  name: string
  path: string
  address: string
}

export function checksec(sessionId: string, filename: string) {
  return request<ChecksecData>('GET', `/api/compile/${sessionId}/checksec/${filename}`)
}

export function sections(sessionId: string, filename: string) {
  return request<{ sections: SectionInfo[] }>('GET', `/api/compile/${sessionId}/sections/${filename}`)
}

export function strings(sessionId: string, filename: string, minLength = 4) {
  return request<{ strings: StringEntry[] }>('GET', `/api/compile/${sessionId}/strings/${filename}?min_length=${minLength}`)
}

export function dependencies(sessionId: string, filename: string) {
  return request<{ dependencies: DependencyEntry[] }>('GET', `/api/compile/${sessionId}/dependencies/${filename}`)
}

// ── Pwn ──────────────────────────────────────────────────────

/** Backend wraps free-form dict payloads in {data: ...} (PwnDictResponse).
 *  Sprint 17-D: type it generically so callers can drop `as any` casts. */
export interface PwnDict<T> { data: T }
export interface PwnList<T> { items: T[] }

export interface PwnChecksec {
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

export interface PwnSymbol { name: string; address: string }
export interface PwnGotEntry { name: string; address: string }
export interface PwnPltEntry { name: string; address: string }

export function pwnUploadBinary(sessionId: string, filename: string, dataB64: string) {
  return request<{ path: string; size: number }>('POST', `/api/pwn/${sessionId}/upload`, { filename, data_b64: dataB64 })
}

export function pwnCompile(sessionId: string, path: string, language: string, vulnFlags = true) {
  return request<{ binary_path: string; size: number }>('POST', `/api/pwn/${sessionId}/compile`, { path, language, vuln_flags: vulnFlags })
}

export function pwnLoadElf(sessionId: string, path: string) {
  return request<{ path: string; arch: string; bits: number; endian: string; entry: string; type: string }>(
    'POST', `/api/pwn/${sessionId}/elf/load`, { path }
  )
}

export function pwnChecksec(sessionId: string, path: string) {
  return request<PwnDict<PwnChecksec>>('GET', `/api/pwn/${sessionId}/elf/checksec?path=${encodeURIComponent(path)}`)
}

export function pwnSymbols(sessionId: string, path: string) {
  return request<PwnDict<Record<string, string>>>('GET', `/api/pwn/${sessionId}/elf/symbols?path=${encodeURIComponent(path)}`)
}

export function pwnGot(sessionId: string, path: string) {
  return request<PwnDict<Record<string, string>>>('GET', `/api/pwn/${sessionId}/elf/got?path=${encodeURIComponent(path)}`)
}

export function pwnPlt(sessionId: string, path: string) {
  return request<PwnDict<Record<string, string>>>('GET', `/api/pwn/${sessionId}/elf/plt?path=${encodeURIComponent(path)}`)
}

export function pwnSections(sessionId: string, path: string) {
  return request<PwnDict<Record<string, unknown>>>('GET', `/api/pwn/${sessionId}/elf/sections?path=${encodeURIComponent(path)}`)
}

export function pwnFunctions(sessionId: string, path: string) {
  return request<PwnDict<Record<string, string>>>('GET', `/api/pwn/${sessionId}/elf/functions?path=${encodeURIComponent(path)}`)
}

export function pwnSearchElf(sessionId: string, path: string, needle: string, isHex = false) {
  return request<{ results: string[] }>('POST', `/api/pwn/${sessionId}/elf/search`, { path, needle, is_hex: isHex })
}

export function pwnCyclic(sessionId: string, length: number) {
  return request<{ hex: string }>('POST', `/api/pwn/${sessionId}/cyclic`, { length })
}

export function pwnCyclicFind(sessionId: string, value: string) {
  return request<{ offset: number }>('POST', `/api/pwn/${sessionId}/cyclic/find`, { value })
}

export function pwnRopCreate(sessionId: string, elfPath: string) {
  return request<{ rop_id: string }>('POST', `/api/pwn/${sessionId}/rop/create`, { elf_path: elfPath })
}

export function pwnRopGadget(sessionId: string, ropId: string, instructions: string[]) {
  return request<{ address: string }>('POST', `/api/pwn/${sessionId}/rop/gadget`, { rop_id: ropId, instructions })
}

export function pwnRopChain(sessionId: string, ropId: string) {
  return request<{ hex: string }>('GET', `/api/pwn/${sessionId}/rop/${ropId}/chain`)
}

export function pwnRopDump(sessionId: string, ropId: string) {
  return request<{ dump: string }>('GET', `/api/pwn/${sessionId}/rop/${ropId}/dump`)
}

export function pwnFmtstr(sessionId: string, offset: number, writes: Record<string, number>, numbwritten = 0, writeSize = 'byte') {
  return request<{ hex: string }>('POST', `/api/pwn/${sessionId}/fmtstr`, { offset, writes, numbwritten, write_size: writeSize })
}

export function pwnShellcraftList(sessionId: string) {
  return request<{ templates: string[] }>('GET', `/api/pwn/${sessionId}/shellcraft/list`)
}

export function pwnShellcraftAsm(sessionId: string, template: string, args: Record<string, string> = {}) {
  return request<{ hex: string }>('POST', `/api/pwn/${sessionId}/shellcraft/asm`, { template, args })
}

export function pwnAsm(sessionId: string, source: string) {
  return request<{ hex: string }>('POST', `/api/pwn/${sessionId}/asm`, { source })
}

export function pwnDisasm(sessionId: string, hex: string) {
  return request<{ assembly: string }>('POST', `/api/pwn/${sessionId}/disasm`, { hex_data: hex })
}

export function pwnContext(sessionId: string, arch?: string, bits?: number) {
  const body: Record<string, unknown> = {}
  if (arch) body.arch = arch
  if (bits) body.bits = bits
  return request<{ arch: string; os: string; bits: number; endian: string }>('POST', `/api/pwn/${sessionId}/context`, body)
}

export function pwnStringsElf(sessionId: string, path: string) {
  return request<{ strings: StringEntry[] }>('GET', `/api/compile/${sessionId}/strings/${path.split('/').pop()}`)
}

export function writeSource(sessionId: string, filename: string, content: string) {
  return request<{ filename: string; content: string }>('POST', `/api/compile/${sessionId}/files`, { filename, content })
}

export function uploadBinary(sessionId: string, filename: string, binaryData: ArrayBuffer) {
  // Write as hex to workspace, then reference by path
  const hex = Array.from(new Uint8Array(binaryData)).map(b => b.toString(16).padStart(2, '0')).join('')
  return request<{ filename: string; content: string }>('POST', `/api/compile/${sessionId}/files`, { filename, content: hex })
}

// ── Agent IA (ADR-023) ───────────────────────────────────────

export type AgentProviderName = 'anthropic' | 'openai' | 'openrouter' | 'ollama'

export interface AgentChunk {
  type: 'session' | 'delta' | 'tool_call' | 'tool_result' | 'tool_pending' | 'done' | 'error'
  data: Record<string, any>
}

export interface AgentChatBody {
  session_id?: string | null
  module: string
  chips: string[]
  message: string
  anvil_session_ids?: Record<string, string>
  allow_write_exec?: boolean | null
}

export interface AgentSessionSummary {
  id: string
  title: string
  module: string
  provider: AgentProviderName
  model: string
  created_at: string
  last_used: string
  message_count: number
}

export interface AgentToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: unknown
  error?: string | null
  duration_ms?: number | null
  destructive?: boolean
}

export interface AgentMessage {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  tool_calls?: AgentToolCall[]
  tool_call_id?: string | null
}

export interface AgentSessionFull {
  id: string
  title: string
  module: string
  provider: AgentProviderName
  model: string
  created_at: string
  last_used: string
  messages: AgentMessage[]
}

export interface AgentSettingsView {
  active_provider: AgentProviderName
  providers: Record<AgentProviderName, {
    api_key_masked: string
    has_key: boolean
    base_url: string | null
    default_model: string
  }>
  strict_mode: boolean
  allow_write_exec: boolean
  token_cap: number
  language: 'fr' | 'en'
}

/** Stream a chat turn from the in-app agent (SSE). */
export async function* agentChatStream(body: AgentChatBody, signal?: AbortSignal): AsyncGenerator<AgentChunk> {
  const res = await fetch(`${BASE}/api/agent/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    const txt = await res.text().catch(() => res.statusText)
    throw new Error(`Agent stream failed (${res.status}): ${txt.slice(0, 200)}`)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let nl: number
    while ((nl = buf.indexOf('\n\n')) !== -1) {
      const evt = buf.slice(0, nl)
      buf = buf.slice(nl + 2)
      for (const line of evt.split('\n')) {
        if (!line.startsWith('data:')) continue
        const payload = line.slice(5).trim()
        if (!payload) continue
        try {
          yield JSON.parse(payload) as AgentChunk
        } catch {
          /* ignore malformed */
        }
      }
    }
  }
}

export function agentListSessions() {
  return request<{ sessions: AgentSessionSummary[] }>('GET', '/api/agent/sessions')
}

export function agentGetSession(id: string) {
  return request<AgentSessionFull>('GET', `/api/agent/sessions/${id}`)
}

export function agentDeleteSession(id: string) {
  return request<{ deleted: boolean }>('DELETE', `/api/agent/sessions/${id}`)
}

export function agentPurgeSessions() {
  return request<{ deleted: number }>('DELETE', '/api/agent/sessions')
}

export function agentGetSettings() {
  return request<AgentSettingsView>('GET', '/api/agent/settings')
}

export function agentUpdateSettings(payload: Partial<{
  active_provider: AgentProviderName
  strict_mode: boolean
  allow_write_exec: boolean
  language: 'fr' | 'en'
  token_cap: number
  providers: Partial<Record<AgentProviderName, { api_key?: string; base_url?: string | null; default_model?: string }>>
}>) {
  return request<AgentSettingsView>('PUT', '/api/agent/settings', payload)
}

export function agentListProviders() {
  return request<{ providers: AgentProviderName[] }>('GET', '/api/agent/providers')
}

export function agentTestProvider(provider: AgentProviderName, opts: { api_key?: string; base_url?: string; model?: string } = {}) {
  return request<{ ok: boolean; status?: number; error?: string }>('POST', '/api/agent/providers/test', { provider, ...opts })
}

export function agentAuditLog(limit = 200) {
  return request<{ entries: Array<Record<string, unknown>> }>('GET', `/api/agent/audit?limit=${limit}`)
}
