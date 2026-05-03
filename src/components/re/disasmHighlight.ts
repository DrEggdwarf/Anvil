/** Syntax highlighting tokens for x86/x64 disassembly. */

export interface DisasmToken {
  text: string
  kind: 'mnemonic' | 'register' | 'immediate' | 'memory' | 'label' | 'comment' | 'plain'
}

// x86 register names (partial — covers common 64/32/16/8-bit)
const REGISTERS = new Set([
  'rax','rbx','rcx','rdx','rsi','rdi','rbp','rsp',
  'r8','r9','r10','r11','r12','r13','r14','r15',
  'eax','ebx','ecx','edx','esi','edi','ebp','esp',
  'r8d','r9d','r10d','r11d','r12d','r13d','r14d','r15d',
  'ax','bx','cx','dx','si','di','bp','sp',
  'al','bl','cl','dl','sil','dil','bpl','spl',
  'ah','bh','ch','dh',
  'xmm0','xmm1','xmm2','xmm3','xmm4','xmm5','xmm6','xmm7',
  'ymm0','ymm1','ymm2','ymm3','rip','eflags','cs','ds','es','fs','gs','ss',
])

// Mnemonic color categories
const JUMPS = /^j[a-z]{1,4}$/   // jmp, je, jne, jl, jg, jle, jge, jz, jnz, ja, jb, ...
const CALLS = /^call$/
const RETS  = /^(ret|retq|leave|hlt|nop|ud2|int)$/
const ARITH = /^(add|sub|mul|imul|div|idiv|xor|and|or|not|neg|shl|shr|sar|rol|ror|inc|dec|adc|sbb)$/
const CMPS  = /^(cmp|test|cmpq|testq)$/

type MnemonicClass = 'jump' | 'call' | 'ret' | 'arith' | 'cmp' | 'default'

function classifyMnemonic(m: string): MnemonicClass {
  const lm = m.toLowerCase()
  if (JUMPS.test(lm)) return 'jump'
  if (CALLS.test(lm)) return 'call'
  if (RETS.test(lm)) return 'ret'
  if (ARITH.test(lm)) return 'arith'
  if (CMPS.test(lm)) return 'cmp'
  return 'default'
}

/** CSS color for a mnemonic class (uses CSS vars where possible). */
export function mnemonicColor(cls: MnemonicClass): string {
  switch (cls) {
    case 'jump':  return '#f0a020'  // amber
    case 'call':  return '#4fc1ff'  // bright blue
    case 'ret':   return '#f04747'  // red
    case 'arith': return '#c586c0'  // purple
    case 'cmp':   return '#b5cea8'  // muted green
    default:      return '#d4d4d4'  // near-white
  }
}


/**
 * Parse a `disasm` string into colored tokens suitable for SVG <tspan> or React spans.
 * Returns [{text, kind}] array.
 */
export function tokenizeDisasm(disasm: string): DisasmToken[] {
  if (!disasm) return []

  // Split mnemonic from operands
  const spaceIdx = disasm.search(/\s/)
  if (spaceIdx === -1) {
    return [{ text: disasm, kind: 'mnemonic' }]
  }

  const mnem = disasm.slice(0, spaceIdx)
  const rest = disasm.slice(spaceIdx)

  const tokens: DisasmToken[] = [
    { text: mnem, kind: 'mnemonic' },
  ]

  // Parse operands with simple tokenization
  // We do a character-by-character scan to preserve brackets
  let i = 0
  let buf = ''
  const flush = (kind: DisasmToken['kind'] = 'plain') => {
    if (buf) { tokens.push({ text: buf, kind }); buf = '' }
  }

  while (i < rest.length) {
    const ch = rest[i]
    if (ch === '[') {
      flush()
      // consume until ]
      let mem = ch; i++
      while (i < rest.length && rest[i] !== ']') { mem += rest[i]; i++ }
      if (i < rest.length) { mem += rest[i]; i++ }
      tokens.push({ text: mem, kind: 'memory' })
      continue
    }
    if (ch === ';' || (ch === '#' && i > 0)) {
      flush()
      tokens.push({ text: rest.slice(i), kind: 'comment' })
      break
    }
    // Check if word is a register
    const wordMatch = rest.slice(i).match(/^[a-z][a-z0-9]*/i)
    if (wordMatch) {
      const word = wordMatch[0]
      if (REGISTERS.has(word.toLowerCase())) {
        flush()
        tokens.push({ text: word, kind: 'register' })
        i += word.length
        continue
      }
    }
    // Check if number/hex
    const hexMatch = rest.slice(i).match(/^0x[0-9a-f]+/i) ?? rest.slice(i).match(/^[0-9]+/)
    if (hexMatch) {
      flush()
      tokens.push({ text: hexMatch[0], kind: 'immediate' })
      i += hexMatch[0].length
      continue
    }
    buf += ch
    i++
  }
  flush()
  return tokens
}

/** Assign a CSS color string to a token kind. */
export function tokenColor(kind: DisasmToken['kind'], mnem?: string): string {
  switch (kind) {
    case 'mnemonic':  return mnemonicColor(classifyMnemonic(mnem ?? ''))
    case 'register':  return '#9cdcfe'
    case 'immediate': return '#b5cea8'
    case 'memory':    return '#dcdcaa'
    case 'label':     return '#dcdcaa'
    case 'comment':   return '#6a9955'
    default:          return '#d4d4d4'
  }
}
