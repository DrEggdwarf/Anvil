import { useState, useCallback, useEffect, lazy, Suspense } from 'react'
import { invoke } from '@tauri-apps/api/core'
import { useColResize } from './hooks/useColResize'
import { useAnvilSession } from './hooks/useAnvilSession'
import { usePwnSession } from './hooks/usePwnSession'
import { EditorPanel } from './components/EditorPanel'
import { RegistersPane } from './components/RegistersPane'
import { AnvilTerminal } from './components/AnvilTerminal'
import { StackPanel } from './components/panels/StackPanel'
import { MemoryPanel } from './components/panels/MemoryPanel'
import { SecurityPanel } from './components/panels/SecurityPanel'
import './App.css'

// Sprint 15 fix #1: heavy modes are code-split out of the initial bundle.
// PwnMode pulls Monaco + xterm + the pwn completion table; ReferenceModal pulls
// the 6 reference datasets (~150 KB). Loading them lazily cuts initial JS by ~30-40%.
const PwnMode = lazy(() => import('./components/PwnMode').then(m => ({ default: m.PwnMode })))
const ReferenceModal = lazy(() =>
  import('./components/ReferenceModal').then(m => ({ default: m.ReferenceModal }))
)

function LazyFallback({ label }: { label: string }) {
  return (
    <div className="anvil-lazy-fallback">
      <i className="fa-solid fa-spinner fa-spin" /> Loading {label}…
    </div>
  )
}

type Mode = 'ASM' | 'RE' | 'Pwn' | 'Debug' | 'Firmware' | 'Protocols'

const MODE_ICONS: Record<Mode, string> = {
  ASM: 'fa-microchip',
  RE: 'fa-magnifying-glass-chart',
  Pwn: 'fa-skull-crossbones',
  Debug: 'fa-bug',
  Firmware: 'fa-hard-drive',
  Protocols: 'fa-network-wired',
}

const MODE_CAT: Record<Mode, string> = {
  ASM: 'asm',
  RE: 're',
  Pwn: 'pwn',
  Debug: 'dbg',
  Firmware: 'fw',
  Protocols: 'hw',
}

const SAMPLE = `section .data
    msg db "Hello, World!", 10
    len equ $ - msg

section .text
    global _start

_start:
    mov rax, 1
    mov rdi, 1
    mov rsi, msg
    mov rdx, len
    syscall

    mov rax, 60
    xor rdi, rdi
    syscall
`

