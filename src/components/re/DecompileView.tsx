import { useState, useEffect, useRef } from 'react'
import Editor, { type Monaco } from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import * as api from '../../api/client'
import type { DecompileResult } from '../../types/re'

interface DecompileViewProps {
  sessionId: string | null
  address: string | null
  selectedAddr?: string | null
  onSelectLine?: (addr: string) => void
  onMissing?: () => void
}

export function DecompileView({ sessionId, address, selectedAddr, onSelectLine, onMissing }: DecompileViewProps) {
  const [result, setResult] = useState<DecompileResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)
  const monacoRef = useRef<Monaco | null>(null)
  const decorationsRef = useRef<editor.IEditorDecorationsCollection | null>(null)

  useEffect(() => {
    if (!sessionId || !address) return
    setLoading(true)
    setError(null)
    api.reDecompile(sessionId, address)
      .then(setResult)
      .catch((e: Error & { code?: string }) => {
        if (e.code === 'DECOMPILER_MISSING') onMissing?.()
        setError(e.message)
      })
      .finally(() => setLoading(false))
  }, [sessionId, address, onMissing])

  // Highlight the line that contains the selected address (best-effort heuristic)
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current || !result?.code) return
    const ed = editorRef.current
    const monaco = monacoRef.current

    if (!selectedAddr) {
      decorationsRef.current?.clear()
      return
    }

    // Search for hex (0xADDR or just ADDR without 0x) in the decompiled code
    const addrNum = parseInt(selectedAddr, 16)
    const variants = [
      selectedAddr.toLowerCase(),
      `0x${addrNum.toString(16)}`,
      `0x${addrNum.toString(16).toUpperCase()}`,
      addrNum.toString(16),
    ]
    const lines = result.code.split('\n')
    let foundLine = -1
    for (let i = 0; i < lines.length; i++) {
      const lower = lines[i].toLowerCase()
      if (variants.some(v => lower.includes(v.toLowerCase()))) {
        foundLine = i + 1
        break
      }
    }

    decorationsRef.current?.clear()
    if (foundLine > 0) {
      decorationsRef.current = ed.createDecorationsCollection([{
        range: new monaco.Range(foundLine, 1, foundLine, 1),
        options: {
          isWholeLine: true,
          className: 'anvil-decompile-line-highlight',
          marginClassName: 'anvil-decompile-line-margin',
        },
      }])
      ed.revealLineInCenterIfOutsideViewport(foundLine)
    }
  }, [selectedAddr, result])

  const handleMount = (ed: editor.IStandaloneCodeEditor, monaco: Monaco) => {
    editorRef.current = ed
    monacoRef.current = monaco
    // Click handler — emit selected address if line contains 0xADDR
    ed.onDidChangeCursorPosition(e => {
      if (!onSelectLine || !result?.code) return
      const lines = result.code.split('\n')
      const lineText = lines[e.position.lineNumber - 1] ?? ''
      const match = lineText.match(/0x[0-9a-fA-F]+/)
      if (match) onSelectLine(match[0].toLowerCase())
    })
  }

  if (!address) return (
    <div className="anvil-re-empty">
      <i className="fa-solid fa-code" /> Sélectionne une fonction à décompiler
    </div>
  )

  if (loading) return (
    <div className="anvil-re-loading">
      <i className="fa-solid fa-spinner fa-spin" /> Décompilation en cours…
    </div>
  )

  if (error) return (
    <div className="anvil-re-error">
      <i className="fa-solid fa-triangle-exclamation" /> {error}
      <div className="anvil-re-error-hint">rz-ghidra doit être installé : <code>rizin -H rzghidra</code></div>
    </div>
  )

  return (
    <div className="anvil-decompile-wrap">
      {result && (
        <div className="anvil-decompile-header">
          <span className="anvil-decompile-source">
            <i className="fa-solid fa-code-branch" /> {result.source ?? 'rz-ghidra'}
          </span>
          <span className="anvil-decompile-addr">{address}</span>
        </div>
      )}
      <div className="anvil-decompile-editor">
        <Editor
          language={result?.language ?? 'c'}
          value={result?.code ?? ''}
          theme="vs-dark"
          onMount={handleMount}
          options={{
            readOnly: true,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            fontSize: 13,
            fontFamily: 'var(--font-code, "Geist Mono", monospace)',
            lineNumbers: 'on',
            renderLineHighlight: 'line',
            padding: { top: 8 },
          }}
        />
      </div>
    </div>
  )
}
