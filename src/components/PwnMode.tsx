import { useState, useRef, useCallback, useEffect } from 'react'
import type { usePwnSession } from '../hooks/usePwnSession'
import PwnEditor from './PwnEditor'
import SourceViewer from './SourceViewer'
import { AnvilTerminal } from './AnvilTerminal'
import { FilterableList } from './FilterableList'

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

type PwnSession = ReturnType<typeof usePwnSession>

interface PwnModeProps {
  session: PwnSession
  cols: number[]
  bodyRef: React.RefObject<HTMLDivElement | null>
  onColResize: (idx: number) => (e: React.MouseEvent) => void
}
type ToolPanel = 'cyclic' | 'rop' | 'fmtstr' | 'shellcraft' | 'asm' | null

/* ═══════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════ */

interface BinaryDropZoneProps {
  onLoad: (file: File) => void
  loading: boolean
  binaryName: string | null
}

function BinaryDropZone({ onLoad, loading, binaryName }: BinaryDropZoneProps) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) onLoad(file)
  }

  function handleClick() {
    inputRef.current?.click()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) onLoad(file)
  }

  if (binaryName) {
    return (
      <div className="anvil-pwn-binary-loaded">
        <i className="fa-solid fa-file-code" />
        <span className="anvil-pwn-binary-name">{binaryName}</span>
        <button className="anvil-pwn-reload-btn" onClick={handleClick} title="Charger un autre binaire">
          <i className="fa-solid fa-rotate" />
        </button>
        <input ref={inputRef} type="file" style={{ display: 'none' }} onChange={handleFileChange} />
      </div>
    )
  }

  return (
    <div
      className={`anvil-pwn-dropzone ${dragOver ? 'drag-over' : ''}`}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <input ref={inputRef} type="file" style={{ display: 'none' }} onChange={handleFileChange} />
      {loading ? (
        <i className="fa-solid fa-spinner fa-spin anvil-pwn-drop-icon" />
      ) : (
        <i className="fa-solid fa-crosshairs anvil-pwn-drop-icon" />
      )}
      <span className="anvil-pwn-drop-text">
        {loading ? 'Analyse du binaire...' : 'Drop un binaire ELF ici'}
      </span>
      <span className="anvil-pwn-drop-hint">Binaire ELF ou source (.c, .cpp, .rs, .go, .asm)</span>
    </div>
  )
}


interface SymbolsListProps {
  entries: { name: string; address: string }[]
  emptyText: string
}

function SymbolsList({ entries, emptyText }: SymbolsListProps) {
  return (
    <FilterableList
      items={entries}
      emptyText={emptyText}
      getFilterText={e => e.name}
      renderRow={s => (
        <>
          <span className="anvil-pwn-sym-addr">{s.address}</span>
          <span className="anvil-pwn-sym-name">{s.name}</span>
        </>
      )}
    />
  )
}

interface StringsListProps {
  entries: { offset: string; string: string }[]
}

function StringsList({ entries }: StringsListProps) {
  return (
    <FilterableList
      items={entries}
      emptyText="No strings found"
      placeholder="Filtrer strings..."
      maxDisplay={200}
      getFilterText={e => e.string}
      renderRow={s => (
        <>
          <span className="anvil-pwn-sym-addr">{s.offset}</span>
          <span className="anvil-pwn-sym-name anvil-pwn-str-val">{s.string}</span>
        </>
      )}
    />
  )
}

/* ═══════════════════════════════════════════════════════════
   Tool panels
   ═══════════════════════════════════════════════════════════ */

interface ToolPanelWrapProps {
  active: ToolPanel
  onClose: () => void
  session: PwnSession
}

function ToolPanelWrap({ active, onClose, session }: ToolPanelWrapProps) {
  if (!active) return null

  return (
    <div className="anvil-pwn-tool-panel">
      <div className="anvil-pwn-tool-header">
        <span className="anvil-pwn-tool-title">
          {active === 'cyclic' && 'Cyclic Pattern'}
          {active === 'rop' && 'ROP Gadgets'}
          {active === 'fmtstr' && 'Format String'}
          {active === 'shellcraft' && 'Shellcraft'}
          {active === 'asm' && 'Assemble / Disassemble'}
        </span>
        <button className="anvil-pwn-tool-close" onClick={onClose}>
          <i className="fa-solid fa-xmark" />
        </button>
      </div>
      <div className="anvil-pwn-tool-body">
        {active === 'cyclic' && <CyclicTool session={session} />}
        {active === 'rop' && <RopTool session={session} />}
        {active === 'fmtstr' && <FmtStrTool session={session} />}
        {active === 'shellcraft' && <ShellcraftTool session={session} />}
        {active === 'asm' && <AsmTool session={session} />}
      </div>
    </div>
  )
}

