import { useState, useEffect, useCallback } from 'react'
import * as api from '../../api/client'
import type { ChecksecData, SectionInfo, StringEntry } from '../../api/client'

interface SecurityPanelProps {
  sessionId: string | null
  binaryPath: string | null
}

type Tab = 'checksec' | 'sections' | 'strings'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'checksec', label: 'Checksec', icon: 'fa-shield-halved' },
  { id: 'sections', label: 'Sections', icon: 'fa-layer-group' },
  { id: 'strings', label: 'Strings', icon: 'fa-font' },
]

function extractFilename(path: string): string {
  return path.split('/').pop() || ''
}

/* ── Checksec sub-view ──────────────────────────────────── */

function ChecksecView({ data }: { data: ChecksecData }) {
  const checks = [
    { label: 'RELRO', value: data.relro, ok: data.relro === 'full' },
    { label: 'Stack Canary', value: data.canary ? 'Found' : 'Not found', ok: data.canary },
    { label: 'NX (No Execute)', value: data.nx ? 'Enabled' : 'Disabled', ok: data.nx },
    { label: 'PIE', value: data.pie ? 'Enabled' : 'Disabled', ok: data.pie },
    { label: 'RPATH', value: data.rpath ? 'Set' : 'Not set', ok: !data.rpath },
    { label: 'RUNPATH', value: data.runpath ? 'Set' : 'Not set', ok: !data.runpath },
    { label: 'Symbols', value: data.symbols ? 'Present' : 'Stripped', ok: false },
    { label: 'Fortify', value: data.fortify ? 'Enabled' : 'Disabled', ok: data.fortify },
  ]
  return (
    <div className="anvil-sec-checksec">
      {checks.map(c => (
        <div key={c.label} className="anvil-sec-check-row">
          <i className={`fa-solid ${c.ok ? 'fa-check' : 'fa-xmark'} anvil-sec-check-icon ${c.ok ? 'ok' : 'bad'}`} />
          <span className="anvil-sec-check-label">{c.label}</span>
          <span className={`anvil-sec-check-value ${c.ok ? 'ok' : 'bad'}`}>{c.value}</span>
        </div>
      ))}
    </div>
  )
}

/* ── Sections sub-view ──────────────────────────────────── */

function SectionsView({ data }: { data: SectionInfo[] }) {
  if (!data.length) return <div className="anvil-empty"><span className="anvil-empty-hint">Aucune section</span></div>
  return (
    <div className="anvil-sec-table-wrap">
      <table className="anvil-sec-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Type</th>
            <th>Address</th>
            <th>Size</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s, i) => (
            <tr key={i}>
              <td className="anvil-sec-cell-name">{s.name}</td>
              <td className="anvil-sec-cell-type">{s.type}</td>
              <td className="anvil-sec-cell-addr">{s.address}</td>
              <td className="anvil-sec-cell-size">{s.size}</td>
              <td className="anvil-sec-cell-flags">{s.flags}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Strings sub-view ───────────────────────────────────── */

function StringsView({ data }: { data: StringEntry[] }) {
  if (!data.length) return <div className="anvil-empty"><span className="anvil-empty-hint">Aucune chaine trouvee</span></div>
  return (
    <div className="anvil-sec-table-wrap">
      <table className="anvil-sec-table">
        <thead>
          <tr>
            <th>Offset</th>
            <th>String</th>
          </tr>
        </thead>
        <tbody>
          {data.map((s, i) => (
            <tr key={i}>
              <td className="anvil-sec-cell-addr">{s.offset}</td>
              <td className="anvil-sec-cell-str">{s.string}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Main SecurityPanel ─────────────────────────────────── */

export function SecurityPanel({ sessionId, binaryPath }: SecurityPanelProps) {
  const [tab, setTab] = useState<Tab>('checksec')
  const [loading, setLoading] = useState(false)
  const [checksecData, setChecksecData] = useState<ChecksecData | null>(null)
  const [sectionsData, setSectionsData] = useState<SectionInfo[]>([])
  const [stringsData, setStringsData] = useState<StringEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const filename = binaryPath ? extractFilename(binaryPath) : null

  const fetchTab = useCallback(async (which: Tab) => {
    if (!sessionId || !filename) return
    setLoading(true)
    setError(null)
    try {
      switch (which) {
        case 'checksec': {
          const res = await api.checksec(sessionId, filename)
          setChecksecData(res)
          break
        }
        case 'sections': {
          const res = await api.sections(sessionId, filename)
          setSectionsData(res.sections)
          break
        }
        case 'strings': {
          const res = await api.strings(sessionId, filename)
          setStringsData(res.strings)
          break
        }
      }
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [sessionId, filename])

  // Auto-fetch when binary changes
  useEffect(() => {
    if (sessionId && filename) {
      fetchTab('checksec')
    } else {
      setChecksecData(null)
      setSectionsData([])
      setStringsData([])
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, filename])

  function handleTabClick(t: Tab) {
    setTab(t)
    // Lazy-load: fetch if we don't have data yet
    if (t === 'sections' && !sectionsData.length && sessionId && filename) fetchTab(t)
    if (t === 'strings' && !stringsData.length && sessionId && filename) fetchTab(t)
  }

  if (!sessionId || !filename) {
    return (
      <div className="anvil-panel-section-body">
        <div className="anvil-empty">
          <i className="fa-solid fa-shield-halved anvil-empty-icon" />
          <span>Compilez un binaire pour analyser</span>
          <span className="anvil-empty-hint">Checksec, sections, strings</span>
        </div>
      </div>
    )
  }

  return (
    <div className="anvil-panel-section-body">
      {/* Tab bar */}
      <div className="anvil-sec-tabs">
        {TABS.map(t => (
          <button
            key={t.id}
            className={`anvil-sec-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => handleTabClick(t.id)}
          >
            <i className={`fa-solid ${t.icon}`} />
            {t.label}
          </button>
        ))}
        <button
          className="anvil-sec-refresh"
          onClick={() => fetchTab(tab)}
          disabled={loading}
          title="Rafraichir"
        >
          <i className={`fa-solid fa-arrows-rotate ${loading ? 'fa-spin' : ''}`} />
        </button>
      </div>

      {/* Content */}
      {error && <div className="anvil-sec-error"><i className="fa-solid fa-triangle-exclamation" /> {error}</div>}
      {loading && !error && (
        <div className="anvil-empty">
          <i className="fa-solid fa-spinner fa-spin anvil-empty-icon" />
          <span>Analyse en cours...</span>
        </div>
      )}
      {!loading && !error && tab === 'checksec' && checksecData && <ChecksecView data={checksecData} />}
      {!loading && !error && tab === 'sections' && <SectionsView data={sectionsData} />}
      {!loading && !error && tab === 'strings' && <StringsView data={stringsData} />}
    </div>
  )
}
