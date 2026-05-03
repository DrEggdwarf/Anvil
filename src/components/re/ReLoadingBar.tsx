import type { LoadingStep } from '../../hooks/useRizinSession'

interface ReLoadingBarProps {
  steps: LoadingStep[]
  binaryName: string
  error: string | null
  onRetry: () => void
}

export function ReLoadingBar({ steps, binaryName, error, onRetry }: ReLoadingBarProps) {
  const total = steps.length
  const done = steps.filter(s => s.status === 'done').length
  const pct = total > 0 ? Math.round((done / total) * 100) : 0
  const hasError = steps.some(s => s.status === 'error')

  return (
    <div className="anvil-re-loading">
      <div className="anvil-re-loading-card">
        <div className="anvil-re-loading-header">
          <i className="fa-solid fa-microchip" />
          <span className="anvil-re-loading-name">{binaryName}</span>
          {!hasError && <span className="anvil-re-loading-pct">{pct}%</span>}
        </div>

        {!hasError && (
          <div className="anvil-re-loading-track">
            <div
              className="anvil-re-loading-fill"
              style={{ width: `${pct}%` }}
            />
          </div>
        )}

        <div className="anvil-re-loading-steps">
          {steps.map(step => (
            <div
              key={step.id}
              className={`anvil-re-loading-step anvil-re-loading-step--${step.status}`}
            >
              <span className="anvil-re-loading-step-icon">
                {step.status === 'running' && <i className="fa-solid fa-spinner fa-spin" />}
                {step.status === 'done'    && <i className="fa-solid fa-check" />}
                {step.status === 'error'   && <i className="fa-solid fa-xmark" />}
                {step.status === 'pending' && <span className="anvil-re-step-dot" />}
              </span>
              <span className="anvil-re-loading-step-label">{step.label}</span>
            </div>
          ))}
        </div>

        {hasError && error && (
          <div className="anvil-re-loading-error">
            <i className="fa-solid fa-triangle-exclamation" />
            <span>{error}</span>
          </div>
        )}

        {hasError && (
          <button className="anvil-re-loading-retry" onClick={onRetry}>
            <i className="fa-solid fa-arrow-left" />
            Retour
          </button>
        )}
      </div>
    </div>
  )
}