interface ToolProps { session: PwnSession }

function CyclicTool({ session }: ToolProps) {
  const [length, setLength] = useState('200')
  const [findVal, setFindVal] = useState('')
  const [result, setResult] = useState('')

  async function generate() {
    const hex = await session.cyclicGenerate(parseInt(length) || 200)
    if (hex) setResult(hex)
  }

  async function find() {
    const offset = await session.cyclicFind(findVal)
    if (offset !== null) setResult(`Offset: ${offset}`)
  }

  return (
    <div className="anvil-pwn-tool-form">
      <div className="anvil-pwn-tool-row">
        <label>Length</label>
        <input value={length} onChange={e => setLength(e.target.value)} type="number" min="1" max="100000" />
        <button className="anvil-pwn-tool-btn" onClick={generate}>Generate</button>
      </div>
      <div className="anvil-pwn-tool-row">
        <label>Find value</label>
        <input value={findVal} onChange={e => setFindVal(e.target.value)} placeholder="0x61616162 or baaa" />
        <button className="anvil-pwn-tool-btn" onClick={find}>Find</button>
      </div>
      {result && <pre className="anvil-pwn-tool-result">{result}</pre>}
    </div>
  )
}

function RopTool({ session }: ToolProps) {
  const [gadget, setGadget] = useState('pop rdi; ret')
  const [result, setResult] = useState('')

  async function search() {
    const instructions = gadget.split(';').map(s => s.trim()).filter(Boolean)
    const addr = await session.ropFindGadgets(instructions)
    if (addr) setResult(addr)
  }

  return (
    <div className="anvil-pwn-tool-form">
      <div className="anvil-pwn-tool-row">
        <label>Gadget</label>
        <input value={gadget} onChange={e => setGadget(e.target.value)} placeholder="pop rdi; ret" />
        <button className="anvil-pwn-tool-btn" onClick={search}>Search</button>
      </div>
      {result && <pre className="anvil-pwn-tool-result">Found @ {result}</pre>}
    </div>
  )
}

function FmtStrTool({ session }: ToolProps) {
  const [offset, setOffset] = useState('6')
  const [target, setTarget] = useState('')
  const [value, setValue] = useState('')
  const [result, setResult] = useState('')

  async function generate() {
    if (!target || !value) return
    const writes: Record<string, number> = { [target]: parseInt(value) }
    const hex = await session.fmtstrPayload(parseInt(offset), writes)
    if (hex) setResult(hex)
  }

  return (
    <div className="anvil-pwn-tool-form">
      <div className="anvil-pwn-tool-row">
        <label>Offset</label>
        <input value={offset} onChange={e => setOffset(e.target.value)} type="number" />
      </div>
      <div className="anvil-pwn-tool-row">
        <label>Target addr</label>
        <input value={target} onChange={e => setTarget(e.target.value)} placeholder="0x404028" />
      </div>
      <div className="anvil-pwn-tool-row">
        <label>Value</label>
        <input value={value} onChange={e => setValue(e.target.value)} placeholder="0x401196" />
      </div>
      <button className="anvil-pwn-tool-btn" onClick={generate}>Generate payload</button>
      {result && <pre className="anvil-pwn-tool-result">{result}</pre>}
    </div>
  )
}

