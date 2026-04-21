import { memo, useState } from 'react'
import type { StackData, RegMap } from '../../hooks/useAnvilSession'

type DisplayMode = 'hex' | 'dec' | 'bin'

interface Props {
  stackData: StackData | null
  registers: RegMap
}

function toNum(hexStr: string): number {
  if (!hexStr || hexStr === '0x0') return 0
  try { return Number(BigInt(hexStr)) } catch { return 0 }
}

/** Compute little-endian qword from 8 bytes */
function leQword(cells: (number | null)[], mode: DisplayMode): string {
  let allNull = true
  const bytes: number[] = []
  for (let i = 7; i >= 0; i--) {
    const b = cells[i]
    if (b !== null) allNull = false
    bytes.push(b ?? 0)
  }
  if (allNull) return '0x0'
  const hex = bytes.map(b => b.toString(16).padStart(2, '0')).join('')
  const n = BigInt('0x' + hex)
  if (mode === 'dec') return n.toString(10)
  if (mode === 'bin') return '0b' + n.toString(2)
  const stripped = hex.replace(/^0+/, '') || '0'
  return '0x' + stripped
}

function fmtByte(b: number, mode: DisplayMode): string {
  if (mode === 'dec') return b.toString(10).padStart(3, ' ')
  if (mode === 'bin') return b.toString(2).padStart(8, '0')
  return b.toString(16).padStart(2, '0')
}

/** Color palette for qword groups */
const QWORD_COLORS = [
  '#73daca', // teal
  '#7dcfff', // blue
  '#bb9af7', // purple
  '#ff9e64', // orange
  '#f7768e', // red
  '#9ece6a', // green
  '#e0af68', // amber
  '#7aa2f7', // indigo
]

