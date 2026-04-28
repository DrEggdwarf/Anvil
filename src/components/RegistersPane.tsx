import { useState, memo } from 'react'
import type { RegMap } from '../hooks/useAnvilSession'

/* ── Exact copy of ASMBLE color + data logic ── */

const SEG_COLORS = ['#ff9e64', '#7dcfff', '#bb9af7', '#73daca']

const REG_MAIN = ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rsp', 'rbp'] as const
const REG_EXT = ['r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15'] as const
const FLAGS_BITS: Record<string, number> = { CF: 0, PF: 2, AF: 4, ZF: 6, SF: 7, OF: 11, DF: 10 }
const FLAGS_ORDER = ['ZF', 'CF', 'SF', 'OF', 'PF', 'AF', 'DF'] as const

/* ── getSubRegs — straight from ASMBLE/src/data/registers.ts ── */

interface SubReg { name: string; bits: string; val: number }

const E32: Record<string, string> = { rax: 'eax', rbx: 'ebx', rcx: 'ecx', rdx: 'edx', rsi: 'esi', rdi: 'edi', rsp: 'esp', rbp: 'ebp' }
const E16: Record<string, string> = { rax: 'ax', rbx: 'bx', rcx: 'cx', rdx: 'dx', rsi: 'si', rdi: 'di', rsp: 'sp', rbp: 'bp' }
const E8L: Record<string, string> = { rax: 'al', rbx: 'bl', rcx: 'cl', rdx: 'dl', rsi: 'sil', rdi: 'dil', rsp: 'spl', rbp: 'bpl' }
const E8H: Record<string, string> = { rax: 'ah', rbx: 'bh', rcx: 'ch', rdx: 'dh' }

function getSubRegs(name: string, val64: number): SubReg[] {
  const v = BigInt.asUintN(64, BigInt(val64))
  const lo32 = Number(v & 0xffffffffn)
  const lo16 = Number(v & 0xffffn)
  const lo8  = Number(v & 0xffn)
  const hi8  = Number((v >> 8n) & 0xffn)
  if (/^r\d+$/.test(name)) return [
    { name: name + 'd', bits: '31:0', val: lo32 },
    { name: name + 'w', bits: '15:0', val: lo16 },
    { name: name + 'b', bits: '7:0',  val: lo8 },
  ]
  const subs: SubReg[] = [
    { name: E32[name], bits: '31:0', val: lo32 },
    { name: E16[name], bits: '15:0', val: lo16 },
  ]
  if (E8H[name]) subs.push({ name: E8H[name], bits: '15:8', val: hi8 })
  subs.push({ name: E8L[name], bits: '7:0', val: lo8 })
  return subs
}

/* ── Helpers ── */

function toNum(hexStr: string): number {
  if (!hexStr || hexStr === '0x0') return 0
  try { return Number(BigInt(hexStr)) } catch { return 0 }
}

function fmtMain(v: number, mode: 'hex' | 'dec' | 'bin'): string {
  if (mode === 'bin') return '0b' + BigInt.asUintN(64, BigInt(v)).toString(2)
  if (mode === 'hex') return '0x' + (v === 0 ? '0' : BigInt.asUintN(64, BigInt(v)).toString(16))
  return String(v)
}

function fmtTooltip(v: number): string {
  const b = BigInt.asUintN(64, BigInt(v))
  return `hex: 0x${b.toString(16)}\ndec: ${v}\nbin: 0b${b.toString(2)}`
}

function fmtSeg(v: number, mode: 'hex' | 'dec' | 'bin'): string {
  if (mode === 'bin') return v.toString(2)
  return mode === 'hex' ? (v === 0 ? '0' : '0x' + v.toString(16)) : String(v)
}