function ShellcraftTool({ session }: ToolProps) {
  const [template, setTemplate] = useState('sh')
  const [result, setResult] = useState('')

  const templates = ['sh', 'cat', 'connect', 'dupsh', 'findpeersh', 'listen', 'readfile', 'write']

  async function generate() {
    const hex = await session.shellcraftGenerate(template)
    if (hex) setResult(hex)
  }

  return (
    <div className="anvil-pwn-tool-form">
      <div className="anvil-pwn-tool-row">
        <label>Template</label>
        <select value={template} onChange={e => setTemplate(e.target.value)}>
          {templates.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <button className="anvil-pwn-tool-btn" onClick={generate}>Generate</button>
      {result && <pre className="anvil-pwn-tool-result">{result}</pre>}
    </div>
  )
}

function AsmTool({ session }: ToolProps) {
  const [mode, setMode] = useState<'asm' | 'disasm'>('asm')
  const [input, setInput] = useState('')
  const [result, setResult] = useState('')

  async function run() {
    if (mode === 'asm') {
      const hex = await session.assembleCode(input)
      if (hex) setResult(hex)
    } else {
      const asm = await session.disassembleHex(input)
      if (asm) setResult(asm)
    }
  }

  return (
    <div className="anvil-pwn-tool-form">
      <div className="anvil-pwn-tool-row">
        <button className={`anvil-pwn-tab-btn ${mode === 'asm' ? 'active' : ''}`} onClick={() => setMode('asm')}>ASM → Hex</button>
        <button className={`anvil-pwn-tab-btn ${mode === 'disasm' ? 'active' : ''}`} onClick={() => setMode('disasm')}>Hex → ASM</button>
      </div>
      <textarea
        className="anvil-pwn-tool-textarea"
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder={mode === 'asm' ? 'nop\nxor rdi, rdi\nmov rax, 60\nsyscall' : '9048c7c03c000000 0f05'}
        rows={4}
      />
      <button className="anvil-pwn-tool-btn" onClick={run}>
        {mode === 'asm' ? 'Assemble' : 'Disassemble'}
      </button>
      {result && <pre className="anvil-pwn-tool-result">{result}</pre>}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Terminal (removed — using AnvilTerminal xterm.js instead)
   ═══════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════
   Checksec inline badges
   ═══════════════════════════════════════════════════════════ */

function ChecksecBadges({ data }: { data: PwnSession['checksecData'] }) {
  if (!data) return null
  const checks = [
    { label: 'RELRO', value: data.relro === 'full' ? 'Full' : data.relro === 'partial' ? 'Partial' : 'None', ok: data.relro === 'full' },
    { label: 'Canary', ok: data.canary },
    { label: 'NX', ok: data.nx },
    { label: 'PIE', ok: data.pie },
    { label: 'Fortify', ok: data.fortify },
  ]
  return (
    <div className="anvil-pwn-checksec-badges">
      {checks.map(c => (
        <span key={c.label} className={`anvil-pwn-badge ${c.ok ? 'ok' : 'vuln'}`} title={c.label}>
          <i className={`fa-solid ${c.ok ? 'fa-shield-halved' : 'fa-unlock'}`} />
          {c.label}{'value' in c ? ` ${c.value}` : ''}
        </span>
      ))}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Bottom panel tabs: Terminal | Symbols | GOT | PLT | Strings
   ═══════════════════════════════════════════════════════════ */

type BottomTab = 'terminal' | 'symbols' | 'got' | 'plt' | 'strings'

interface BottomPanelProps {
  session: PwnSession
  activeTab: BottomTab
  onTabChange: (tab: BottomTab) => void
  height: number
}

function BottomPanel({ session, activeTab, onTabChange, height }: BottomPanelProps) {
  const TABS: { id: BottomTab; label: string; icon: string; count?: number }[] = [
    { id: 'terminal', label: 'Terminal', icon: 'fa-terminal' },
    { id: 'symbols', label: 'Symbols', icon: 'fa-tag', count: session.symbols.length },
    { id: 'got', label: 'GOT', icon: 'fa-table-cells', count: session.gotEntries.length },
    { id: 'plt', label: 'PLT', icon: 'fa-right-left', count: session.pltEntries.length },
    { id: 'strings', label: 'Strings', icon: 'fa-font', count: session.elfStrings.length },
  ]

  // Convert PwnTermLine[] to TermLine[] for AnvilTerminal
  const termLines = session.lines.map(l => ({
    type: l.type === 'cmd' ? 'info' as const : l.type === 'output' ? 'output' as const : l.type as 'info' | 'error' | 'output',
    text: l.text,
  }))

  return (
    <div className="anvil-pwn-bottom" style={{ height }}>
      <div className="anvil-pwn-bottom-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`anvil-pwn-bottom-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => onTabChange(t.id)}
          >
            <i className={`fa-solid ${t.icon}`} />
            <span>{t.label}</span>
            {t.count !== undefined && t.count > 0 && (
              <span className="anvil-pwn-tab-count">{t.count}</span>
            )}
          </button>
        ))}
      </div>
      <div className="anvil-pwn-bottom-content">
        {activeTab === 'terminal' && (
          <AnvilTerminal lines={termLines} onClear={session.clearTerminal} />
        )}
        {activeTab === 'symbols' && <SymbolsList entries={session.symbols} emptyText="No symbols — load a binary" />}
        {activeTab === 'got' && <SymbolsList entries={session.gotEntries} emptyText="No GOT entries" />}
        {activeTab === 'plt' && <SymbolsList entries={session.pltEntries} emptyText="No PLT entries" />}
        {activeTab === 'strings' && <StringsList entries={session.elfStrings} />}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Main layout
   ═══════════════════════════════════════════════════════════ */

export function PwnMode({ session, cols, bodyRef, onColResize }: PwnModeProps) {
  const [activeTool, setActiveTool] = useState<ToolPanel>(null)
  const [bottomTab, setBottomTab] = useState<BottomTab>('terminal')
  const [bottomH, setBottomH] = useState(220)
  const rowDrag = useRef<{ startY: number; startH: number } | null>(null)
  const layoutRef = useRef<HTMLDivElement>(null)

  /* ── Row resize (editors ↔ bottom panel) ── */
  const onRowDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    rowDrag.current = { startY: e.clientY, startH: bottomH }
    document.body.style.cursor = 'row-resize'
    document.body.style.userSelect = 'none'
  }, [bottomH])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!rowDrag.current || !layoutRef.current) return
      const delta = rowDrag.current.startY - e.clientY
      const total = layoutRef.current.getBoundingClientRect().height
      const minH = 80
      const maxH = total * 0.7
      setBottomH(Math.max(minH, Math.min(rowDrag.current.startH + delta, maxH)))
    }
    const onUp = () => {
      if (rowDrag.current) {
        rowDrag.current = null
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [])

  const TOOLS: { id: ToolPanel; label: string; icon: string; desc: string }[] = [
    { id: 'cyclic', label: 'Cyclic', icon: 'fa-wave-square', desc: 'Pattern generator/finder' },
    { id: 'rop', label: 'ROP', icon: 'fa-link', desc: 'Gadget search' },
    { id: 'fmtstr', label: 'FmtStr', icon: 'fa-percent', desc: 'Format string payload' },
    { id: 'shellcraft', label: 'Shellcraft', icon: 'fa-scroll', desc: 'Shellcode generator' },
    { id: 'asm', label: 'ASM', icon: 'fa-microchip', desc: 'Assemble / Disassemble' },
  ]

  const binaryName = session.binaryPath?.split('/').pop() ?? null
  const hasSource = !!session.sourceCode && !!session.sourceLang

  return (
    <div className="anvil-pwn-layout" ref={(el) => {
      // Forward to both refs
      layoutRef.current = el;
      if (typeof bodyRef === 'object' && bodyRef) (bodyRef as React.MutableRefObject<HTMLDivElement | null>).current = el
    }}>
      {/* ── Top bar: binary + checksec + tools ── */}
      <div className="anvil-pwn-topbar">
        <BinaryDropZone
          onLoad={session.loadBinary}
          loading={session.loading}
          binaryName={binaryName}
        />
        <ChecksecBadges data={session.checksecData} />
        <div className="anvil-pwn-topbar-sep" />
        <div className="anvil-pwn-tools-inline">
          {TOOLS.map(t => (
            <button
              key={t.id}
              className={`anvil-pwn-tool-inline ${activeTool === t.id ? 'active' : ''}`}
              onClick={() => setActiveTool(activeTool === t.id ? null : t.id)}
              title={t.desc}
            >
              <i className={`fa-solid ${t.icon}`} />
              <span>{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Tool panel (slides open below topbar) */}
      {activeTool && (
        <ToolPanelWrap active={activeTool} onClose={() => setActiveTool(null)} session={session} />
      )}

      {/* ── Editors: Source (left) | Exploit (right) ── */}
      <div className="anvil-pwn-editors">
        {/* Left: Source viewer or placeholder */}
        <div className="anvil-pwn-editor-pane" style={{ width: cols[0] + '%' }}>
          <div className="anvil-pwn-pane-bar">
            <i className="fa-solid fa-code" />
            <span>{hasSource ? (binaryName?.replace(/\.[^.]+$/, '') ?? 'source') + '.' + session.sourceLang : 'Source'}</span>
            {hasSource && <span className="anvil-pwn-source-lang">{session.sourceLang?.toUpperCase()}</span>}
          </div>
          <div className="anvil-pwn-pane-body">
            {hasSource ? (
              <SourceViewer code={session.sourceCode!} language={session.sourceLang!} />
            ) : (
              <div className="anvil-pwn-pane-empty">
                <i className="fa-solid fa-file-code" />
                <span>Chargez un fichier source pour voir le code vulnérable</span>
              </div>
            )}
          </div>
        </div>

        {/* Resize handle */}
        <div className="anvil-resize-col" onMouseDown={onColResize(0)} />

        {/* Right: Exploit editor */}
        <div className="anvil-pwn-editor-pane" style={{ width: (100 - cols[0]) + '%' }}>
          <div className="anvil-pwn-pane-bar">
            <i className="fa-brands fa-python" style={{ color: '#3776ab' }} />
            <span>exploit.py</span>
            <span className="anvil-pwn-pane-tag">pwntools</span>
          </div>
          <div className="anvil-pwn-pane-body">
            <PwnEditor
              value={session.exploitCode}
              onChange={session.setExploitCode}
            />
          </div>
        </div>
      </div>

      {/* ── Horizontal resize handle ── */}
      <div className="anvil-resize-row" onMouseDown={onRowDown} />

      {/* ── Bottom panel: Terminal + data tabs ── */}
      <BottomPanel
        session={session}
        activeTab={bottomTab}
        onTabChange={setBottomTab}
        height={bottomH}
      />
    </div>
  )
}
