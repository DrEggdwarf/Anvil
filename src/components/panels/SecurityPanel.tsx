const TOOLS = [
  { label: 'Checksec', desc: 'Protections du binaire', icon: 'fa-shield-halved' },
  { label: 'VMmap', desc: 'Mappings memoire', icon: 'fa-map' },
  { label: 'GOT', desc: 'Global Offset Table', icon: 'fa-table-cells' },
  { label: 'Cyclic', desc: 'Pattern De Bruijn', icon: 'fa-barcode' },
  { label: 'ROP', desc: 'Gadgets ROP', icon: 'fa-link' },
  { label: 'Strings', desc: 'Chaines du binaire', icon: 'fa-font' },
]

export function SecurityPanel() {
  return (
    <div className="anvil-panel-section-body">
      <div className="anvil-tool-cards">
        {TOOLS.map(t => (
          <div key={t.label} className="anvil-tool-card">
            <div className="anvil-tool-card-header">
              <i className={`fa-solid ${t.icon} anvil-tool-card-icon`} />
              <span className="anvil-tool-card-label">{t.label}</span>
            </div>
            <span className="anvil-tool-card-desc">{t.desc}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
