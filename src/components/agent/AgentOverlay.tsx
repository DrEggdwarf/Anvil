/* Agent overlay — FAB + widget + chat (ADR-023). One root component owns the
   open/closed state and switches between the entry widget and the chat panel. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAgentSession } from '../../hooks/useAgentSession'
import { useGlobalShortcut } from '../../hooks/useGlobalShortcut'
import { AgentMarkdown } from './AgentMarkdown'
import { ToolCallCard } from './ToolCallCard'

type ViewState = 'closed' | 'widget' | 'chat'

interface Props {
  /** Lower-case category from data-cat (asm, re, pwn, dbg, fw, hw). */
  cat: string
  /** Anvil session ids per bridge type (rizin, pwn, gdb, …). */
  anvilSessionIds: Record<string, string>
  /** Optional FAB tooltip / module label. */
  moduleLabel: string
  /** Open settings page. */
  onOpenSettings: () => void
}

const CHIP_LABELS: Record<string, string> = {
  asm: 'ASM',
  re: 'RE',
  pwn: 'Pwn',
  dbg: 'Debug',
  fw: 'Firmware',
  hw: 'Wire',
}

export function AgentOverlay({ cat, anvilSessionIds, moduleLabel, onOpenSettings }: Props) {
  const [view, setView] = useState<ViewState>('closed')
  const [allowWriteExec, setAllowWriteExec] = useState(false)
  const [chips, setChips] = useState<string[]>([cat])
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLTextAreaElement | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const session = useAgentSession()

  // Keep the default chip in sync with the active module while in the widget.
  useEffect(() => {
    setChips(prev => (prev.length === 0 ? [cat] : prev.includes(cat) ? prev : [cat, ...prev]))
  }, [cat])

  useEffect(() => {
    if (view === 'chat' && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [view, session.messages])

  const openWidget = useCallback(() => {
    if (session.messages.length > 0) {
      // Active chat → ⌘K = nouveau chat (archive l'ancien).
      session.reset()
    }
    setView('widget')
    setTimeout(() => inputRef.current?.focus(), 30)
  }, [session])

  useGlobalShortcut(openWidget)

  const submit = useCallback(async () => {
    const text = draft.trim()
    if (!text) return
    setDraft('')
    if (view === 'widget') setView('chat')
    await session.send(text, {
      module: cat,
      chips,
      anvilSessionIds,
      allowWriteExec,
    })
  }, [draft, view, session, cat, chips, anvilSessionIds, allowWriteExec])

  const closeOverlay = useCallback(() => setView('closed'), [])

  // Esc to close
  useEffect(() => {
    if (view === 'closed') return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation()
        closeOverlay()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [view, closeOverlay])

  const toggleChip = useCallback((c: string) => {
    setChips(prev => (prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]))
  }, [])

  const fabHasChat = session.messages.length > 0
  const allCats = useMemo(() => Object.keys(CHIP_LABELS), [])

  return (
    <>
      {view === 'closed' && (
        <AgentFab
          cat={cat}
          hasChat={fabHasChat}
          recent={session.recent}
          onResume={() => setView(fabHasChat ? 'chat' : 'widget')}
          onNew={() => {
            session.reset()
            setView('widget')
          }}
          onPickHistory={async (id) => {
            await session.loadSession(id)
            setView('chat')
          }}
        />
      )}

      {view !== 'closed' && (
        <div className={`anvil-agent-overlay anvil-agent-overlay--${cat}`} role="dialog" aria-label="Anvil Agent">
          <div className="anvil-agent-dim" onClick={closeOverlay} />
          <div
            className={`anvil-agent-panel anvil-agent-panel--${view}`}
            data-cat={cat}
          >
            {/* Header */}
            <div className="anvil-agent-header">
              <span className="anvil-agent-title">
                <i className="fa-solid fa-sparkles" /> Anvil Agent · {moduleLabel}
              </span>
              <div className="anvil-agent-header-controls">
                <label className="anvil-agent-toggle" title="Autoriser tools destructifs (write/exec)">
                  <input
                    type="checkbox"
                    checked={allowWriteExec}
                    onChange={e => setAllowWriteExec(e.target.checked)}
                  />
                  <span>{allowWriteExec ? '🔓 write/exec' : '🔒 lecture seule'}</span>
                </label>
                <button
                  type="button"
                  className="anvil-agent-icon-btn"
                  onClick={onOpenSettings}
                  title="Settings agent"
                >
                  <i className="fa-solid fa-gear" />
                </button>
                <button
                  type="button"
                  className="anvil-agent-icon-btn"
                  onClick={closeOverlay}
                  title="Fermer (Esc)"
                >
                  <i className="fa-solid fa-xmark" />
                </button>
              </div>
            </div>

            {/* Chips */}
            <div className="anvil-agent-chips">
              {allCats.map(c => (
                <button
                  type="button"
                  key={c}
                  className={`anvil-agent-chip ${chips.includes(c) ? 'anvil-agent-chip--on' : ''} ${c === cat ? 'anvil-agent-chip--module' : ''}`}
                  onClick={() => toggleChip(c)}
                  data-cat={c}
                >
                  {CHIP_LABELS[c]}
                </button>
              ))}
            </div>

            {/* Body — widget shows recent + textarea, chat shows messages + textarea */}
            {view === 'widget' && session.messages.length === 0 ? (
              <div className="anvil-agent-widget-body">
                {session.recent.length > 0 && (
                  <div className="anvil-agent-recent">
                    <span className="anvil-agent-recent-label">Récents</span>
                    <ul>
                      {session.recent.slice(0, 3).map(s => (
                        <li key={s.id}>
                          <button
                            type="button"
                            onClick={async () => {
                              await session.loadSession(s.id)
                              setView('chat')
                            }}
                            className="anvil-agent-recent-item"
                          >
                            <span className="anvil-agent-recent-title">{s.title}</span>
                            <span className="anvil-agent-recent-meta">{s.module} · {s.message_count} msg</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="anvil-agent-messages" ref={scrollRef}>
                {session.messages.map(m => (
                  <div key={m.id} className={`anvil-agent-msg anvil-agent-msg--${m.role}`}>
                    {m.role === 'tool' ? (
                      <pre className="anvil-agent-tool-output">{m.content}</pre>
                    ) : (
                      <>
                        <AgentMarkdown text={m.content} />
                        {m.toolCalls?.map(tc => (
                          <ToolCallCard key={tc.id} call={tc} />
                        ))}
                        {m.pending && !m.content && (
                          <span className="anvil-agent-typing">
                            <i className="fa-solid fa-spinner fa-spin" /> réflexion…
                          </span>
                        )}
                      </>
                    )}
                  </div>
                ))}
                {session.error && (
                  <div className="anvil-agent-msg anvil-agent-msg--error">
                    ⚠ {session.error}
                  </div>
                )}
              </div>
            )}

            {/* Input */}
            <form
              className="anvil-agent-input"
              onSubmit={e => {
                e.preventDefault()
                void submit()
              }}
            >
              <textarea
                ref={inputRef}
                value={draft}
                onChange={e => setDraft(e.target.value)}
                placeholder={`Demande à l'agent (${moduleLabel})…`}
                rows={2}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    void submit()
                  }
                }}
                disabled={session.phase === 'streaming'}
              />
              <div className="anvil-agent-input-controls">
                <span className="anvil-agent-hint">⏎ envoyer · ⇧⏎ saut de ligne · Esc fermer</span>
                {session.phase === 'streaming' ? (
                  <button type="button" className="anvil-agent-cancel" onClick={session.cancel}>
                    <i className="fa-solid fa-stop" /> Stop
                  </button>
                ) : (
                  <button type="submit" className="anvil-agent-send" disabled={!draft.trim()}>
                    <i className="fa-solid fa-paper-plane" />
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

// ── FAB sub-component ────────────────────────────────────
interface FabProps {
  cat: string
  hasChat: boolean
  recent: ReturnType<typeof useAgentSession>['recent']
  onResume: () => void
  onNew: () => void
  onPickHistory: (id: string) => void
}

function AgentFab({ cat, hasChat, recent, onResume, onNew, onPickHistory }: FabProps) {
  const [open, setOpen] = useState(false)
  return (
    <div className="anvil-agent-fab-wrap" data-cat={cat}>
      {open && hasChat && (
        <div className="anvil-agent-fab-tooltip" onMouseLeave={() => setOpen(false)}>
          <button type="button" onClick={onResume}>
            <i className="fa-solid fa-rotate-right" /> Reprendre
          </button>
          <button type="button" onClick={onNew}>
            <i className="fa-solid fa-plus" /> Nouveau chat
          </button>
          {recent.length > 0 && (
            <div className="anvil-agent-fab-history">
              <span>Historique</span>
              <ul>
                {recent.slice(0, 5).map(r => (
                  <li key={r.id}>
                    <button type="button" onClick={() => onPickHistory(r.id)}>
                      {r.title}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      <button
        type="button"
        className="anvil-agent-fab"
        title="Anvil Agent (⌘K)"
        onMouseEnter={() => hasChat && setOpen(true)}
        onClick={() => {
          if (hasChat) {
            onResume()
          } else {
            onNew()
          }
        }}
      >
        <i className="fa-solid fa-sparkles" />
      </button>
    </div>
  )
}
