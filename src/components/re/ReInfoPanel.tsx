import { useState, useEffect } from 'react'
import * as api from '../../api/client'
import type { RizinFunction, RizinXref } from '../../types/re'

interface ReInfoPanelProps {
  sessionId: string | null
  currentFunction: RizinFunction | null
  currentAddress: string | null
  onNavigate: (address: string) => void
  onRename: (address: string, newName: string) => void
}

export function ReInfoPanel({
  sessionId,
  currentFunction,
  currentAddress,
  onNavigate,
  onRename,
}: ReInfoPanelProps) {
  const [xrefsTo, setXrefsTo] = useState<RizinXref[]>([])
  const [xrefsFrom, setXrefsFrom] = useState<RizinXref[]>([])
  const [renaming, setRenaming] = useState(false)
  const [renameVal, setRenameVal] = useState('')

  useEffect(() => {
    if (!sessionId || !currentAddress) return
    setXrefsTo([])
    setXrefsFrom([])
    Promise.all([
      api.reXrefsTo(sessionId, currentAddress).catch(() => [] as RizinXref[]),
      api.reXrefsFrom(sessionId, currentAddress).catch(() => [] as RizinXref[]),
    ]).then(([to, from]) => {
      setXrefsTo(to)
      setXrefsFrom(from)
    })
  }, [sessionId, currentAddress])

  function startRename() {
    setRenameVal(currentFunction?.name ?? '')
    setRenaming(true)
  }

  function commitRename() {
    if (renameVal.trim() && currentAddress) {
      onRename(currentAddress, renameVal.trim())
    }
    setRenaming(false)
  }

  if (!currentFunction && !currentAddress) {
    return (
      <div className="anvil-re-infopanel anvil-re-empty">
        <i className="fa-solid fa-circle-info" /> Sélectionne une fonction
      </div>
    )
  }

  const fn = currentFunction

  return (
    <div className="anvil-re-infopanel">
      {/* Function header */}
      <div className="anvil-re-info-section">
        <div className="anvil-re-info-label">Fonction</div>
        <div className="anvil-re-info-name">
          {renaming ? (
            <input
              className="anvil-re-rename-input"
              value={renameVal}
              autoFocus
              onChange={e => setRenameVal(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') commitRename(); if (e.key === 'Escape') setRenaming(false) }}
              onBlur={commitRename}
            />
          ) : (
            <>
              <span className="anvil-re-info-fn-name" title={fn?.name}>{fn?.name ?? '—'}</span>
              {fn && (
                <button className="anvil-re-icon-btn" onClick={startRename} title="Renommer">
                  <i className="fa-solid fa-pen" />
                </button>
              )}
            </>
          )}
        </div>
        {fn && (
          <div className="anvil-re-info-meta">
            <InfoRow label="Adresse" value={`0x${fn.offset.toString(16)}`} />
            {fn.size != null && <InfoRow label="Taille" value={`${fn.size} octets`} />}
            {fn.nbinstr != null && <InfoRow label="Instructions" value={String(fn.nbinstr)} />}
            {fn.nlocals != null && <InfoRow label="Locals" value={String(fn.nlocals)} />}
            {fn.nargs != null && <InfoRow label="Args" value={String(fn.nargs)} />}
          </div>
        )}
      </div>

      {/* Xrefs to */}
      {xrefsTo.length > 0 && (
        <div className="anvil-re-info-section">
          <div className="anvil-re-info-label">Appelé depuis ({xrefsTo.length})</div>
          <div className="anvil-re-xref-list">
            {xrefsTo.slice(0, 10).map((x, i) => (
              <button
                key={i}
                className="anvil-re-xref-item"
                onClick={() => onNavigate(`0x${x.from.toString(16)}`)}
                title={x.type}
              >
                <i className="fa-solid fa-arrow-left" />
                <span>{`0x${x.from.toString(16)}`}</span>
                {x.type && <span className="anvil-re-xref-type">{x.type}</span>}
              </button>
            ))}
            {xrefsTo.length > 10 && (
              <span className="anvil-re-xref-more">+{xrefsTo.length - 10} autres</span>
            )}
          </div>
        </div>
      )}

      {/* Xrefs from */}
      {xrefsFrom.length > 0 && (
        <div className="anvil-re-info-section">
          <div className="anvil-re-info-label">Appels sortants ({xrefsFrom.length})</div>
          <div className="anvil-re-xref-list">
            {xrefsFrom.slice(0, 10).map((x, i) => (
              <button
                key={i}
                className="anvil-re-xref-item"
                onClick={() => onNavigate(`0x${x.to.toString(16)}`)}
                title={x.type}
              >
                <i className="fa-solid fa-arrow-right" />
                <span>{`0x${x.to.toString(16)}`}</span>
                {x.type && <span className="anvil-re-xref-type">{x.type}</span>}
              </button>
            ))}
            {xrefsFrom.length > 10 && (
              <span className="anvil-re-xref-more">+{xrefsFrom.length - 10} autres</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="anvil-re-info-row">
      <span className="anvil-re-info-row-label">{label}</span>
      <span className="anvil-re-info-row-value">{value}</span>
    </div>
  )
}
