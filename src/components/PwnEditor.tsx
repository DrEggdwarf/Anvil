/**
 * PwnEditor — Monaco-based Python exploit editor with pwntools completions.
 */

import { useRef, useCallback } from 'react'
import Editor, { type OnMount, type BeforeMount } from '@monaco-editor/react'
import type * as Monaco from 'monaco-editor'
import { registerPwnCompletions } from './editor/pwnCompletions'

interface PwnEditorProps {
  value: string
  onChange: (value: string) => void
}

import { ANVIL_DARK_THEME, defineAnvilDarkTheme } from './editor/anvilMonacoTheme'

export default function PwnEditor({ value, onChange }: PwnEditorProps) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)

  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    defineAnvilDarkTheme(monaco)
    registerPwnCompletions(monaco)
  }, [])

  const handleMount: OnMount = useCallback((editor) => {
    editorRef.current = editor
    editor.focus()
  }, [])

  const handleChange = useCallback((val: string | undefined) => {
    if (val !== undefined) onChange(val)
  }, [onChange])

  return (
    <Editor
      height="100%"
      language="python"
      theme={ANVIL_DARK_THEME}
      value={value}
      onChange={handleChange}
      beforeMount={handleBeforeMount}
      onMount={handleMount}
      options={{
        fontSize: 12.5,
        fontFamily: "'Geist Mono', 'JetBrains Mono', 'Fira Code', monospace",
        lineHeight: 22,
        tabSize: 4,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        suggestOnTriggerCharacters: true,
        quickSuggestions: true,
        parameterHints: { enabled: true },
        wordBasedSuggestions: 'currentDocument',
        bracketPairColorization: { enabled: true },
        autoClosingBrackets: 'languageDefined',
        autoClosingQuotes: 'languageDefined',
        autoIndent: 'full',
        formatOnPaste: true,
        folding: true,
        lineNumbers: 'on',
        renderLineHighlight: 'line',
        cursorBlinking: 'smooth',
        cursorSmoothCaretAnimation: 'on',
        smoothScrolling: true,
        contextmenu: true,
        snippetSuggestions: 'top',
        padding: { top: 8, bottom: 8 },
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
        overviewRulerBorder: false,
        scrollbar: {
          verticalScrollbarSize: 6,
          horizontalScrollbarSize: 6,
          useShadows: false,
        },
      }}
    />
  )
}
