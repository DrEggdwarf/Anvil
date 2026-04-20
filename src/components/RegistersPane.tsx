import { useState } from 'react'
import type { RegMap } from '../hooks/useAnvilSession'

const SEG_COLORS = ['#ff9e64', '#7dcfff', '#bb9af7', '#73daca']

const REG_MAIN = ['rax', 'rbx', 'rcx', 'rdx', 'rsi', 'rdi', 'rsp', 'rbp'] as const
const REG_EXT = ['r8', 'r9', 'r10', 'r11', 'r12', 'r13', 'r14', 'r15'] as const
const FLAGS = ['ZF', 'CF', 'SF', 'OF', 'PF', 'AF', 'DF'] as const

const SUB_REGS: Record<string, { e32: string; e16: string; e8h?: string; e8l: string }> = {
  rax: { e32: 'eax', e16: 'ax', e8h: 'ah', e8l: 'al' },
  rbx: { e32: 'ebx', e16: 'bx', e8h: 'bh', e8l: 'bl' },
  rcx: { e32: 'ecx', e16: 'cx', e8h: 'ch', e8l: 'cl' },
  rdx: { e32: 'edx', e16: 'dx', e8h: 'dh', e8l: 'dl' },
  rsi: { e32: 'esi', e16: 'si', e8l: 'sil' },
  rdi: { e32: 'edi', e16: 'di', e8l: 'dil' },
  rsp: { e32: 'esp', e16: 'sp', e8l: 'spl' },
  rbp: { e32: 'ebp', e16: 'bp', e8l: 'bpl' },
}

function formatVal(val: string, mode: 'hex' | 'dec' | 'bin'): string {
  if (!val || val === '0x0') return '0x0'
  const n = BigInt(val)
  if (mode === 'dec') return n.toString(10)
  if (mode === 'bin') return '0b' + n.toString(2)
  return '0x' + n.toString(16)
}

function subVal(fullVal: string, bits: [number, number]): string {
  if (!fullVal || fullVal === '0x0') return '0'
  try {
    const n = BigInt(fullVal)
    const mask = (1n << BigInt(bits[0] - bits[1] + 1)) - 1n
    return ((n >> BigInt(bits[1])) & mask).toString(16)
  } catch { return '0' }
}

interface RegCardProps {
  name: string
  value: string
  displayMode: 'hex' | 'dec' | 'bin'
  changed: boolean
}

function RegCard({ name, value, displayMode, changed }: RegCardProps) {
  const sub = SUB_REGS[name]
  if (!sub) return null
  const has8h = !!sub.e8h

  return (
    <div className={`anvil-regcard ${changed ? 'anvil-regcard--changed' : ''}`}>
      <div className="anvil-regcard-head">
        <span className="anvil-regcard-pill">{name}</span>
        <span className="anvil-regcard-val">{formatVal(value, displayMode)}</span>
      </div>
      <div className="anvil-regcard-bar">
        <div
          className="anvil-regbar-seg"
          style={{ width: '50%', backgroundColor: SEG_COLORS[0] + '20' }}
          title={`${sub.e32} (31:0)`}
        >
          <span className="anvil-seg-pill" style={{ color: SEG_COLORS[0] }}>{sub.e32}</span>
          <span className="anvil-seg-val">{subVal(value, [31, 0])}</span>
        </div>
        {has8h ? (
          <>
            <div
              className="anvil-regbar-seg"
              style={{ width: '12.5%', backgroundColor: SEG_COLORS[2] + '25' }}
              title={`${sub.e8h} (15:8)`}
            >
              <span className="anvil-seg-pill" style={{ color: SEG_COLORS[2] }}>{sub.e8h}</span>
              <span className="anvil-seg-val">{subVal(value, [15, 8])}</span>
            </div>
            <div
              className="anvil-regbar-seg"
              style={{ width: '12.5%', backgroundColor: SEG_COLORS[3] + '25' }}
              title={`${sub.e8l} (7:0)`}
            >
              <span className="anvil-seg-pill" style={{ color: SEG_COLORS[3] }}>{sub.e8l}</span>
              <span className="anvil-seg-val">{subVal(value, [7, 0])}</span>
            </div>
          </>
        ) : (
          <>
            <div
              className="anvil-regbar-seg"
              style={{ width: '12.5%', backgroundColor: SEG_COLORS[1] + '25' }}
              title={`${sub.e16} (15:0)`}
            >
              <span className="anvil-seg-pill" style={{ color: SEG_COLORS[1] }}>{sub.e16}</span>
              <span className="anvil-seg-val">{subVal(value, [15, 0])}</span>
            </div>
            <div
              className="anvil-regbar-seg"
              style={{ width: '12.5%', backgroundColor: SEG_COLORS[3] + '25' }}
              title={`${sub.e8l} (7:0)`}
            >
              <span className="anvil-seg-pill" style={{ color: SEG_COLORS[3] }}>{sub.e8l}</span>
              <span className="anvil-seg-val">{subVal(value, [7, 0])}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

interface Props {
  registers: RegMap
  prevRegisters?: RegMap
}

export function RegistersPane({ registers, prevRegisters }: Props) {
  const [displayMode, setDisplayMode] = useState<'hex' | 'dec' | 'bin'>('hex')
  const [showModified, setShowModified] = useState(false)
  const [showUpper, setShowUpper] = useState(false)

  const prev = prevRegisters || {}

  function isChanged(name: string) {
    return prev[name] !== undefined && prev[name] !== registers[name]
  }

  const ripVal = registers['rip'] || '0x0000000000000000'

  return (
    <div className="anvil-regs-pane">
      <div className="anvil-regs-header">
        <span className="anvil-section-title">Registres</span>
        <div className="anvil-regs-filters">
          <button
            className={`anvil-regs-toggle ${showModified ? 'active' : ''}`}
            onClick={() => setShowModified(!showModified)}
          >modifies</button>
          <button
            className={`anvil-regs-toggle ${showUpper ? 'active' : ''}`}
            onClick={() => setShowUpper(!showUpper)}
          >63:32</button>
          <button
            className="anvil-regs-toggle active"
            onClick={() => setDisplayMode(m => m === 'hex' ? 'dec' : m === 'dec' ? 'bin' : 'hex')}
          >{displayMode.toUpperCase()}</button>
        </div>
      </div>

      <div className="anvil-regs-scroll">
        <div className="anvil-rip-bar">
          <span className="anvil-rip-label">RIP</span>
          <span className="anvil-rip-val">{formatVal(ripVal, displayMode)}</span>
          <span className="anvil-rip-instr">--</span>
        </div>

        <div className="anvil-regcards-list">
          {REG_MAIN.map(name => {
            const changed = isChanged(name)
            if (showModified && !changed) return null
            return (
              <RegCard
                key={name}
                name={name}
                value={registers[name] || '0x0'}
                displayMode={displayMode}
                changed={changed}
              />
            )
          })}
        </div>

        <div className="anvil-regext-grid">
          {REG_EXT.map(name => {
            const changed = isChanged(name)
            if (showModified && !changed) return null
            return (
              <div key={name} className={`anvil-regext ${changed ? 'anvil-regext--changed' : ''}`}>
                <span className="anvil-regext-name">{name}</span>
                <span className="anvil-regext-val">{formatVal(registers[name] || '0x0', displayMode)}</span>
              </div>
            )
          })}
        </div>

        <div className="anvil-flags-inline">
          {FLAGS.map(f => (
            <span key={f} className={`anvil-flag-pill ${registers['eflags'] ? '' : ''}`}>{f}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
