import { useEffect, useState } from 'react'
import * as api from '../../api/client'
import type { RizinXref } from '../../types/re'

interface XrefsPanelProps {
  sessionId: string | null
  address: string | null
  onNavigate: (addr: string) => void
}

export function XrefsPanel({ sessionId, address, onNavigate }: XrefsPanelProps) {
  const [xrefsTo, setXrefsTo] = useState<RizinXref[]>([])
  const [xrefsFrom, setXrefsFrom] = useState<RizinXref[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId || !address) {
      setXrefsTo([])
      setXrefsFrom([])
      return
    }
    setLoading(true)
    setError(null)
    Promise.all([
      api.reXrefsTo(sessionId, address).catch(() => [] as RizinXref[]),
      api.reXrefsFrom(sessionId, address).catch(() => [] as RizinXref[]),
    ])
      .then(([to, from]) => {
        setXrefsTo(to)
        setXrefsFrom(from)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, address])

  if (!address) return (
    <div className="anvil-re-empty">
      <i className="fa-solid fa-arrows-left-right" /> Sélectionne une fonction pour voir ses références
    </div>
  )
  if (loading) return (
    <div className="anvil-re-loading">
      <i className="fa-solid fa-spinner fa-spin" /> Chargement des xrefs…
    </div>
  )
  if (error) return (
    <div className="anvil-re-error">
      <i className="fa-solid fa-triangle-exclamation" /> {error}
    </div>
  )

  const renderList = (items: RizinXref[], dir: 'to' | 'from') => {
    if (items.length === 0) {
      return <div className="anvil-xrefs-empty">— aucune —</div>
    }
    return (
      <ul className="anvil-xrefs-list">
        {items.map((x, i) => {
          const target = dir === 'to' ? x.from : x.to
          const targetHex = `0x${target.toString(16)}`
          return (
            <li key={i} className="anvil-xrefs-item" onClick={() => onNavigate(targetHex)}>
              <span className={`anvil-xrefs-type anvil-xrefs-type--${x.type ?? 'data'}`}>
                {x.type ?? '?'}
              </span>
              <span className="anvil-xrefs-addr">{targetHex}</span>
              {x.name && <span className="anvil-xrefs-name">{x.name}</span>}
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <div className="anvil-xrefs-wrap">
      <div className="anvil-xrefs-section">
        <div className="anvil-xrefs-header">
          <i className="fa-solid fa-arrow-right-to-bracket" />
          Appelé depuis ({xrefsTo.length})
        </div>
        {renderList(xrefsTo, 'to')}
      </div>

      <div className="anvil-xrefs-section">
        <div className="anvil-xrefs-header">
          <i className="fa-solid fa-arrow-right-from-bracket" />
          Référence vers ({xrefsFrom.length})
        </div>
        {renderList(xrefsFrom, 'from')}
      </div>
    </div>
  )
}