function App() {
  const [mode, setMode] = useState<Mode>('ASM')
  const [backendOk, setBackendOk] = useState<boolean | null>(null)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [openPanels, setOpenPanels] = useState({ stack: true, memory: true, security: false })
  const [assembler, setAssembler] = useState<'nasm' | 'gas' | 'fasm'>('nasm')
  const [refOpen, setRefOpen] = useState(false)
  const [fileName] = useState('source.asm')
  const [code, setCode] = useState(SAMPLE)
  const [breakpoints, setBreakpoints] = useState<Set<number>>(new Set())

  const session = useAnvilSession()
  const pwnSession = usePwnSession()
  const { cols, bodyRef, onDown } = useColResize([30, 36, 34])
  const { cols: pwnCols, bodyRef: pwnBodyRef, onDown: pwnOnDown } = useColResize([45, 55])

  const toggleBp = useCallback((line: number) => {
    setBreakpoints(prev => {
      const next = new Set(prev)
      if (next.has(line)) next.delete(line); else next.add(line)
      return next
    })
    session.setBreakpoint(line)
  }, [session])

  // Cleanup sessions on unmount
  useEffect(() => {
    return () => { session.destroySessions(); pwnSession.destroySession() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function checkBackend() {
    try {
      const ok = await invoke<boolean>('check_backend')
      setBackendOk(ok)
    } catch {
      setBackendOk(false)
    }
  }

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next)
  }

  function togglePanel(key: keyof typeof openPanels) {
    setOpenPanels(p => ({ ...p, [key]: !p[key] }))
  }

  function handleDownload() {
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    a.click()
    URL.revokeObjectURL(url)
  }

  function handleOpen() {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.asm,.s,.S,.nasm'
    input.onchange = () => {
      const file = input.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => setCode(reader.result as string)
      reader.readAsText(file)
    }
    input.click()
  }

  const backendStatus = backendOk === null ? 'checking' : backendOk ? 'ok' : 'err'

  return (
    <main className="anvil-app" data-cat={MODE_CAT[mode]}>
      {/* ── Header ────────────────────────────────────────────── */}
      <header className="anvil-header">
        <span className="anvil-logo"><i className="fa-solid fa-hammer" /> AN<strong>VIL</strong></span>

        <nav className="anvil-modes">
          {(['ASM', 'RE', 'Pwn', 'Debug', 'Firmware', 'Protocols'] as Mode[]).map(m => (
            <button
              key={m}
              className={`anvil-mode-btn ${mode === m ? 'anvil-mode-btn--active' : ''}`}
              onClick={() => setMode(m)}
            >
              <i className={`fa-solid ${MODE_ICONS[m]}`} />
              {m}
            </button>
          ))}
        </nav>

        <div className="anvil-header-controls">
          <div className="anvil-ctrl-group">
            <button className="anvil-theme-btn" onClick={() => setRefOpen(true)} title="Reference">
              <i className="fa-solid fa-book" />
            </button>
            <button className="anvil-theme-btn" onClick={toggleTheme} title="Toggle theme">
              <i className={`fa-solid ${theme === 'dark' ? 'fa-moon' : 'fa-sun'}`} />
            </button>
          </div>

          <div className="anvil-ctrl-group">
            <span className={`anvil-status-dot anvil-status-dot--${backendStatus === 'ok' ? 'ok' : 'err'}`} />
            <button className="anvil-btn" onClick={checkBackend} style={{ border: 'none', background: 'none', padding: '2px 4px' }}>
              Backend
            </button>
          </div>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────────── */}
      {mode === 'Pwn' ? (
        <Suspense fallback={<LazyFallback label="Pwn mode" />}>
          <PwnMode
            session={pwnSession}
            cols={pwnCols}
            bodyRef={pwnBodyRef}
            onColResize={pwnOnDown}
          />
        </Suspense>
      ) : (
      <div className="anvil-body" ref={bodyRef}>
        {/* Column 1: Editor */}
        <div className="anvil-col anvil-col-editor" style={{ width: cols[0] + '%' }}>
          {/* File bar + assembler selector */}
          <div className="anvil-file-bar">
            <i className="fa-solid fa-file-code anvil-file-bar-icon" />
            <span className="anvil-file-bar-name">{fileName}</span>
            <span className="anvil-file-bar-sep" />
            <select
              className="anvil-asm-select"
              value={assembler}
              onChange={e => setAssembler(e.target.value as 'nasm' | 'gas' | 'fasm')}
            >
              <option value="nasm">NASM x86-64</option>
              <option value="gas">GAS (AT&T)</option>
              <option value="fasm">FASM</option>
            </select>
            <div className="anvil-file-bar-actions">
              <button className="anvil-file-btn" title="Open file" onClick={handleOpen}><i className="fa-solid fa-folder-open" /></button>
              <button className="anvil-file-btn" title="Download .asm" onClick={handleDownload}><i className="fa-solid fa-download" /></button>
            </div>
          </div>

          {/* Execution toolbar (compact) */}
          <div className="anvil-exec-toolbar">
            {/* Build & Run: compile + load into GDB */}
            <button
              className="anvil-tb-run"
              title="Compiler et lancer (F5)"
              disabled={session.compiling || session.running}
              onClick={() => session.buildAndRun(code, assembler)}
            >
              {session.compiling
                ? <i className="fa-solid fa-spinner fa-spin" />
                : <i className="fa-solid fa-hammer" />}
              Run <span className="anvil-kbd">F5</span>
            </button>
            {/* Play / Pause: auto-step toggle */}
            <button
              className={`anvil-tb-btn anvil-tb-playpause ${session.autoStepping ? 'active' : ''}`}
              title={session.autoStepping ? 'Mettre en pause l\'auto-step' : 'Lancer l\'auto-step'}
              onClick={() => session.autoStepping ? session.stopAutoStep() : session.startAutoStep()}
            >
              <i className={`fa-solid ${session.autoStepping ? 'fa-pause' : 'fa-play'}`} />
            </button>
            <span className="anvil-tb-div" />
            <div className="anvil-step-group">
              <button
                className="anvil-step-btn"
                title="Instruction precedente"
                onClick={() => session.stepBack()}
              >
                <i className="fa-solid fa-chevron-left" />
                <span className="anvil-step-label">Back</span>
              </button>
              <button
                className="anvil-step-btn"
                title="Entrer dans la fonction (F11)"
                onClick={() => session.stepInto()}
              >
                <i className="fa-solid fa-right-to-bracket" />
                <span className="anvil-step-label">Into</span>
              </button>
              <button
                className="anvil-step-btn"
                title="Passer par-dessus (F10)"
                onClick={() => session.stepOver()}
              >
                <i className="fa-solid fa-share" />
                <span className="anvil-step-label">Over</span>
              </button>
              <button
                className="anvil-step-btn"
                title="Sortir de la fonction (Shift+F11)"
                onClick={() => session.stepOut()}
              >
                <i className="fa-solid fa-right-from-bracket" />
                <span className="anvil-step-label">Out</span>
              </button>
              <button
                className="anvil-step-btn"
                title="Instruction suivante"
                onClick={() => session.stepOver()}
              >
                <i className="fa-solid fa-chevron-right" />
                <span className="anvil-step-label">Next</span>
              </button>
            </div>
            <span className="anvil-step-count">step {session.stepCount || '--'}</span>
          </div>

          <EditorPanel
            code={code}
            onChange={setCode}
            activeLine={session.activeLine}
            errorLine={session.errorLine}
            breakpoints={breakpoints}
            onToggleBreakpoint={toggleBp}
          />
        </div>

        {/* Resize handle 1 */}
        <div className="anvil-resize-col" onMouseDown={onDown(0)} />

        {/* Column 2: Registers + Terminal */}
        <div className="anvil-col anvil-col-regs" style={{ width: cols[1] + '%' }}>
          <RegistersPane registers={session.registers} prevRegisters={session.prevRegisters} />
          <AnvilTerminal lines={session.lines} onClear={session.clearTerminal} />
        </div>

        {/* Resize handle 2 */}
        <div className="anvil-resize-col" onMouseDown={onDown(1)} />

        {/* Column 3: Right panels (collapsible) */}
        {rightCollapsed ? (
          <div className="anvil-col-right-collapsed">
            <button className="anvil-tab-collapse" onClick={() => setRightCollapsed(false)} title="Expand">
              <i className="fa-solid fa-chevron-left" />
            </button>
          </div>
        ) : (
          <div className="anvil-col" style={{ width: cols[2] + '%' }}>
            <div className="anvil-right-toolbar">
              <button className="anvil-tab-collapse" onClick={() => setRightCollapsed(true)} title="Collapse">
                <i className="fa-solid fa-chevron-right" />
              </button>
            </div>

            <div className="anvil-stacked-panels">
              <div className="anvil-panel-section">
                <div className="anvil-panel-section-header" onClick={() => togglePanel('stack')}>
                  <i className={`fa-solid fa-chevron-right anvil-panel-section-arrow ${openPanels.stack ? 'open' : ''}`} />
                  <i className="fa-solid fa-layer-group anvil-panel-icon" />
                  <span className="anvil-panel-section-title">Stack</span>
                </div>
                {openPanels.stack && <StackPanel stackData={session.stackData} registers={session.registers} />}
              </div>

              <div className="anvil-panel-section">
                <div className="anvil-panel-section-header" onClick={() => togglePanel('memory')}>
                  <i className={`fa-solid fa-chevron-right anvil-panel-section-arrow ${openPanels.memory ? 'open' : ''}`} />
                  <i className="fa-solid fa-memory anvil-panel-icon" />
                  <span className="anvil-panel-section-title">Memory</span>
                </div>
                {openPanels.memory && <MemoryPanel
                  memoryData={session.memoryData}
                  memoryRegions={session.memoryRegions}
                  registers={session.registers}
                  readMemory={session.readMemory}
                  writeMemory={session.writeMemory}
                  fetchMemoryMap={session.fetchMemoryMap}
                />}
              </div>

              <div className="anvil-panel-section">
                <div className="anvil-panel-section-header" onClick={() => togglePanel('security')}>
                  <i className={`fa-solid fa-chevron-right anvil-panel-section-arrow ${openPanels.security ? 'open' : ''}`} />
                  <i className="fa-solid fa-shield-halved anvil-panel-icon" />
                  <span className="anvil-panel-section-title">Security</span>
                </div>
                {openPanels.security && <SecurityPanel sessionId={session.sessionId} binaryPath={session.binaryPath} />}
              </div>
            </div>
          </div>
        )}
      </div>
      )}

      {refOpen && (
        <Suspense fallback={<LazyFallback label="Reference" />}>
          <ReferenceModal
            open={refOpen}
            onClose={() => setRefOpen(false)}
            mode={MODE_CAT[mode] as import('./components/ReferenceModal').AppMode}
          />
        </Suspense>
      )}

      {/* ── Status Bar ────────────────────────────────────────── */}
      <footer className="anvil-statusbar">
        <span className="anvil-statusbar-item clickable">HEX</span>
        {mode === 'Pwn' ? (
          <span className="anvil-statusbar-item">{pwnSession.binaryInfo ? `${pwnSession.binaryInfo.arch} ${pwnSession.binaryInfo.bits}-bit` : 'No binary'}</span>
        ) : (
          <span className="anvil-statusbar-item">{assembler.toUpperCase()}</span>
        )}
        <span className="anvil-statusbar-item"><i className="fa-solid fa-microchip" /> {mode}</span>
        <div className="anvil-statusbar-right">
          <span className="anvil-statusbar-item">Step: {session.stepCount}</span>
          <span className={`anvil-status-dot anvil-status-dot--${backendStatus === 'ok' ? 'ok' : 'err'}`} />
        </div>
      </footer>
    </main>
  )
}

export default App
