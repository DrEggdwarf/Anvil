import { useRef, useState } from 'react'

interface ReEmptyStateProps {
  onOpenPath: (path: string) => void
  error?: string | null
}

export function ReEmptyState({ onOpenPath, error }: ReEmptyStateProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pathInputRef = useRef<HTMLInputElement>(null)
  const [hint, setHint] = useState<string | null>(null)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const path = (file as File & { path?: string }).path
    if (path) {
      onOpenPath(path)
    } else {
      // Browser / dev mode: file.path unavailable — pre-fill input with name
      // and show a hint so user can type the full absolute path
      if (pathInputRef.current) {
        pathInputRef.current.value = file.name
        pathInputRef.current.select()
        pathInputRef.current.focus()
        setHint(`Fichier sélectionné : ${file.name} — complète le chemin absolu puis Entrée`)
      }
    }
    e.target.value = ''
  }

  function handlePathKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      const val = (e.currentTarget).value.trim()
      if (val) onOpenPath(val)
    }
  }

  return (
    <div className="anvil-re-empty">
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: 'none' }}
        onChange={handleFile}
      />

      <div className="anvil-re-empty-card">
        <div className="anvil-re-empty-icon">
          <i className="fa-solid fa-microchip" />
        </div>

        <h2 className="anvil-re-empty-title">Reverse Engineering</h2>
        <p className="anvil-re-empty-desc">
          Charge un binaire pour démarrer l'analyse
        </p>

        <button
          className="anvil-re-empty-btn"
          onClick={() => fileInputRef.current?.click()}
        >
          <i className="fa-solid fa-folder-open" />
          Charger un binaire
        </button>

        <div className="anvil-re-empty-divider">
          <span>ou colle un chemin absolu</span>
        </div>

        <div className="anvil-re-empty-path-wrap">
          <input
            ref={pathInputRef}
            className="anvil-re-empty-path-input"
            placeholder="/chemin/vers/le/binaire"
            onKeyDown={handlePathKey}
          />
          <button
            className="anvil-re-empty-path-btn"
            onClick={() => {
              const val = pathInputRef.current?.value.trim()
              if (val) onOpenPath(val)
            }}
          >
            <i className="fa-solid fa-arrow-right" />
          </button>
        </div>

        {hint && (
          <p className="anvil-re-empty-hint">
            <i className="fa-solid fa-circle-info" /> {hint}
          </p>
        )}

        <p className="anvil-re-empty-formats">
          ELF · PE · Mach-O · .so · .bin · firmware
        </p>

        {error && (
          <div className="anvil-re-loading-error">
            <i className="fa-solid fa-triangle-exclamation" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  )
}