export const StackPanel = memo(function StackPanel({ stackData, registers }: Props) {
  const [displayMode, setDisplayMode] = useState<DisplayMode>('hex')
  const [expandedRow, setExpandedRow] = useState<number | null>(null)
  const rsp = toNum(registers['rsp'])
  const rbp = toNum(registers['rbp'])

  const cycleMode = () => setDisplayMode(m => m === 'hex' ? 'dec' : m === 'dec' ? 'bin' : 'hex')

  if (!stackData || stackData.bytes.length === 0) {
    return (
      <div className="anvil-panel-section-body">
        <div className="anvil-empty">
          <span>Stack vide</span>
          <span className="anvil-empty-hint">Les donnees de la stack apparaitront pendant le debug</span>
        </div>
      </div>
    )
  }

  const { baseAddr, bytes } = stackData
  const alignedBase = baseAddr - (baseAddr % 8)
  const preOffset = baseAddr - alignedBase
  const padded: (number | null)[] = []
  for (let i = 0; i < preOffset; i++) padded.push(null)
  for (const b of bytes) padded.push(b)
  while (padded.length % 8 !== 0) padded.push(null)

  const rows: { addr: number; offset: number; cells: (number | null)[] }[] = []
  for (let i = 0; i < padded.length; i += 8) {
    const addr = alignedBase + i
    rows.push({ addr, offset: addr - rsp, cells: padded.slice(i, i + 8) })
  }

  // Classify each row into a zone
  const hasFrame = rbp > rsp && rbp > 0
  type Zone = 'locals' | 'frame' | 'caller'
  const classified = rows.map((row, idx) => {
    let zone: Zone = 'caller'
    if (hasFrame) {
      if (row.addr >= rsp && row.addr < rbp) zone = 'locals'
      else if (row.addr >= rbp && row.addr < rbp + 16) zone = 'frame'
    }
    return { ...row, zone, idx }
  })

  // Group consecutive rows by zone
  const groups: { zone: Zone; rows: typeof classified }[] = []
  for (const row of classified) {
    if (groups.length === 0 || groups[groups.length - 1].zone !== row.zone) {
      groups.push({ zone: row.zone, rows: [row] })
    } else {
      groups[groups.length - 1].rows.push(row)
    }
  }

  const ZONE_LABELS: Record<Zone, string> = {
    locals: 'Locals',
    frame: 'Stack frame',
    caller: hasFrame ? 'Caller' : '',
  }

  return (
    <div className="anvil-panel-section-body">
      <div className="anvil-stack">
        <div className="anvil-stack-head">
          <span className="anvil-stack-label-high">Adresses hautes &uarr;</span>
          <button className="anvil-regs-toggle on" onClick={cycleMode} title="Basculer hex / dec / bin">
            {displayMode.toUpperCase()}
          </button>
        </div>

        <div className="anvil-stack-rows">
          {groups.map((group, gi) => {
            const zoneLabel = ZONE_LABELS[group.zone]
            return (
              <div key={gi} className={`anvil-stack-zone anvil-stack-zone--${group.zone}`}>
                {zoneLabel && <div className="anvil-stack-zone-label">{zoneLabel}</div>}
                {group.rows.map((row) => {
                  const ri = row.idx
                  const isRspRow = row.offset === 0
                  const isRbpRow = rbp >= row.addr && rbp < row.addr + 8
                  const qIdx = ri % QWORD_COLORS.length
                  const color = QWORD_COLORS[qIdx]
                  const qword = leQword(row.cells, displayMode)
                  const hasNonZero = row.cells.some(b => b !== null && b !== 0)
                  const isExpanded = expandedRow === ri

                  const offsetLabel = row.offset === 0
                    ? 'RSP'
                    : row.offset > 0
                      ? `+${row.offset.toString(16).toUpperCase()}`
                      : `-${(-row.offset).toString(16).toUpperCase()}`

                  // Semantic annotation for frame rows
                  let annotation = ''
                  if (hasFrame) {
                    if (isRbpRow) annotation = 'saved rbp'
                    else if (rbp + 8 >= row.addr && rbp + 8 < row.addr + 8) annotation = 'ret addr'
                  }

                  const barParts = row.cells.map(b => b !== null && b !== 0)

                  return (
                    <div
                      key={ri}
                      className={`anvil-stack-row${isRspRow ? ' rsp-row' : ''}${isRbpRow ? ' rbp-row' : ''}${isExpanded ? ' expanded' : ''}`}
                      onClick={() => setExpandedRow(isExpanded ? null : ri)}
                    >
                      <div className="anvil-stack-row-compact">
                        <span className={`anvil-stack-offset${isRspRow ? ' rsp' : ''}`}>{offsetLabel}</span>
                        <span className="anvil-stack-bar">
                          {barParts.map((active, bi) => (
                            <span
                              key={bi}
                              className={`anvil-stack-bar-seg${active ? ' on' : ''}`}
                              style={active ? { backgroundColor: color } : undefined}
                            />
                          ))}
                        </span>
                        <span className={`anvil-stack-qval${hasNonZero ? ' has-val' : ''}`} style={hasNonZero ? { color } : undefined}>
                          {qword}
                        </span>
                        {annotation && <span className={`anvil-stack-anno${annotation === 'ret addr' ? ' ret' : annotation === 'saved rbp' ? ' frame' : ''}`}>{annotation}</span>}
                        {isRbpRow && !isRspRow && <span className="anvil-stack-tag rbp-tag">RBP</span>}
                      </div>

                      {isExpanded && (
                        <div className="anvil-stack-detail">
                          {row.cells.map((byte, ci) => {
                            const isActive = byte !== null && byte !== 0
                            return (
                              <span
                                key={ci}
                                className={`anvil-stack-byte${isActive ? ' active' : ''}${byte === null ? ' null' : ''}`}
                                style={isActive ? { backgroundColor: color, color: 'rgba(0,0,0,0.85)' } : undefined}
                                title={byte !== null ? `+${(row.offset + ci).toString(16)}: 0x${byte.toString(16).padStart(2, '0')} (${byte})` : ''}
                              >
                                {byte !== null ? fmtByte(byte, displayMode) : ''}
                              </span>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>

        <div className="anvil-stack-footer">
          <span className="anvil-stack-grow">&darr; PUSH decremente RSP</span>
        </div>
      </div>
    </div>
  )
})
