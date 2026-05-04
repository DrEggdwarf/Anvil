/* Agent settings — providers (BYOK), comportement, historique, audit (ADR-023). */

import { useCallback, useEffect, useState } from 'react'
import {
  agentAuditLog,
  agentDeleteSession,
  agentGetSettings,
  agentListSessions,
  agentPurgeSessions,
  agentTestProvider,
  agentUpdateSettings,
  type AgentProviderName,
  type AgentSessionSummary,
  type AgentSettingsView,
} from '../../api/client'

interface Props {
  open: boolean
  onClose: () => void
}

const PROVIDERS: AgentProviderName[] = ['anthropic', 'openai', 'openrouter', 'ollama']

export function AgentSettings({ open, onClose }: Props) {
  const [settings, setSettings] = useState<AgentSettingsView | null>(null)
  const [activeProv, setActiveProv] = useState<AgentProviderName>('anthropic')
  const [keyDraft, setKeyDraft] = useState('')
  const [modelDraft, setModelDraft] = useState('')
  const [baseDraft, setBaseDraft] = useState('')
  const [testStatus, setTestStatus] = useState<string | null>(null)
  const [sessions, setSessions] = useState<AgentSessionSummary[]>([])
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([])
  const [tab, setTab] = useState<'providers' | 'behavior' | 'history' | 'audit'>('providers')

  const refresh = useCallback(async () => {
    const s = await agentGetSettings()
    setSettings(s)
    setActiveProv(s.active_provider)
    const conf = s.providers[s.active_provider]
    setKeyDraft('')
    setModelDraft(conf.default_model)
    setBaseDraft(conf.base_url || '')
    const list = await agentListSessions()
    setSessions(list.sessions)
    const a = await agentAuditLog(100)
    setAudit(a.entries)
  }, [])

  useEffect(() => {
    if (open) refresh()
  }, [open, refresh])

  useEffect(() => {
    if (!settings) return
    const conf = settings.providers[activeProv]
    setKeyDraft('')
    setModelDraft(conf.default_model)
    setBaseDraft(conf.base_url || '')
    setTestStatus(null)
  }, [activeProv, settings])

  if (!open || !settings) return null

  const conf = settings.providers[activeProv]

  const saveProvider = async () => {
    const updated = await agentUpdateSettings({
      providers: {
        [activeProv]: {
          api_key: keyDraft || undefined,
          base_url: baseDraft || null,
          default_model: modelDraft,
        },
      },
    })
    setSettings(updated)
    setKeyDraft('')
    setTestStatus('Sauvegardé.')
  }

  const testNow = async () => {
    setTestStatus('Test en cours…')
    const r = await agentTestProvider(activeProv, {
      api_key: keyDraft || undefined,
      base_url: baseDraft || undefined,
      model: modelDraft || undefined,
    })
    setTestStatus(r.ok ? `OK (HTTP ${r.status ?? '?'})` : `Échec : ${r.error || r.status}`)
  }

  const setActive = async () => {
    const updated = await agentUpdateSettings({ active_provider: activeProv })
    setSettings(updated)
  }

  const updateBehavior = async (patch: Parameters<typeof agentUpdateSettings>[0]) => {
    const updated = await agentUpdateSettings(patch)
    setSettings(updated)
  }

  return (
    <div className="anvil-agent-settings-modal" role="dialog">
      <div className="anvil-agent-settings-backdrop" onClick={onClose} />
      <div className="anvil-agent-settings-card">
        <header className="anvil-agent-settings-header">
          <h2><i className="fa-solid fa-sparkles" /> Paramètres Agent</h2>
          <button type="button" className="anvil-agent-icon-btn" onClick={onClose}>
            <i className="fa-solid fa-xmark" />
          </button>
        </header>

        <nav className="anvil-agent-settings-tabs">
          {(['providers', 'behavior', 'history', 'audit'] as const).map(t => (
            <button
              key={t}
              type="button"
              className={tab === t ? 'active' : ''}
              onClick={() => setTab(t)}
            >
              {t === 'providers' ? 'Providers' : t === 'behavior' ? 'Comportement' : t === 'history' ? 'Historique' : 'Audit log'}
            </button>
          ))}
        </nav>

        <div className="anvil-agent-settings-body">
          {tab === 'providers' && (
            <div className="anvil-agent-providers">
              <div className="anvil-agent-prov-tabs">
                {PROVIDERS.map(p => (
                  <button
                    key={p}
                    type="button"
                    className={activeProv === p ? 'active' : ''}
                    onClick={() => setActiveProv(p)}
                  >
                    {p}
                    {settings.providers[p].has_key && <span className="anvil-agent-prov-dot" />}
                  </button>
                ))}
              </div>
              <div className="anvil-agent-prov-form">
                <label>
                  Clé API
                  <input
                    type="password"
                    value={keyDraft}
                    placeholder={conf.has_key ? conf.api_key_masked : 'sk-…'}
                    onChange={e => setKeyDraft(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  Modèle par défaut
                  <input value={modelDraft} onChange={e => setModelDraft(e.target.value)} />
                </label>
                <label>
                  Base URL (optionnel)
                  <input
                    value={baseDraft}
                    onChange={e => setBaseDraft(e.target.value)}
                    placeholder={activeProv === 'ollama' ? 'http://127.0.0.1:11434' : ''}
                  />
                </label>
                <div className="anvil-agent-prov-actions">
                  <button type="button" onClick={saveProvider}>
                    <i className="fa-solid fa-floppy-disk" /> Enregistrer
                  </button>
                  <button type="button" onClick={testNow}>
                    <i className="fa-solid fa-plug" /> Tester
                  </button>
                  <button
                    type="button"
                    onClick={setActive}
                    disabled={settings.active_provider === activeProv}
                    className="anvil-agent-btn-primary"
                  >
                    <i className="fa-solid fa-circle-check" /> Activer
                  </button>
                </div>
                {testStatus && <p className="anvil-agent-test-status">{testStatus}</p>}
                <p className="anvil-agent-prov-hint">
                  Provider actif : <strong>{settings.active_provider}</strong>
                </p>
              </div>
            </div>
          )}

          {tab === 'behavior' && (
            <div className="anvil-agent-behavior">
              <label className="anvil-agent-inline">
                <input
                  type="checkbox"
                  checked={settings.strict_mode}
                  onChange={e => updateBehavior({ strict_mode: e.target.checked })}
                />
                Strict mode (allowlist tools par module)
              </label>
              <label className="anvil-agent-inline">
                <input
                  type="checkbox"
                  checked={settings.allow_write_exec}
                  onChange={e => updateBehavior({ allow_write_exec: e.target.checked })}
                />
                Autoriser tools write/exec par défaut
              </label>
              <label>
                Token cap (output / session)
                <input
                  type="number"
                  min={100}
                  max={1_000_000}
                  value={settings.token_cap}
                  onChange={e => updateBehavior({ token_cap: Number(e.target.value) })}
                />
              </label>
              <label>
                Langue
                <select
                  value={settings.language}
                  onChange={e => updateBehavior({ language: e.target.value as 'fr' | 'en' })}
                >
                  <option value="fr">Français</option>
                  <option value="en">English</option>
                </select>
              </label>
            </div>
          )}

          {tab === 'history' && (
            <div className="anvil-agent-history">
              <div className="anvil-agent-history-actions">
                <button
                  type="button"
                  onClick={async () => {
                    if (!confirm('Supprimer toutes les conversations agent ?')) return
                    await agentPurgeSessions()
                    await refresh()
                  }}
                >
                  <i className="fa-solid fa-trash" /> Tout purger
                </button>
              </div>
              <ul>
                {sessions.map(s => (
                  <li key={s.id}>
                    <span className="anvil-agent-hist-title">{s.title}</span>
                    <span className="anvil-agent-hist-meta">
                      {s.module} · {s.provider} · {s.message_count} msg · {new Date(s.last_used).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      className="anvil-agent-icon-btn"
                      onClick={async () => {
                        await agentDeleteSession(s.id)
                        await refresh()
                      }}
                    >
                      <i className="fa-solid fa-xmark" />
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {tab === 'audit' && (
            <div className="anvil-agent-audit">
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Tool</th>
                    <th>ms</th>
                    <th>bytes</th>
                    <th>err</th>
                  </tr>
                </thead>
                <tbody>
                  {audit.map((e, i) => (
                    <tr key={i}>
                      <td>{String(e.ts ?? '')}</td>
                      <td><code>{String(e.tool ?? '')}</code></td>
                      <td>{String(e.duration_ms ?? '')}</td>
                      <td>{String(e.result_bytes ?? '')}</td>
                      <td>{e.error ? '⚠' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
