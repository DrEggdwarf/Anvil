import { useState, useRef, useEffect } from 'react'
import type { TermLine } from '../hooks/useAnvilSession'

interface Props {
  lines: TermLine[]
  onClear: () => void
}

export function TerminalDrawer({ lines, onClear }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [lines.length])

  return (
    <div className="anvil-terminal-drawer">
      <div className="anvil-terminal-bar">
        <span className="anvil-terminal-bar-title">
          <i className="fa-solid fa-terminal" /> Terminal
        </span>
        <span className="anvil-terminal-line-count">{lines.length} lignes</span>
        <div className="anvil-terminal-bar-actions">
          <button className="anvil-file-btn" onClick={e => { e.stopPropagation(); onClear() }} title="Clear">
            <i className="fa-solid fa-trash-can" />
          </button>
          <button className="anvil-file-btn" onClick={() => setCollapsed(!collapsed)} title={collapsed ? 'Expand' : 'Collapse'}>
            <i className={`fa-solid ${collapsed ? 'fa-chevron-up' : 'fa-chevron-down'}`} />
          </button>
        </div>
      </div>
      {!collapsed && (
        <div className="anvil-terminal-output" ref={scrollRef} style={{ height: 140 }}>
          {lines.map((l, i) => (
            <div key={i} className={`anvil-terminal-line ${l.type}`}>
              <span className="anvil-terminal-prompt"><i className="fa-solid fa-angle-right" /></span> {l.text}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
