import { useEffect, useState, useCallback } from 'react'
import * as api from '../../api/client'

interface HexViewProps {
  sessionId: string | null
  address: string | null
}

const PAGE_SIZE = 512

export function HexView({ sessionId, address }: HexViewProps) {
  const [text, setText] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [length, setLength] = useState(PAGE_SIZE)
  const [customAddr, setCustomAddr] = useState<string>('')

  const effectiveAddr = customAddr || address

  const fetchHex = useCallback(() => {
    if (!sessionId || !effectiveAddr) return
    setLoading(true)
    setError(null)
    api.reReadHexText(sessionId, effectiveAddr, length)
      .then(r => setText(r.output))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sessionId, effectiveAddr, length])

  useEffect(() => {
    fetchHex()
  }, [fetchHex])

  if (!address) return (
    <div className="anvil-re-empty">
      <i className="fa-solid fa-table-cells" /> Sélectionne une fonction pour voir le dump hex
    </div>
  )

  return (
    <div className="anvil-hex-wrap">
      <div className="anvil-hex-toolbar">
        <input
          type="text"
          className="anvil-hex-addr"
          placeholder={address ?? '0x…'}
          value={customAddr}
          onChange={e => setCustomAddr(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') fetchHex() }}
        />
        <select
          className="anvil-hex-length"
          value={length}
          onChange={e => setLength(parseInt(e.target.value, 10))}
        >
          <option value={256}>256 B</option>
          <option value={512}>512 B</option>
          <option value={1024}>1 KB</option>
          <option value={4096}>4 KB</option>
        </select>
        <button className="anvil-hex-refresh" onClick={fetchHex} title="Recharger">
          <i className="fa-solid fa-rotate" />
        </button>
      </div>

      <div className="anvil-hex-body">
        {loading && (
          <div className="anvil-re-loading">
            <i className="fa-solid fa-spinner fa-spin" /> Lecture mémoire…
          </div>
        )}
        {error && (
          <div className="anvil-re-error">
            <i className="fa-solid fa-triangle-exclamation" /> {error}
          </div>
        )}
        {!loading && !error && (
          <pre className="anvil-hex-dump">{text}</pre>
        )}
      </div>
    </div>
  )
}
