// TypeScript interfaces for Rizin / RE mode API responses

export interface RizinFunction {
  offset: number
  name: string
  size: number
  type?: string
  nbbs?: number
  edges?: number
  calls?: number
  cc?: number
  nbinstr?: number
  nlocals?: number
  nargs?: number
}

export interface RizinOp {
  offset: number
  type: string
  disasm: string
  bytes?: string
  size?: number
  jump?: number
  fail?: number
  comment?: string
  refs?: unknown[]
  xrefs?: unknown[]
}

// CFG block from agj
export interface CfgBlock {
  offset: number
  size: number
  jump?: number    // unconditional or true branch target
  fail?: number    // false branch (only for conditional jcc)
  ninstr?: number
  ops: RizinOp[]
}

// agj returns [{name, offset, blocks: [...]}]
export interface CfgGraph {
  name: string
  offset: number
  blocks: CfgBlock[]
}

export interface RizinString {
  offset: number
  vaddr: number
  string: string
  section?: string
  type?: string
  size?: number
  paddr?: number
}

export interface RizinImport {
  ordinal: number
  bind: string
  type: string
  name: string
  plt?: number
  libname?: string
}

export interface RizinExport {
  offset: number
  vaddr: number
  name: string
  flagname?: string
  realname?: string
  size?: number
  type?: string
}

export interface RizinSymbol {
  offset: number
  name: string
  flagname?: string
  realname?: string
  size?: number
  type?: string
  bind?: string
}

export interface RizinXref {
  from: number
  to: number
  type: string
  name?: string
}

export interface RizinBinaryInfo {
  file?: string
  format?: string
  arch?: string
  bits?: number
  endian?: string
  os?: string
  class?: string
  lang?: string
  canary?: boolean
  nx?: boolean
  pic?: boolean
  relocs?: boolean
  relro?: string
  stripped?: boolean
  static?: boolean
  size?: number
  aslr?: boolean
  type?: string
}

export interface DecompileResult {
  address: string
  language: string
  code: string
  source: string
  summary?: string
}

export interface AnalyzeResult {
  status: string
  level: string
  functions_found: number
  summary: string
  raw?: string
}
