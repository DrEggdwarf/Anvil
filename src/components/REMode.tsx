import { useState, useCallback } from 'react'
import { CfgView } from './re/CfgView'
import { DecompileView } from './re/DecompileView'
import { DisasmView } from './re/DisasmView'
import { XrefsPanel } from './re/XrefsPanel'
import { HexView } from './re/HexView'
import { ReSidebar } from './re/ReSidebar'
import { ReTopBar } from './re/ReTopBar'
import { ReEmptyState } from './re/ReEmptyState'
import { ReLoadingBar } from './re/ReLoadingBar'
import type { RizinSession } from '../hooks/useRizinSession'
import '../styles/re.css'

type RightTab = 'decompile' | 'disasm' | 'xrefs' | 'hex'

interface REModeProps {
  session: RizinSession
}

export function REMode({ session }: REModeProps) {
  const [rightTab, setRightTab] = useState<RightTab>('disasm')
  const [decompilerAvailable, setDecompilerAvailable] = useState(true)
  // ASM↔C sync — shared selected address (line-level highlight)
  const [selectedAddr, setSelectedAddr] = useState<string | null>(null)

  const navigate = useCallback((addr: string) => {
    session.navigate(addr)
  }, [session])

  const onDecompilerMissing = useCallback(() => {
    setDecompilerAvailable(false)
    setRightTab('disasm')
  }, [])

  // State machine
  const isEmpty   = !session.binaryPath && !session.opening
  const isLoading = session.opening

  if (isEmpty) {
    return (
      <div className="anvil-re-root">
        <ReEmptyState onOpenPath={session.openBinary} error={session.openError} />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="anvil-re-root">
        <ReLoadingBar
          steps={session.loadingSteps}
          binaryName={session.binaryPath?.split('/').pop() ?? '…'}
          error={session.openError}
          onRetry={session.destroySession}
        />
      </div>
    )
  }

  // isReady — 3-panel layout
  const fnAddr = session.currentFunction
    ? `0x${session.currentFunction.offset.toString(16)}`
    : null

  return (
    <div className="anvil-re-root">
      <ReTopBar
        binaryPath={session.binaryPath}
        binaryInfo={session.binaryInfo}
        analyzing={session.analyzing}
        analyzeError={session.analyzeError}
        analyzed={session.analyzed}
        functionCount={session.functions.length}
        onAnalyze={() => session.analyze()}
        onReset={session.destroySession}
      />

      <div className="anvil-re-body">
        {/* Left — function tree */}
        <div className="anvil-re-sidebar-wrap">
          <ReSidebar
            functions={session.functions}
            strings={session.strings}
            imports={session.imports}
            exports={session.exports}
            currentAddress={session.currentAddress}
            onNavigate={(addr, fn) => session.navigate(addr, fn ?? undefined)}
            onLoadStrings={session.loadSidebarData}
            onLoadImports={session.loadSidebarData}
            onLoadExports={session.loadSidebarData}
          />
        </div>

        {/* Center — CFG */}
        <div className="anvil-re-main">
          {fnAddr ? (
            <CfgView
              sessionId={session.sessionId}
              address={fnAddr}
              onNavigate={navigate}
            />
          ) : (
            <div className="anvil-re-center-hint">
              <i className="fa-solid fa-hand-pointer" />
              <span>Sélectionne une fonction dans la liste</span>
            </div>
          )}
        </div>

        {/* Right — pseudo-code / disasm / xrefs / hex */}
        <div className="anvil-re-right-panel">
          <div className="anvil-re-right-tabs">
            {decompilerAvailable && (
              <button
                className={`anvil-re-right-tab${rightTab === 'decompile' ? ' active' : ''}`}
                onClick={() => setRightTab('decompile')}
              >
                Pseudo-code
              </button>
            )}
            <button
              className={`anvil-re-right-tab${rightTab === 'disasm' ? ' active' : ''}`}
              onClick={() => setRightTab('disasm')}
            >
              Désassemblage
            </button>
            <button
              className={`anvil-re-right-tab${rightTab === 'xrefs' ? ' active' : ''}`}
              onClick={() => setRightTab('xrefs')}
            >
              Xrefs
            </button>
            <button
              className={`anvil-re-right-tab${rightTab === 'hex' ? ' active' : ''}`}
              onClick={() => setRightTab('hex')}
            >
              Hex
            </button>
          </div>
          <div className="anvil-re-right-body">
            {rightTab === 'decompile' && decompilerAvailable && (
              <DecompileView
                sessionId={session.sessionId}
                address={fnAddr}
                selectedAddr={selectedAddr}
                onSelectLine={setSelectedAddr}
                onMissing={onDecompilerMissing}
              />
            )}
            {rightTab === 'disasm' && (
              <DisasmView
                sessionId={session.sessionId}
                address={fnAddr}
                selectedAddr={selectedAddr}
                onSelectLine={setSelectedAddr}
                onNavigate={navigate}
              />
            )}
            {rightTab === 'xrefs' && (
              <XrefsPanel
                sessionId={session.sessionId}
                address={fnAddr}
                onNavigate={navigate}
              />
            )}
            {rightTab === 'hex' && (
              <HexView
                sessionId={session.sessionId}
                address={fnAddr}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

