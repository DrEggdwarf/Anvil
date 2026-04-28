import { memo, useState, useCallback } from 'react'
import type { MemoryData, MemoryRegion, RegMap } from '../../hooks/useAnvilSession'

interface Props {
  memoryData: MemoryData | null
  memoryRegions: MemoryRegion[]
  registers: RegMap
  readMemory: (address: string, size?: number) => Promise<void>
  writeMemory: (address: string, hexData: string) => Promise<void>
  fetchMemoryMap: () => Promise<void>
}

const SIZES = [64, 128, 256, 512] as const

function isPrintable(b: number): boolean {
  return b >= 0x20 && b <= 0x7e
}

export const MemoryPanel = memo(function MemoryPanel({
  memoryData, memoryRegions, registers, readMemory, writeMemory, fetchMemoryMap,
}: Props) {
  const [addrInput, setAddrInput] = useState('$rip')
  const [size, setSize] = useState<number>(256)
  const [editIdx, setEditIdx] = useState<number | null>(null)
  const [editVal, setEditVal] = useState('')
  const [showMap, setShowMap] = useState(false)

  const doRead = useCallback(() => {
    if (addrInput.trim()) readMemory(addrInput.trim(), size)
  }, [addrInput, size, readMemory])

  const goTo = useCallback((addr: string) => {
    setAddrInput(addr)
    readMemory(addr, size)
  }, [size, readMemory])

  const commitEdit = useCallback(async () => {
    if (editIdx === null || !memoryData) return
    const val = editVal.replace(/\s/g, '')
    if (!/^[0-9a-fA-F]{2}$/.test(val)) { setEditIdx(null); return }
    const addr = '0x' + (memoryData.baseAddr + editIdx).toString(16)
    await writeMemory(addr, val)
    await readMemory('0x' + memoryData.baseAddr.toString(16), size)
    setEditIdx(null)
    setEditVal('')
  }, [editIdx, editVal, memoryData, writeMemory, readMemory, size])

  // Quick nav buttons from registers
  const shortcuts = [
    { label: 'RIP', expr: '$rip' },
    { label: 'RSP', expr: '$rsp' },
    { label: 'RBP', expr: '$rbp' },
  ]

  if (!memoryData) {
    return (
      <div className="anvil-panel-section-body">
        <div className="anvil-mem">
          <div className="anvil-mem-toolbar">
            <input
              className="anvil-mem-addr"
              value={addrInput}
              onChange={e => setAddrInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doRead()}
              placeholder="Adresse ou expression"
              spellCheck={false}
            />
            <select className="anvil-mem-size" value={size} onChange={e => setSize(Number(e.target.value))}>
              {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <button className="anvil-mem-go" onClick={doRead} title="Lire la memoire">
              <i className="fa-solid fa-magnifying-glass" />
            </button>
          </div>
          <div className="anvil-mem-shortcuts">
            {shortcuts.map(s => (
              <button key={s.label} className="anvil-mem-shortcut" onClick={() => goTo(s.expr)}>{s.label}</button>
            ))}
          </div>
          <div className="anvil-empty">
            <span>Memoire</span>
            <span className="anvil-empty-hint">Entrez une adresse pour inspecter la memoire</span>
          </div>
        </div>
      </div>
    )
  }

  const { baseAddr, bytes } = memoryData

  // Build rows of 16 bytes (classic hex dump)
  const rows: { addr: number; offset: number; cells: number[] }[] = []
  for (let i = 0; i < bytes.length; i += 16) {
    rows.push({
      addr: baseAddr + i,
      offset: i,
      cells: bytes.slice(i, i + 16),
    })
  }

  return (
    <div className="anvil-panel-section-body">
      <div className="anvil-mem">
        {/* Toolbar */}
        <div className="anvil-mem-toolbar">
          <input
            className="anvil-mem-addr"
            value={addrInput}
            onChange={e => setAddrInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doRead()}
            placeholder="Adresse ou expression"
            spellCheck={false}
          />
          <select className="anvil-mem-size" value={size} onChange={e => setSize(Number(e.target.value))}>
            {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <button className="anvil-mem-go" onClick={doRead} title="Rafraichir">
            <i className="fa-solid fa-magnifying-glass" />
          </button>
        </div>

        {/* Quick nav */}
        <div className="anvil-mem-shortcuts">
          {shortcuts.map(s => (
            <button key={s.label} className="anvil-mem-shortcut" onClick={() => goTo(s.expr)}>{s.label}</button>
          ))}
          <button
            className={`anvil-mem-shortcut map ${showMap ? 'active' : ''}`}
            onClick={() => { setShowMap(!showMap); if (!showMap && memoryRegions.length === 0) fetchMemoryMap() }}
          >
            MAP
          </button>
        </div>

        {/* Hex dump */}
        <div className="anvil-mem-dump">
          <div className="anvil-mem-header">
            <span className="anvil-mem-haddr">Address</span>
            <span className="anvil-mem-hhex">
              {Array.from({ length: 16 }, (_, i) => (
                <span key={i} className="anvil-mem-hcol">{i.toString(16).toUpperCase()}</span>
              ))}
            </span>
            <span className="anvil-mem-hascii">ASCII</span>
          </div>

          {rows.map((row) => {
            const addrHex = row.addr.toString(16).padStart(8, '0')
            // Highlight: check if RIP/RSP/RBP points into this row
            const rip = registers['rip'] ? Number(BigInt(registers['rip'])) : 0
            const rsp = registers['rsp'] ? Number(BigInt(registers['rsp'])) : 0
            let rowClass = 'anvil-mem-row'
            if (rip >= row.addr && rip < row.addr + 16) rowClass += ' rip-row'
            else if (rsp >= row.addr && rsp < row.addr + 16) rowClass += ' rsp-row'

            return (
              <div key={row.offset} className={rowClass}>
                <span className="anvil-mem-addr-col">{addrHex}</span>
                <span className="anvil-mem-hex">
                  {row.cells.map((b, ci) => {
                    const absIdx = row.offset + ci
                    const isEditing = editIdx === absIdx

                    if (isEditing) {
                      return (
                        <input
                          key={ci}
                          className="anvil-mem-edit"
                          value={editVal}
                          onChange={e => setEditVal(e.target.value.slice(0, 2))}
                          onKeyDown={e => {
                            if (e.key === 'Enter') commitEdit()
                            if (e.key === 'Escape') setEditIdx(null)
                          }}
                          onBlur={() => setEditIdx(null)}
                          autoFocus
                          maxLength={2}
                          spellCheck={false}
                        />
                      )
                    }

                    const isNonZero = b !== 0
                    return (
                      <span
                        key={ci}
                        className={`anvil-mem-byte${isNonZero ? ' nz' : ''}`}
                        onDoubleClick={() => { setEditIdx(absIdx); setEditVal(b.toString(16).padStart(2, '0')) }}
                        title={`0x${(row.addr + ci).toString(16)}: ${b} (0x${b.toString(16).padStart(2, '0')})`}
                      >
                        {b.toString(16).padStart(2, '0')}
                      </span>
                    )
                  })}
                </span>
                <span className="anvil-mem-ascii">
                  {row.cells.map((b, ci) => (
                    <span key={ci} className={isPrintable(b) ? 'printable' : ''}>{isPrintable(b) ? String.fromCharCode(b) : '.'}</span>
                  ))}
                </span>
              </div>
            )
          })}
        </div>

        {/* Memory map (collapsible) */}
        {showMap && (
          <div className="anvil-mem-map">
            <div className="anvil-mem-map-head">
              <span>Memory Map</span>
              <button className="anvil-mem-shortcut" onClick={fetchMemoryMap}><i className="fa-solid fa-rotate" /></button>
            </div>
            {memoryRegions.length === 0 ? (
              <div className="anvil-mem-map-empty">Aucune region (lancez le programme d'abord)</div>
            ) : (
              <div className="anvil-mem-map-list">
                {memoryRegions.map((r, i) => (
                  <div key={i} className="anvil-mem-map-row" onClick={() => goTo(r.start)}>
                    <span className="anvil-mem-map-addr">{r.start}</span>
                    <span className="anvil-mem-map-perms">{r.perms}</span>
                    <span className="anvil-mem-map-name">{r.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
})