function parseFlags(eflagsVal: string): Set<string> {
  const active = new Set<string>()
  if (!eflagsVal) return active
  try {
    const n = BigInt(eflagsVal)
    for (const [flag, bit] of Object.entries(FLAGS_BITS)) {
      if ((n >> BigInt(bit)) & 1n) active.add(flag)
    }
  } catch { /* ignore */ }
  return active
}

/* ── RegCard — faithful copy of ASMBLE RegCard ── */

interface RegCardProps {
  name: string
  val: number
  prevVal: number | null
  changed: boolean
  showUpper: boolean
  displayMode: 'hex' | 'dec' | 'bin'
}

const RegCard = memo(function RegCard({ name, val, prevVal, changed, showUpper, displayMode }: RegCardProps) {
  const subs = getSubRegs(name, val)
  const hi32 = Number(BigInt.asUintN(64, BigInt(val)) >> 32n)

  type Seg = { name: string; val: number; pct: number; ci: number }
  const segs: Seg[] = []
  const scale = showUpper ? 1 : 2
  if (showUpper) segs.push({ name: '63:32', val: hi32, pct: 50, ci: -1 })

  if (subs.length >= 2) {
    const v31_16 = (subs[0].val >>> 16) & 0xFFFF
    segs.push({ name: subs[0].name, val: v31_16, pct: 25 * scale, ci: 0 })
  }
  if (subs.length === 4) {
    segs.push({ name: subs[2].name, val: subs[2].val, pct: 12.5 * scale, ci: 2 })
    segs.push({ name: subs[3].name, val: subs[3].val, pct: 12.5 * scale, ci: 3 })
  } else if (subs.length === 3) {
    const v15_8 = (subs[1].val >>> 8) & 0xFF
    segs.push({ name: subs[1].name, val: v15_8, pct: 12.5 * scale, ci: 1 })
    segs.push({ name: subs[2].name, val: subs[2].val, pct: 12.5 * scale, ci: 3 })
  }

  return (
    <div className={`anvil-regcard ${changed ? 'changed' : ''}`}>
      <div className="anvil-regcard-head">
        <span className="anvil-regcard-pill">{name}</span>
        <span className="anvil-regcard-val" title={fmtTooltip(val)}>{fmtMain(val, displayMode)}</span>
        {changed && prevVal !== null && (
          <span className="anvil-regcard-delta">
            <span className="anvil-delta-old">{fmtMain(prevVal, displayMode)}</span>
            <span className="anvil-delta-arrow">&rarr;</span>
            <span className="anvil-delta-new">{fmtMain(val, displayMode)}</span>
            <span className="anvil-delta-diff">{(() => {
              const d = BigInt(val) - BigInt(prevVal)
              return d >= 0n ? `+${d}` : String(d)
            })()}</span>
          </span>
        )}
      </div>
      <div className="anvil-regcard-bar">
        {segs.map((seg, i) => (
          <div
            key={i}
            className={`anvil-regbar-seg ${seg.val !== 0 ? 'active' : ''} ${seg.ci === -1 ? 'upper' : ''}`}
            style={seg.ci >= 0
              ? { width: seg.pct + '%', backgroundColor: SEG_COLORS[seg.ci] + (seg.val !== 0 ? '' : '20') }
              : { width: seg.pct + '%' }
            }
            title={`${seg.name} = ${seg.val} (0x${seg.val.toString(16)})`}
          >
            <span className="anvil-seg-pill">{seg.name}</span>
            <span className="anvil-seg-val">{fmtSeg(seg.val, displayMode)}</span>
          </div>
        ))}
      </div>
    </div>
  )
})

/* ── RegExtRow — faithful copy of ASMBLE RegExtRow ── */

