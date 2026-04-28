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

/* Anvil dark theme matching our CSS design tokens */
function defineAnvilTheme(monaco: typeof Monaco) {
  monaco.editor.defineTheme('anvil-dark', {
    base: 'vs-dark',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6a737d', fontStyle: 'italic' },
      { token: 'keyword', foreground: 'c586c0' },
      { token: 'keyword.control', foreground: 'c586c0' },
      { token: 'string', foreground: 'ce9178' },
      { token: 'number', foreground: 'b5cea8' },
      { token: 'type', foreground: '4ec9b0' },
      { token: 'identifier', foreground: '9cdcfe' },
      { token: 'delimiter', foreground: 'd4d4d4' },
      { token: 'function', foreground: 'dcdcaa' },
      { token: 'variable', foreground: '9cdcfe' },
      { token: 'operator', foreground: 'd4d4d4' },
      { token: 'decorator', foreground: 'dcdcaa' },
    ],
    colors: {
      'editor.background': '#0d1117',
      'editor.foreground': '#e6edf3',
      'editor.lineHighlightBackground': '#161b22',
      'editor.selectionBackground': '#264f7844',
      'editor.inactiveSelectionBackground': '#264f7822',
      'editorCursor.foreground': '#e040a0',
      'editorLineNumber.foreground': '#484f58',
      'editorLineNumber.activeForeground': '#e040a0',
      'editorGutter.background': '#0d1117',
      'editorWidget.background': '#161b22',
      'editorWidget.border': '#30363d',
      'editorSuggestWidget.background': '#161b22',
      'editorSuggestWidget.border': '#30363d',
      'editorSuggestWidget.selectedBackground': '#264f78',
      'input.background': '#0d1117',
      'input.border': '#30363d',
      'scrollbarSlider.background': '#484f5866',
      'scrollbarSlider.hoverBackground': '#484f5899',
      'minimap.background': '#0d1117',
    },
  })
}

export default function PwnEditor({ value, onChange }: PwnEditorProps) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)

  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    defineAnvilTheme(monaco)
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
      theme="anvil-dark"
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
