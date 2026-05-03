import { useState, useEffect, useCallback, useRef } from 'react'
import * as api from '../../api/client'
import { tokenizeDisasm, tokenColor } from './disasmHighlight'
import type { RizinOp } from '../../types/re'

interface DisasmViewProps {
  sessionId: string | null
  address: string | null
  selectedAddr?: string | null
  onSelectLine?: (addr: string) => void
  onNavigate: (address: string) => void
}


export function DisasmView({ sessionId, address, selectedAddr, onSelectLine, onNavigate }: DisasmViewProps) {
  const [ops, setOps] = useState<RizinOp[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; op: RizinOp } | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!sessionId || !address) return
    setLoading(true)
    setError(null)
    api.reDisasmFunction(sessionId, address)
      .then(setOps)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, address])

  const handleContextMenu = useCallback((e: React.MouseEvent, op: RizinOp) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, op })
  }, [])

  const closeMenu = useCallback(() => setContextMenu(null), [])

  // Auto-scroll to selected line when it changes from outside (e.g. decompile click)
  useEffect(() => {
    if (selectedAddr && selectedRef.current) {
      selectedRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedAddr])

  if (!address) return (
    <div className="anvil-re-empty">
      <i className="fa-solid fa-arrow-pointer" /> Sélectionne une fonction dans la liste
    </div>
  )

  if (loading) return (
    <div className="anvil-re-loading">
      <i className="fa-solid fa-spinner fa-spin" /> Désassemblage…
    </div>
  )

  if (error) return (
    <div className="anvil-re-error">
      <i className="fa-solid fa-triangle-exclamation" /> {error}
    </div>
  )

  return (
    <div className="anvil-disasm-view" onClick={closeMenu}>
      <div className="anvil-disasm-scroll" ref={scrollRef}>
        {ops.map((op, i) => {
          const addrHex = `0x${op.offset.toString(16)}`
          const tokens = tokenizeDisasm(op.disasm ?? '')
          const isJump = op.jump != null
          const isSelected = selectedAddr != null && parseInt(selectedAddr, 16) === op.offset
          return (
            <div
              key={i}
              ref={isSelected ? selectedRef : undefined}
              className={`anvil-disasm-line${isJump ? ' anvil-disasm-line--jump' : ''}${isSelected ? ' anvil-disasm-line--selected' : ''}`}
              onContextMenu={e => handleContextMenu(e, op)}
              onClick={() => onSelectLine?.(addrHex)}
              data-addr={addrHex}
            >
              {/* Address */}
              <span className="anvil-disasm-addr">{addrHex}</span>
              {/* Bytes */}
              <span className="anvil-disasm-bytes">{op.bytes ?? ''}</span>
              {/* Instruction */}
              <span className="anvil-disasm-instr">
                {tokens.map((tok, ti) => {
                  const color = tokenColor(tok.kind, tok.kind === 'mnemonic' ? tok.text : undefined)
                  const isJumpTarget = tok.kind === 'immediate' && isJump
                  return (
                    <span
                      key={ti}
                      style={{ color }}
                      className={isJumpTarget ? 'anvil-disasm-target' : undefined}
                      onClick={isJumpTarget ? () => onNavigate(`0x${parseInt(tok.text, 16).toString(16)}`) : undefined}
                    >
                      {tok.text}
                    </span>
                  )
                })}
              </span>
              {/* Comment */}
              {op.comment && (
                <span className="anvil-disasm-comment"> ; {op.comment}</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Context menu */}
      {contextMenu && (
        <div
          className="anvil-context-menu"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button onClick={() => {
            navigator.clipboard.writeText(`0x${contextMenu.op.offset.toString(16)}`)
            closeMenu()
          }}>
            <i className="fa-solid fa-copy" /> Copier l'adresse
          </button>
          <button onClick={() => {
            onNavigate(`0x${contextMenu.op.offset.toString(16)}`)
            closeMenu()
          }}>
            <i className="fa-solid fa-arrow-right" /> Naviguer ici
          </button>
          {contextMenu.op.jump != null && (
            <button onClick={() => {
              onNavigate(`0x${contextMenu.op.jump!.toString(16)}`)
              closeMenu()
            }}>
              <i className="fa-solid fa-code-branch" /> Suivre le saut
            </button>
          )}
        </div>
      )}
    </div>
  )
}