const RegExtRow = memo(function RegExtRow({ name, val, prevVal, changed, displayMode }: {
  name: string; val: number; prevVal: number | null; changed: boolean; displayMode: 'hex' | 'dec' | 'bin'
}) {
  return (
    <div className={`anvil-regext ${changed ? 'changed' : ''}`}>
      <span className="anvil-regext-name">{name}</span>
      <span className="anvil-regext-val" title={fmtTooltip(val)}>{fmtMain(val, displayMode)}</span>
      {changed && prevVal !== null && (
        <span className="anvil-regext-delta">{(() => {
          const d = BigInt(val) - BigInt(prevVal)
          return d >= 0n ? `+${d}` : String(d)
        })()}</span>
      )}
    </div>
  )
})

/* ── RegistersPane ── */

interface Props {
  registers: RegMap
  prevRegisters?: RegMap
}

export function RegistersPane({ registers, prevRegisters }: Props) {
  const [displayMode, setDisplayMode] = useState<'hex' | 'dec' | 'bin'>('hex')
  const [showModified, setShowModified] = useState(false)
  const [showUpper, setShowUpper] = useState(false)

  const prev = prevRegisters || {}
  const activeFlags = parseFlags(registers['eflags'])
  const prevFlags = parseFlags(prev['eflags'])

  function isChanged(name: string) {
    return prev[name] !== undefined && prev[name] !== registers[name]
  }

  const ripVal = toNum(registers['rip'])
  const ripChanged = prev['rip'] !== undefined && prev['rip'] !== registers['rip']

  const cycleMode = () => setDisplayMode(m => m === 'hex' ? 'dec' : m === 'dec' ? 'bin' : 'hex')

  return (
    <div className="anvil-regs-pane">
      <div className="anvil-regs-header">
        <span className="anvil-section-title">Registres</span>
        <div className="anvil-regs-filters">
          <button
            className={`anvil-regs-toggle ${showModified ? 'on' : ''}`}
            onClick={() => setShowModified(!showModified)}
            title="N'afficher que les registres modifies"
          >Δ</button>
          <button
            className={`anvil-regs-toggle ${showUpper ? 'on' : ''}`}
            onClick={() => setShowUpper(!showUpper)}
            title="Afficher les bits 63:32 (partie haute)"
          >63:32</button>
          <button
            className="anvil-regs-toggle on"
            onClick={cycleMode}
            title="Basculer hex / dec / bin"
          >{displayMode.toUpperCase()}</button>
        </div>
      </div>

      <div className="anvil-regs-scroll">
        {/* RIP bar */}
        <div className={`anvil-rip-bar ${ripChanged ? 'changed' : ''}`}>
          <span className="anvil-rip-label">RIP</span>
          <span className="anvil-rip-val">{fmtMain(ripVal, displayMode)}</span>
        </div>

        {/* Main registers */}
        <div className="anvil-regcards-list">
          {REG_MAIN.map(name => {
            const changed = isChanged(name)
            if (showModified && !changed) return null
            return (
              <RegCard
                key={name}
                name={name}
                val={toNum(registers[name])}
                prevVal={prev[name] !== undefined ? toNum(prev[name]) : null}
                displayMode={displayMode}
                changed={changed}
                showUpper={showUpper}
              />
            )
          })}
        </div>

        {/* Extended registers r8-r15 */}
        <div className="anvil-regext-grid">
          {REG_EXT.map(name => {
            const changed = isChanged(name)
            if (showModified && !changed) return null
            return (
              <RegExtRow
                key={name}
                name={name}
                val={toNum(registers[name])}
                prevVal={prev[name] !== undefined ? toNum(prev[name]) : null}
                displayMode={displayMode}
                changed={changed}
              />
            )
          })}
        </div>

        {/* Flags — pills with pulse animation */}
        <div className="anvil-flags-inline">
          {FLAGS_ORDER.map(f => {
            const isActive = activeFlags.has(f)
            const wasActive = prevFlags.has(f)
            const flagChanged = isActive !== wasActive
            return (
              <span
                key={f}
                className={`anvil-flag-pill${isActive ? ' active' : ''}${flagChanged ? ' pulse' : ''}`}
                title={`${f}: ${isActive ? '1' : '0'}`}
              >
                {f}
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}
