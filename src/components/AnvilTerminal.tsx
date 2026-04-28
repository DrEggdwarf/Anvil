import { useRef, useEffect, useState } from 'react'
import { Terminal as XTerm } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'
import type { TermLine } from '../hooks/useAnvilSession'

interface Props {
  lines: TermLine[]
  onClear: () => void
  /** Optional: callback when user types a command in the terminal */
  onInput?: (data: string) => void
}

const THEME = {
  background: '#111111',
  foreground: '#e0e0e0',
  cursor: '#4a9eff',
  cursorAccent: '#111111',
  selectionBackground: 'rgba(74,158,255,0.25)',
  black: '#111111',
  red: '#f04747',
  green: '#22c37a',
  yellow: '#f0a020',
  blue: '#4a9eff',
  magenta: '#e040a0',
  cyan: '#22c3c3',
  white: '#e0e0e0',
  brightBlack: '#606060',
  brightRed: '#f06060',
  brightGreen: '#30d090',
  brightYellow: '#f0c020',
  brightBlue: '#6ab4ff',
  brightMagenta: '#f060c0',
  brightCyan: '#40d8d8',
  brightWhite: '#ffffff',
}

const TYPE_COLORS: Record<string, string> = {
  info:   '\x1b[34m',   // blue (accent)
  error:  '\x1b[31m',   // red
  step:   '\x1b[90m',   // gray
  output: '\x1b[32m',   // green
}
const RESET = '\x1b[0m'

export function AnvilTerminal({ lines, onClear, onInput }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<XTerm | null>(null)
  const fitRef = useRef<FitAddon | null>(null)
  const lineCountRef = useRef(0)
  const [collapsed, setCollapsed] = useState(false)

  // Initialize xterm
  useEffect(() => {
    if (!containerRef.current) return

    // Cleanup any previous instance (React StrictMode)
    if (termRef.current) {
      termRef.current.dispose()
      termRef.current = null
      fitRef.current = null
    }

    const term = new XTerm({
      theme: THEME,
      fontFamily: "'Geist Mono', 'Fira Code', monospace",
      fontSize: 12,
      lineHeight: 1.6,
      cursorBlink: false,
      disableStdin: !onInput,
      scrollback: 5000,
      convertEol: true,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.loadAddon(new WebLinksAddon())

    term.open(containerRef.current)
    // Delay fit to ensure container has layout dimensions
    requestAnimationFrame(() => {
      try { fit.fit() } catch { /* ignore */ }
    })

    if (onInput) {
      term.onData((data) => onInput(data))
    }

    termRef.current = term
    fitRef.current = fit

    // Replay existing lines into fresh terminal
    lineCountRef.current = 0
    for (const line of lines) {
      const color = TYPE_COLORS[line.type] || ''
      const prefix = line.type === 'output' ? '' : '\u276f '
      term.writeln(`${color}${prefix}${line.text}${RESET}`)
    }
    lineCountRef.current = lines.length

    // Resize observer
    const container = containerRef.current
    const ro = new ResizeObserver(() => {
      try { fit.fit() } catch { /* ignore during teardown */ }
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      term.dispose()
      termRef.current = null
      fitRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Write new lines to xterm
  useEffect(() => {
    const term = termRef.current
    if (!term) return

    const newLines = lines.slice(lineCountRef.current)
    for (const line of newLines) {
      const color = TYPE_COLORS[line.type] || ''
      const prefix = line.type === 'output' ? '' : '❯ '
      term.writeln(`${color}${prefix}${line.text}${RESET}`)
    }
    lineCountRef.current = lines.length
  }, [lines])

  // Handle clear
  useEffect(() => {
    if (lines.length === 0 && termRef.current) {
      termRef.current.clear()
      lineCountRef.current = 0
    }
  }, [lines.length])

  // Refit when uncollapsed
  useEffect(() => {
    if (!collapsed) {
      setTimeout(() => fitRef.current?.fit(), 50)
    }
  }, [collapsed])

  return (
    <div className="anvil-terminal-drawer">
      <div className="anvil-terminal-bar" onClick={() => setCollapsed(!collapsed)} style={{ cursor: 'pointer' }}>
        <span className="anvil-terminal-bar-title">
          <i className="fa-solid fa-terminal" /> Terminal
        </span>
        <span className="anvil-terminal-line-count">{lines.length} lignes</span>
        <div className="anvil-terminal-bar-actions">
          <button className="anvil-file-btn" onClick={e => { e.stopPropagation(); onClear() }} title="Clear">
            <i className="fa-solid fa-trash-can" />
          </button>
          <button className="anvil-file-btn" onClick={(e) => { e.stopPropagation(); setCollapsed(!collapsed) }} title={collapsed ? 'Expand' : 'Collapse'}>
            <i className={`fa-solid ${collapsed ? 'fa-chevron-up' : 'fa-chevron-down'}`} />
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="anvil-xterm-container"
        style={collapsed ? { display: 'none' } : undefined}
      />
    </div>
  )
}
