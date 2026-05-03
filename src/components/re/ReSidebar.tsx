import { useState } from 'react'
import { FilterableList } from '../FilterableList'
import type { RizinFunction, RizinString, RizinImport, RizinExport } from '../../types/re'

type SidebarTab = 'functions' | 'strings' | 'imports' | 'exports'

interface ReSidebarProps {
  functions: RizinFunction[]
  strings: RizinString[]
  imports: RizinImport[]
  exports: RizinExport[]
  currentAddress: string | null
  onNavigate: (address: string, fn?: RizinFunction) => void
  onLoadStrings: () => void
  onLoadImports: () => void
  onLoadExports: () => void
}

export function ReSidebar({
  functions,
  strings,
  imports,
  exports,
  currentAddress,
  onNavigate,
  onLoadStrings,
  onLoadImports,
  onLoadExports,
}: ReSidebarProps) {
  const [tab, setTab] = useState<SidebarTab>('functions')

  return (
    <div className="anvil-re-sidebar">
      {/* Tab bar */}
      <div className="anvil-re-sidebar-tabs">
        <button
          className={`anvil-re-sidebar-tab${tab === 'functions' ? ' active' : ''}`}
          onClick={() => setTab('functions')}
          title="Fonctions"
        >
          <span className="anvil-re-sidebar-tab-label">Fonctions</span>
          {functions.length > 0 && <span className="anvil-re-sidebar-tab-count">{functions.length}</span>}
        </button>
        <button
          className={`anvil-re-sidebar-tab${tab === 'strings' ? ' active' : ''}`}
          onClick={() => { setTab('strings'); if (!strings.length) onLoadStrings() }}
          title="Chaînes de caractères"
        >
          <span className="anvil-re-sidebar-tab-label">Chaînes</span>
          {strings.length > 0 && <span className="anvil-re-sidebar-tab-count">{strings.length}</span>}
        </button>
        <button
          className={`anvil-re-sidebar-tab${tab === 'imports' ? ' active' : ''}`}
          onClick={() => { setTab('imports'); if (!imports.length) onLoadImports() }}
          title="Imports"
        >
          <span className="anvil-re-sidebar-tab-label">Imports</span>
          {imports.length > 0 && <span className="anvil-re-sidebar-tab-count">{imports.length}</span>}
        </button>
        <button
          className={`anvil-re-sidebar-tab${tab === 'exports' ? ' active' : ''}`}
          onClick={() => { setTab('exports'); if (!exports.length) onLoadExports() }}
          title="Exports"
        >
          <span className="anvil-re-sidebar-tab-label">Exports</span>
          {exports.length > 0 && <span className="anvil-re-sidebar-tab-count">{exports.length}</span>}
        </button>
      </div>

      {/* Content */}
      <div className="anvil-re-sidebar-body">
        {tab === 'functions' && (
          <FilterableList<RizinFunction>
            items={functions}
            getFilterText={fn => fn.name}
            getKey={fn => fn.offset}
            placeholder="Filtrer fonctions…"
            emptyText="Aucune fonction — lancez l'analyse"
            className="anvil-re-list"
            renderRow={fn => {
              const addr = `0x${fn.offset.toString(16)}`
              const isActive = addr === currentAddress
              return (
                <div
                  key={fn.offset}
                  className={`anvil-re-list-row${isActive ? ' active' : ''}`}
                  onClick={() => onNavigate(addr, fn)}
                  title={`${fn.name} @ ${addr}`}
                >
                  <span className="anvil-re-list-icon">
                    {fn.name.startsWith('sym.imp.') ? (
                      <i className="fa-solid fa-download" style={{ color: 'var(--amber)' }} />
                    ) : fn.name.startsWith('sub.') ? (
                      <i className="fa-solid fa-code" style={{ color: '#6e7' }} />
                    ) : (
                      <i className="fa-solid fa-bolt" style={{ color: 'var(--accent)' }} />
                    )}
                  </span>
                  <span className="anvil-re-list-name">{fn.name}</span>
                  <span className="anvil-re-list-addr">{addr}</span>
                </div>
              )
            }}
          />
        )}

        {tab === 'strings' && (
          <FilterableList<RizinString>
            items={strings}
            getFilterText={s => s.string}
            getKey={(_, i) => i}
            placeholder="Filtrer chaînes…"
            emptyText="Aucune chaîne"
            className="anvil-re-list"
            renderRow={(s, i) => (
              <div
                key={i}
                className="anvil-re-list-row"
                onClick={() => onNavigate(`0x${s.vaddr.toString(16)}`)}
                title={s.string}
              >
                <span className="anvil-re-list-icon">
                  <i className="fa-solid fa-quote-right" style={{ color: 'var(--blue)' }} />
                </span>
                <span className="anvil-re-list-name anvil-re-list-name--string">{s.string}</span>
                <span className="anvil-re-list-addr">{`0x${s.vaddr.toString(16)}`}</span>
              </div>
            )}
          />
        )}

        {tab === 'imports' && (
          <FilterableList<RizinImport>
            items={imports}
            getFilterText={imp => imp.name}
            getKey={(_, i) => i}
            placeholder="Filtrer imports…"
            emptyText="Aucun import"
            className="anvil-re-list"
            renderRow={(imp, i) => (
              <div key={i} className="anvil-re-list-row">
                <span className="anvil-re-list-icon">
                  <i className="fa-solid fa-download" style={{ color: 'var(--amber)' }} />
                </span>
                <span className="anvil-re-list-name">{imp.name}</span>
                <span className="anvil-re-list-meta">{imp.type}</span>
              </div>
            )}
          />
        )}

        {tab === 'exports' && (
          <FilterableList<RizinExport>
            items={exports}
            getFilterText={exp => exp.name}
            getKey={(_, i) => i}
            placeholder="Filtrer exports…"
            emptyText="Aucun export"
            className="anvil-re-list"
            renderRow={(exp, i) => (
              <div
                key={i}
                className="anvil-re-list-row"
                onClick={() => onNavigate(`0x${exp.vaddr.toString(16)}`)}
              >
                <span className="anvil-re-list-icon">
                  <i className="fa-solid fa-upload" style={{ color: 'var(--green)' }} />
                </span>
                <span className="anvil-re-list-name">{exp.name}</span>
                <span className="anvil-re-list-addr">{`0x${exp.vaddr.toString(16)}`}</span>
              </div>
            )}
          />
        )}
      </div>
    </div>
  )
}
