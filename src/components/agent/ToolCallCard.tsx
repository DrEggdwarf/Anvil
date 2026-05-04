/* Tool call card — expandable row inline in the chat (ADR-023). */

import { useState } from 'react'
import type { AgentToolCall } from '../../api/client'

interface Props {
  call: AgentToolCall
}

export function ToolCallCard({ call }: Props) {
  const [open, setOpen] = useState(false)
  const status = call.error ? 'error' : call.result !== undefined ? 'done' : 'running'
  const cat = call.destructive ? 'exec' : 'read'

  return (
    <div className={`anvil-agent-tool anvil-agent-tool--${cat} anvil-agent-tool--${status}`}>
      <button
        type="button"
        className="anvil-agent-tool-header"
        onClick={() => setOpen(o => !o)}
      >
        <i className={`fa-solid ${open ? 'fa-caret-down' : 'fa-caret-right'}`} />
        <i className="fa-solid fa-wrench anvil-agent-tool-icon" />
        <code className="anvil-agent-tool-name">{call.name}</code>
        <span className="anvil-agent-tool-status">
          {status === 'running' && <i className="fa-solid fa-spinner fa-spin" />}
          {status === 'done' && <i className="fa-solid fa-check" />}
          {status === 'error' && <i className="fa-solid fa-triangle-exclamation" />}
          {call.duration_ms != null && <span> {call.duration_ms} ms</span>}
        </span>
      </button>
      {open && (
        <div className="anvil-agent-tool-body">
          <div className="anvil-agent-tool-section">
            <span className="anvil-agent-tool-label">Arguments</span>
            <pre>{JSON.stringify(call.arguments, null, 2)}</pre>
          </div>
          {call.error ? (
            <div className="anvil-agent-tool-section">
              <span className="anvil-agent-tool-label">Erreur</span>
              <pre className="anvil-agent-tool-error">{call.error}</pre>
            </div>
          ) : call.result !== undefined ? (
            <div className="anvil-agent-tool-section">
              <span className="anvil-agent-tool-label">Résultat</span>
              <pre>{stringify(call.result)}</pre>
            </div>
          ) : null}
        </div>
      )}
    </div>
  )
}

function stringify(v: unknown): string {
  if (typeof v === 'string') return v
  try {
    const txt = JSON.stringify(v, null, 2)
    return txt.length > 4000 ? txt.slice(0, 4000) + '\n…(tronqué)' : txt
  } catch {
    return String(v)
  }
}
