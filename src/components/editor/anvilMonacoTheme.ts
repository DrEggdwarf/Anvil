// Shared Monaco theme — extracted Sprint 16 to remove the duplicate definitions
// previously living inside PwnEditor.tsx and SourceViewer.tsx (ADR-018 quality gate).

import type * as Monaco from 'monaco-editor'

export const ANVIL_DARK_THEME = 'anvil-dark'

let _registered = false

/** Idempotent: defineTheme can be called multiple times safely, but we still skip work. */
export function defineAnvilDarkTheme(monaco: typeof Monaco): void {
  if (_registered) return
  monaco.editor.defineTheme(ANVIL_DARK_THEME, {
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
  _registered = true
}
