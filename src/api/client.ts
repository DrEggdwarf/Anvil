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
    throw new Error(err.detail || err.message || res.statusText)
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
  return request<SessionInfo>('POST', '/api/sessions', { bridge_type })
}

export function deleteSession(id: string) {
  return request<void>('DELETE', `/api/sessions/${id}`)
}

// ── Compile ──────────────────────────────────────────────────

export interface CompileAsmOpts {
  source_code: string
  filename?: string
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
