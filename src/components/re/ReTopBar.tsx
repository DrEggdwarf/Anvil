import { useRef, useState } from 'react'
import type { RizinBinaryInfo } from '../../types/re'

interface ReTopBarProps {
  binaryPath: string | null
  binaryInfo: RizinBinaryInfo | null
  analyzing: boolean
  analyzeError: string | null
  analyzed: boolean
  functionCount: number
  onAnalyze: () => void
  onReset: () => void
}

export function ReTopBar({
  binaryPath,
  binaryInfo,
  analyzing,
  analyzeError,
  analyzed,
  functionCount,
  onAnalyze,
  onReset,
}: ReTopBarProps) {
  const binaryName = binaryPath?.split('/').pop() ?? null

  return (
    <div className="anvil-re-topbar">
      {/* Binary identity */}
      <div className="anvil-re-topbar-binary">
        <i className="fa-solid fa-microchip" />
        <span className="anvil-re-topbar-binary-name" title={binaryPath ?? ''}>
          {binaryName}
        </span>
        {functionCount > 0 && (
          <span className="anvil-re-topbar-count">{functionCount} fn</span>
        )}
      </div>

      {/* Re-analyze */}
      <button
        className={`anvil-re-topbar-btn${analyzing ? ' anvil-re-topbar-btn--spin' : ''}`}
        onClick={onAnalyze}
        disabled={analyzing}
        title="Relancer l'analyse"
      >
        {analyzing
          ? <><i className="fa-solid fa-spinner fa-spin" /> Analyse…</>
          : <><i className="fa-solid fa-rotate" /> Réanalyser</>
        }
      </button>

      {/* Error inline */}
      {analyzeError && (
        <span className="anvil-re-topbar-err">
          <i className="fa-solid fa-triangle-exclamation" /> {analyzeError}
        </span>
      )}

      {/* Security badges — right side */}
      {binaryInfo && (
        <div className="anvil-re-badges">
          <SecurityBadge label="PIE"    active={binaryInfo.pic ?? false} />
          <SecurityBadge label="RELRO"  active={binaryInfo.relro !== 'no' && binaryInfo.relro !== undefined} />
          <SecurityBadge label="NX"     active={binaryInfo.nx ?? false} />
          <SecurityBadge label="CANARY" active={binaryInfo.canary ?? false} />
          <SecurityBadge label="ASLR"   active={binaryInfo.aslr ?? false} />
          {binaryInfo.arch && (
            <span className="anvil-re-badge anvil-re-badge--info">{binaryInfo.arch} {binaryInfo.bits}b</span>
          )}
          {binaryInfo.type && (
            <span className="anvil-re-badge anvil-re-badge--info">{binaryInfo.type}</span>
          )}
        </div>
      )}

      {/* Close / reset */}
      <button
        className="anvil-re-topbar-close"
        onClick={onReset}
        title="Fermer le binaire"
      >
        <i className="fa-solid fa-xmark" />
      </button>
    </div>
  )
}

interface SecurityBadgeProps { label: string; active: boolean }
function SecurityBadge({ label, active }: SecurityBadgeProps) {
  return (
    <span className={`anvil-re-badge ${active ? 'anvil-re-badge--on' : 'anvil-re-badge--off'}`}>
      {label}
    </span>
  )
}


