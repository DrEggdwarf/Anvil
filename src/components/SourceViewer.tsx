/**
 * SourceViewer — Read-only Monaco editor showing the target source code
 * with vulnerable patterns highlighted (red decorations).
 */

import { useRef, useCallback, useEffect } from 'react'
import Editor, { type OnMount, type BeforeMount } from '@monaco-editor/react'
import type * as Monaco from 'monaco-editor'
import { ANVIL_DARK_THEME, defineAnvilDarkTheme } from './editor/anvilMonacoTheme'

interface SourceViewerProps {
  code: string
  language: string  // 'c', 'cpp', 'rust', 'go', 'asm'
}

/* Vulnerable patterns per language */
const VULN_PATTERNS: Record<string, RegExp[]> = {
  c: [
    /\b(gets|sprintf|strcpy|strcat|scanf|vsprintf|realpath|getwd)\s*\(/g,
    /\b(printf|fprintf|snprintf|syslog|err|warn)\s*\(\s*[^"]/g,   // format string (non-literal first arg)
    /\b(system|popen|exec[lv]p?e?)\s*\(/g,
    /\b(malloc|calloc|realloc|free)\s*\(/g,
    /\b(read|write|recv|send|memcpy|memmove)\s*\(/g,
    /\bchar\s+\w+\s*\[\s*\d+\s*\]/g,  // stack buffers
    /\bsetuid\s*\(\s*0\s*\)/g,
  ],
  cpp: [
    /\b(gets|sprintf|strcpy|strcat|scanf|vsprintf)\s*\(/g,
    /\b(printf|fprintf|snprintf)\s*\(\s*[^"]/g,
    /\b(system|popen)\s*\(/g,
    /\b(new|delete)\b/g,
    /\b(reinterpret_cast|const_cast)\s*</g,
    /\bchar\s+\w+\s*\[\s*\d+\s*\]/g,
    /\bunsafe\b/g,
  ],
  rs: [
    /\bunsafe\b/g,
    /\b(ptr::copy|ptr::copy_nonoverlapping|ptr::write|ptr::read)\b/g,
    /\braw\b.*\bpointer\b/g,
    /\b(transmute|from_raw_parts)\b/g,
    /\bstd::mem::forget\b/g,
  ],
  go: [
    /\bunsafe\./g,
    /\bC\.\w+/g,  // CGo calls
    /\b(exec\.Command|os\.Exec)\b/g,
  ],
  asm: [
    /\b(syscall|int\s+0x80)\b/g,
    /\bjmp\s+r[a-z]+/g,  // indirect jumps
    /\bcall\s+r[a-z]+/g,  // indirect calls
  ],
}

function findVulnRanges(code: string, lang: string): { line: number; startCol: number; endCol: number; match: string }[] {
  const patterns = VULN_PATTERNS[lang] || VULN_PATTERNS.c || []
  const lines = code.split('\n')
  const results: { line: number; startCol: number; endCol: number; match: string }[] = []

  for (let i = 0; i < lines.length; i++) {
    const lineText = lines[i]
    // Skip comments
    const trimmed = lineText.trim()
    if (trimmed.startsWith('//') || trimmed.startsWith('/*') || trimmed.startsWith('*')) continue

    for (const pattern of patterns) {
      pattern.lastIndex = 0
      let m: RegExpExecArray | null
      while ((m = pattern.exec(lineText)) !== null) {
        results.push({
          line: i + 1,
          startCol: m.index + 1,
          endCol: m.index + m[0].length + 1,
          match: m[0],
        })
      }
    }
  }
  return results
}

/** Map our language IDs to Monaco language IDs */
function monacoLang(lang: string): string {
  switch (lang) {
    case 'c': case 'h': return 'c'
    case 'cpp': case 'cc': case 'cxx': case 'hpp': return 'cpp'
    case 'rs': return 'rust'
    case 'go': return 'go'
    case 'asm': case 's': return 'asm'  // fallback, Monaco doesn't have great ASM support
    default: return 'c'
  }
}


export default function SourceViewer({ code, language }: SourceViewerProps) {
  const editorRef = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null)
  const monacoRef = useRef<typeof Monaco | null>(null)
  const decorationsRef = useRef<Monaco.editor.IEditorDecorationsCollection | null>(null)

  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    defineAnvilDarkTheme(monaco)
    monacoRef.current = monaco
  }, [])

  const handleMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    applyVulnDecorations(code, language)
  }, [code, language])

  function applyVulnDecorations(src: string, lang: string) {
    const editor = editorRef.current
    const monaco = monacoRef.current
    if (!editor || !monaco) return

    const vulns = findVulnRanges(src, lang)
    const decorations: Monaco.editor.IModelDeltaDecoration[] = vulns.map(v => ({
      range: new monaco.Range(v.line, v.startCol, v.line, v.endCol),
      options: {
        inlineClassName: 'anvil-vuln-highlight',
        hoverMessage: { value: `⚠ Potentially vulnerable: \`${v.match}\`` },
        glyphMarginClassName: 'anvil-vuln-glyph',
        glyphMarginHoverMessage: { value: '⚠ Vulnerability' },
      },
    }))

    // Also highlight entire lines
    const vulnLines = new Set(vulns.map(v => v.line))
    for (const line of vulnLines) {
      decorations.push({
        range: new monaco.Range(line, 1, line, 1),
        options: {
          isWholeLine: true,
          className: 'anvil-vuln-line',
          overviewRuler: {
            color: '#e040a0',
            position: monaco.editor.OverviewRulerLane.Right,
          },
        },
      })
    }

    if (decorationsRef.current) {
      decorationsRef.current.clear()
    }
    decorationsRef.current = editor.createDecorationsCollection(decorations)
  }

  // Re-apply when code/language changes
  useEffect(() => {
    applyVulnDecorations(code, language)
  }, [code, language])

  return (
    <Editor
      height="100%"
      language={monacoLang(language)}
      theme={ANVIL_DARK_THEME}
      value={code}
      options={{
        readOnly: true,
        fontSize: 12,
        fontFamily: "'Geist Mono', 'JetBrains Mono', 'Fira Code', monospace",
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        folding: true,
        lineNumbers: 'on',
        renderLineHighlight: 'none',
        glyphMargin: true,
        contextmenu: false,
        padding: { top: 4, bottom: 4 },
        overviewRulerLanes: 1,
        overviewRulerBorder: false,
        scrollbar: {
          verticalScrollbarSize: 6,
          horizontalScrollbarSize: 6,
          useShadows: false,
        },
      }}
      beforeMount={handleBeforeMount}
      onMount={handleMount}
    />
  )
}
