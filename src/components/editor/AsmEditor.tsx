import { useState, useRef, useEffect, useLayoutEffect, useCallback, useMemo } from 'react'
import { tokenizeLine } from './tokenizer'
import { lintCode } from './linter'
import { computeFoldRegions } from './foldRegions'
import { COMPLETIONS, INSTR_INFO, kindIcon, kindClass, type CompletionItem } from './completions'

interface AsmEditorProps {
  code: string
  onChange: (code: string) => void
  activeLine: number
  errorLine?: number
  breakpoints?: Set<number>
  onToggleBreakpoint?: (line: number) => void
}

export default function AsmEditor({ code, onChange, activeLine, errorLine, breakpoints, onToggleBreakpoint }: AsmEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const highlightRef = useRef<HTMLPreElement>(null)
  const lineNumsRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<HTMLDivElement>(null)
  const acRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const findInputRef = useRef<HTMLInputElement>(null)
  const highlightLayerRef = useRef<HTMLDivElement>(null)
  const [charW, setCharW] = useState(7.22)

  // Undo / Redo
  const undoRef = useRef<string[]>([])
  const redoRef = useRef<string[]>([])
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSnapshotRef = useRef(code)

  const pushUndo = useCallback((snapshot: string) => {
    if (snapshot === undoRef.current[undoRef.current.length - 1]) return
    undoRef.current = [...undoRef.current.slice(-79), snapshot]
    redoRef.current = []
  }, [])

  const scheduleSnapshot = useCallback((prev: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => { pushUndo(prev); lastSnapshotRef.current = prev }, 400)
  }, [pushUndo])

  const handleChange = useCallback((newCode: string) => { scheduleSnapshot(code); onChange(newCode) }, [code, onChange, scheduleSnapshot])

  const handleUndo = useCallback(() => {
    if (debounceRef.current) { clearTimeout(debounceRef.current); debounceRef.current = null }
    if (lastSnapshotRef.current !== code && lastSnapshotRef.current !== undoRef.current[undoRef.current.length - 1]) pushUndo(lastSnapshotRef.current)
    const prev = undoRef.current.pop()
    if (prev === undefined) return
    redoRef.current.push(code); lastSnapshotRef.current = prev; onChange(prev)
  }, [code, onChange, pushUndo])

  const handleRedo = useCallback(() => {
    const next = redoRef.current.pop()
    if (next === undefined) return
    undoRef.current.push(code); lastSnapshotRef.current = next; onChange(next)
  }, [code, onChange])

  const [acVisible, setAcVisible] = useState(false)
  const [acItems, setAcItems] = useState<CompletionItem[]>([])
  const [acIndex, setAcIndex] = useState(0)
  const [acPos, setAcPos] = useState({ top: 0, left: 0 })
  const [acPrefix, setAcPrefix] = useState('')
  const [tooltip, setTooltip] = useState<{ text: string; syntax: string; cat: string; x: number; y: number } | null>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [scrollLeft, setScrollLeft] = useState(0)
  const [cursorWord, setCursorWord] = useState('')
  const [foldedLines, setFoldedLines] = useState<Set<number>>(new Set())
  const [findOpen, setFindOpen] = useState(false)
  const [findText, setFindText] = useState('')
  const [replaceText, setReplaceText] = useState('')
  const [findCaseSensitive, setFindCaseSensitive] = useState(false)

  const lines = useMemo(() => code.split('\n'), [code])
  const foldRegions = useMemo(() => computeFoldRegions(lines), [lines])
  const foldStash = useRef<Map<string, string[]>>(new Map())

  const toggleFold = useCallback((startLine: number) => {
    const region = foldRegions.find(r => r.start === startLine)
    if (!region) return
    const key = `${startLine}:${lines[startLine]}`
    if (foldedLines.has(startLine)) {
      // Unfold: restore stashed lines
      const stashed = foldStash.current.get(key)
      if (stashed) {
        const newLines = [...lines]
        const foldIdx = startLine + 1
        if (newLines[foldIdx]?.startsWith('; ... (')) newLines.splice(foldIdx, 1, ...stashed)
        else newLines.splice(foldIdx, 0, ...stashed)
        foldStash.current.delete(key)
        pushUndo(code)
        onChange(newLines.join('\n'))
      }
      setFoldedLines(prev => { const next = new Set(prev); next.delete(startLine); return next })
    } else {
      // Fold: remove lines and stash them
      const hidden = lines.slice(region.start + 1, region.end + 1)
      foldStash.current.set(key, hidden)
      const count = hidden.length
      const newLines = [...lines]
      newLines.splice(region.start + 1, count, `; ... (${count} lines)`)
      pushUndo(code)
      onChange(newLines.join('\n'))
      setFoldedLines(prev => { const next = new Set(prev); next.add(startLine); return next })
    }
  }, [code, lines, foldRegions, foldedLines, onChange, pushUndo])

  const hiddenLines = useMemo(() => new Set<number>(), [])

  const lintErrors = useMemo(() => lintCode(lines), [lines])

  const labelPositions = useMemo(() => {
    const map = new Map<string, number>()
    lines.forEach((line, i) => { const m = line.match(/^[ \t]*([a-zA-Z_.@$][a-zA-Z0-9_.@$]*):$/); if (m) map.set(m[1].toLowerCase(), i) })
    // Also match labels with content after colon
    lines.forEach((line, i) => { const m = line.match(/^[ \t]*([a-zA-Z_.@$][a-zA-Z0-9_.@$]*):/); if (m && !map.has(m[1].toLowerCase())) map.set(m[1].toLowerCase(), i) })
    return map
  }, [lines])

  const findMatches = useMemo(() => {
    if (!findOpen || !findText) return []
    const matches: { line: number; col: number; len: number }[] = []
    const search = findCaseSensitive ? findText : findText.toLowerCase()
    lines.forEach((line, i) => {
      const hay = findCaseSensitive ? line : line.toLowerCase()
      let idx = 0
      while ((idx = hay.indexOf(search, idx)) !== -1) { matches.push({ line: i, col: idx, len: findText.length }); idx += findText.length || 1 }
    })
    return matches
  }, [findOpen, findText, findCaseSensitive, lines])

  // Measure char width
  useEffect(() => {
    const pre = highlightRef.current; if (!pre) return
    const span = document.createElement('span')
    span.style.cssText = 'visibility:hidden;position:absolute;white-space:pre;font:inherit'
    span.textContent = 'MMMMMMMMMM'; pre.appendChild(span)
    const w = span.getBoundingClientRect().width / 10; pre.removeChild(span)
    if (w > 0) setCharW(w)
  }, [])

  const syncScroll = useCallback(() => {
    const ta = textareaRef.current; if (!ta) return
    const st = ta.scrollTop, sl = ta.scrollLeft
    setScrollTop(st); setScrollLeft(sl)
    if (lineNumsRef.current) lineNumsRef.current.scrollTop = st
    if (highlightLayerRef.current) highlightLayerRef.current.style.transform = `translate(${-sl}px, ${-st}px)`
  }, [])

  const updateCursorWord = useCallback(() => {
    const ta = textareaRef.current; if (!ta) return
    const pos = ta.selectionStart
    const bm = code.slice(0, pos).match(/([a-zA-Z_.@$][a-zA-Z0-9_.@$]*)$/)
    const am = code.slice(pos).match(/^([a-zA-Z0-9_.@$]*)/)
    const word = (bm ? bm[1] : '') + (am ? am[1] : '')
    setCursorWord(word.length >= 2 ? word.toLowerCase() : '')
  }, [code])

  const scopeHighlights = useMemo(() => {
    if (!cursorWord || cursorWord.length < 2) return []
    const matches: { line: number; col: number; len: number }[] = []
    lines.forEach((line, i) => {
      const lower = line.toLowerCase(); let idx = 0
      while ((idx = lower.indexOf(cursorWord, idx)) !== -1) {
        const before = idx > 0 ? lower[idx - 1] : ' '
        const after = idx + cursorWord.length < lower.length ? lower[idx + cursorWord.length] : ' '
        if (!/[a-zA-Z0-9_.]/.test(before) && !/[a-zA-Z0-9_.]/.test(after)) matches.push({ line: i, col: idx, len: cursorWord.length })
        idx += cursorWord.length || 1
      }
    })
    return matches.length > 1 ? matches : []
  }, [cursorWord, lines])

  // Highlight rendering
  const highlightedContent = useMemo(() => {
    const result: React.ReactNode[] = []
    lines.forEach((line, i) => {
      if (hiddenLines.has(i)) { if (i < lines.length - 1) result.push('\n'); return }
      const tokens = tokenizeLine(line)
      tokens.forEach((t, j) => {
        result.push(<span key={`${i}-${j}`} className={`anvil-tok-${t.type}`} data-token-type={t.type} data-token-text={t.text.toLowerCase()} data-line={i}>{t.text}</span>)
      })
      if (i < lines.length - 1) result.push('\n')
    })
    return result
  }, [lines, hiddenLines])

  // Autocomplete
  const getWordAtCursor = useCallback((): { word: string; start: number; end: number; line: number } | null => {
    const ta = textareaRef.current; if (!ta) return null
    const pos = ta.selectionStart
    const linesBefore = code.slice(0, pos).split('\n')
    const currentLine = linesBefore[linesBefore.length - 1]
    const match = currentLine.match(/([a-zA-Z_.%][a-zA-Z0-9_.%]*)$/)
    if (!match) return null
    return { word: match[1], start: pos - match[1].length, end: pos, line: linesBefore.length - 1 }
  }, [code])

  const updateAutocomplete = useCallback(() => {
    const info = getWordAtCursor()
    if (!info || info.word.length < 1) { setAcVisible(false); return }
    const prefix = info.word.toLowerCase()
    const filtered = COMPLETIONS.filter(c => c.label.toLowerCase().startsWith(prefix) && c.label.toLowerCase() !== prefix).slice(0, 12)
    if (filtered.length === 0) { setAcVisible(false); return }
    const ta = textareaRef.current, editor = editorRef.current; if (!ta || !editor) return
    const taRect = ta.getBoundingClientRect(), edRect = editor.getBoundingClientRect()
    const lb = code.slice(0, info.start).split('\n')
    const top = lb.length * 20 - ta.scrollTop + 8 + (taRect.top - edRect.top)
    const left = lb[lb.length - 1].length * charW + 10 - ta.scrollLeft + (taRect.left - edRect.left)
    setAcItems(filtered); setAcIndex(0); setAcPos({ top, left }); setAcPrefix(prefix); setAcVisible(true)
  }, [code, getWordAtCursor, charW])

  const applyCompletion = useCallback((item: CompletionItem) => {
    const info = getWordAtCursor(); if (!info) return
    pushUndo(code); onChange(code.slice(0, info.start) + item.insert + code.slice(info.end)); setAcVisible(false)
    requestAnimationFrame(() => { const ta = textareaRef.current; if (ta) { ta.selectionStart = ta.selectionEnd = info.start + item.insert.length; ta.focus() } })
  }, [code, getWordAtCursor, onChange, pushUndo])

  // Find & Replace
  const handleReplaceOne = useCallback(() => {
    if (!findText || findMatches.length === 0) return
    const m = findMatches[0], before = lines.slice(0, m.line).join('\n'), prefix = before ? before + '\n' : ''
    const currentLine = lines[m.line], newLine = currentLine.slice(0, m.col) + replaceText + currentLine.slice(m.col + m.len)
    const after = lines.slice(m.line + 1).join('\n')
    pushUndo(code); onChange(prefix + newLine + (lines.length > m.line + 1 ? '\n' + after : ''))
  }, [findText, replaceText, findMatches, lines, code, onChange, pushUndo])

  const handleReplaceAll = useCallback(() => {
    if (!findText) return
    const escaped = findText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    pushUndo(code); onChange(code.replace(new RegExp(escaped, findCaseSensitive ? 'g' : 'gi'), replaceText))
  }, [findText, replaceText, findCaseSensitive, code, onChange, pushUndo])

  // Keyboard
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); handleUndo(); return }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) { e.preventDefault(); handleRedo(); return }
    if ((e.ctrlKey || e.metaKey) && e.key === 'f') { e.preventDefault(); setFindOpen(v => !v); setTimeout(() => findInputRef.current?.focus(), 50); return }
    if ((e.ctrlKey || e.metaKey) && e.key === 'h') { e.preventDefault(); setFindOpen(true); setTimeout(() => findInputRef.current?.focus(), 50); return }
    if (acVisible) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setAcIndex(i => Math.min(i + 1, acItems.length - 1)); return }
      if (e.key === 'ArrowUp') { e.preventDefault(); setAcIndex(i => Math.max(i - 1, 0)); return }
      if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); applyCompletion(acItems[acIndex]); return }
      if (e.key === 'Escape') { e.preventDefault(); setAcVisible(false); return }
    }
    if (e.key === 'Escape' && findOpen) { setFindOpen(false); return }
    // Enter: auto-indent — preserve leading whitespace of current line
    if (e.key === 'Enter' && !acVisible) {
      e.preventDefault()
      const ta = e.currentTarget, start = ta.selectionStart, end = ta.selectionEnd
      const linesBefore = code.slice(0, start).split('\n')
      const currentLine = linesBefore[linesBefore.length - 1]
      const indent = currentLine.match(/^(\s*)/)?.[1] || ''
      // If line ends with ':', add extra indent (label block)
      const trimmed = code.slice(0, start).trimEnd()
      const extra = trimmed.endsWith(':') && !indent ? '    ' : ''
      const insert = '\n' + indent + extra
      pushUndo(code); onChange(code.slice(0, start) + insert + code.slice(end))
      const newPos = start + insert.length
      requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = newPos })
      return
    }
    // Auto-close brackets: [ inserts [] with cursor between
    if (e.key === '[') {
      e.preventDefault()
      const ta = e.currentTarget, start = ta.selectionStart, end = ta.selectionEnd
      pushUndo(code); onChange(code.slice(0, start) + '[]' + code.slice(end))
      const newPos = start + 1
      requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = newPos })
      return
    }
    // Skip over ] if already present at cursor
    if (e.key === ']') {
      const ta = e.currentTarget, pos = ta.selectionStart
      if (ta.selectionStart === ta.selectionEnd && code[pos] === ']') {
        e.preventDefault()
        const newPos = pos + 1
        requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = newPos })
        return
      }
    }
    // Backspace between [] deletes both
    if (e.key === 'Backspace' && !e.ctrlKey && !e.metaKey) {
      const ta = e.currentTarget, pos = ta.selectionStart
      if (pos > 0 && ta.selectionStart === ta.selectionEnd && code[pos - 1] === '[' && code[pos] === ']') {
        e.preventDefault()
        pushUndo(code); onChange(code.slice(0, pos - 1) + code.slice(pos + 1))
        const newPos = pos - 1
        requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = newPos })
        return
      }
    }
    if (e.key === 'Tab' && !acVisible) {
      e.preventDefault(); const ta = e.currentTarget, start = ta.selectionStart, end = ta.selectionEnd
      pushUndo(code); onChange(code.slice(0, start) + '    ' + code.slice(end))
      requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = start + 4 })
    }
  }, [acVisible, acItems, acIndex, applyCompletion, code, onChange, findOpen, pushUndo, handleUndo, handleRedo])

  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => { setTooltip(null); handleChange(e.target.value) }, [handleChange])

  // Ctrl+click label jump
  const handleEditorClick = useCallback((e: React.MouseEvent<HTMLPreElement>) => {
    if (!e.ctrlKey && !e.metaKey) return
    const target = e.target as HTMLElement
    const tokenText = target.dataset.tokenText
    if (tokenText) {
      const lineIdx = labelPositions.get(tokenText)
      if (lineIdx !== undefined) {
        e.preventDefault(); const ta = textareaRef.current; if (!ta) return
        let pos = 0; for (let i = 0; i < lineIdx; i++) pos += lines[i].length + 1
        ta.selectionStart = ta.selectionEnd = pos; ta.focus()
        ta.scrollTop = lineIdx * 20 - ta.clientHeight / 2; syncScroll()
      }
    }
  }, [labelPositions, lines, syncScroll])

  useEffect(() => {
    const ta = textareaRef.current
    if (ta && document.activeElement === ta) { const t = setTimeout(() => { updateAutocomplete(); updateCursorWord() }, 30); return () => clearTimeout(t) }
  }, [code, updateAutocomplete, updateCursorWord])

  useEffect(() => {
    if (!acVisible || !acRef.current || !editorRef.current) return
    const popup = acRef.current, edRect = editorRef.current.getBoundingClientRect(), popRect = popup.getBoundingClientRect()
    if (popRect.bottom > edRect.bottom) popup.style.top = `${acPos.top - popRect.height - 20}px`
    if (popRect.right > edRect.right) popup.style.left = `${Math.max(0, edRect.right - edRect.left - popRect.width - 4)}px`
  }, [acVisible, acPos])

  useEffect(() => {
    if (!tooltip || !tooltipRef.current || !editorRef.current) return
    const tipRect = tooltipRef.current.getBoundingClientRect(), edRect = editorRef.current.getBoundingClientRect()
    if (tipRect.bottom > edRect.bottom) tooltipRef.current.style.top = `${tooltip.y - tipRect.height - 8}px`
  }, [tooltip])

  useEffect(() => {
    const ta = textareaRef.current; if (!ta) return
    const handler = () => updateCursorWord()
    ta.addEventListener('click', handler); ta.addEventListener('keyup', handler)
    return () => { ta.removeEventListener('click', handler); ta.removeEventListener('keyup', handler) }
  }, [updateCursorWord])

  // Hover tooltip
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLPreElement>) => {
    const target = e.target as HTMLElement
    const lineStr = target.dataset.line, lineIdx = lineStr !== undefined ? parseInt(lineStr) : -1
    if (target.dataset.tokenType === 'keyword') {
      const word = target.dataset.tokenText
      if (word) { const info = INSTR_INFO.get(word); if (info) { const rect = target.getBoundingClientRect(), editorRect = editorRef.current?.getBoundingClientRect(); if (editorRect) { setTooltip({ text: info.desc, syntax: info.syntax, cat: info.cat, x: rect.left - editorRect.left, y: rect.bottom - editorRect.top + 4 }); return } } }
    }
    if (lineIdx >= 0) {
      const errs = lintErrors.filter(e => e.line === lineIdx)
      if (errs.length > 0) { const rect = target.getBoundingClientRect(), editorRect = editorRef.current?.getBoundingClientRect(); if (editorRect) { setTooltip({ text: errs[0].msg, syntax: errs[0].severity === 'error' ? 'Error' : 'Warning', cat: 'LINT', x: rect.left - editorRect.left, y: rect.bottom - editorRect.top + 4 }); return } }
    }
    setTooltip(null)
  }, [lintErrors])

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  useLayoutEffect(() => {
    const ta = textareaRef.current; if (!ta || activeLine <= 0) return
    const targetTop = (activeLine - 1) * 20
    if (targetTop < ta.scrollTop || targetTop + 20 > ta.scrollTop + ta.clientHeight) { ta.scrollTop = Math.max(0, targetTop - ta.clientHeight / 2); syncScroll() }
  }, [activeLine, syncScroll])

  // Decorations
  const errorUnderlines = useMemo(() => lintErrors.map((err, i) => (
    <div key={`err-${i}`} className={`anvil-ed-error-underline ${err.severity}`} style={{ top: `${err.line * 20 + 8 + 16}px`, left: `${err.col * charW + 10}px`, width: `${Math.max(err.len, 1) * charW}px` }} />
  )), [lintErrors, charW])

  const scopeDivs = useMemo(() => scopeHighlights.map((m, i) => (
    <div key={`scope-${i}`} className="anvil-ed-scope-highlight" style={{ top: `${m.line * 20 + 8}px`, left: `${m.col * charW + 10}px`, width: `${m.len * charW}px` }} />
  )), [scopeHighlights, charW])

  const findDivs = useMemo(() => findMatches.map((m, i) => (
    <div key={`find-${i}`} className="anvil-ed-find-highlight" style={{ top: `${m.line * 20 + 8}px`, left: `${m.col * charW + 10}px`, width: `${m.len * charW}px` }} />
  )), [findMatches, charW])

  // Jump arrows
  const jumpArrows = useMemo(() => {
    const raw: { from: number; to: number }[] = []
    lines.forEach((line, i) => {
      const m = line.match(/^\s*(jmp|je|jz|jne|jnz|jl|jle|jg|jge|jb|ja|jnge|jng|jnle|jnl|jnae|jnbe|js|jo|loop|call)\s+([a-zA-Z_.@$][a-zA-Z0-9_.@$]*)/i)
      if (m) { const target = labelPositions.get(m[2].toLowerCase()); if (target !== undefined && target !== i) raw.push({ from: i, to: target }) }
    })
    const sorted = raw.map(a => ({ ...a, minL: Math.min(a.from, a.to), maxL: Math.max(a.from, a.to) })).sort((a, b) => (a.maxL - a.minL) - (b.maxL - b.minL))
    const assigned: { minL: number; maxL: number; level: number }[] = []
    return sorted.map(a => {
      let level = 0
      const overlapping = assigned.filter(b => !(a.maxL < b.minL || a.minL > b.maxL))
      const usedLevels = new Set(overlapping.map(b => b.level))
      while (usedLevels.has(level)) level++
      assigned.push({ minL: a.minL, maxL: a.maxL, level })
      return { from: a.from, to: a.to, level }
    })
  }, [lines, labelPositions])

  const maxArrowLevel = jumpArrows.reduce((m, a) => Math.max(m, a.level), -1)
  const arrowGutterW = Math.max(30, 20 + (maxArrowLevel + 1) * 5)
  const errCount = lintErrors.filter(e => e.severity === 'error').length
  const warnCount = lintErrors.filter(e => e.severity === 'warning').length

  return (
    <div className="anvil-editor-pro" ref={editorRef}>
      {/* Find & Replace */}
      {findOpen && (
        <div className="anvil-ed-find-bar">
          <div className="anvil-ed-find-row">
            <input ref={findInputRef} className="anvil-ed-find-input" value={findText} onChange={e => setFindText(e.target.value)} placeholder="Find..." onKeyDown={e => { if (e.key === 'Escape') setFindOpen(false) }} />
            <button className={`anvil-ed-find-btn ${findCaseSensitive ? 'active' : ''}`} onClick={() => setFindCaseSensitive(v => !v)} title="Case sensitive">Aa</button>
            <span className="anvil-ed-find-count">{findMatches.length > 0 ? `${findMatches.length} found` : findText ? 'No results' : ''}</span>
          </div>
          <div className="anvil-ed-find-row">
            <input className="anvil-ed-find-input" value={replaceText} onChange={e => setReplaceText(e.target.value)} placeholder="Replace..." onKeyDown={e => { if (e.key === 'Escape') setFindOpen(false) }} />
            <button className="anvil-ed-find-btn" onClick={handleReplaceOne} title="Replace next">1</button>
            <button className="anvil-ed-find-btn" onClick={handleReplaceAll} title="Replace all">All</button>
          </div>
          <button className="anvil-ed-find-close" onClick={() => setFindOpen(false)}><i className="fa-solid fa-xmark" /></button>
        </div>
      )}

      {/* Editor body */}
      <div className="anvil-ed-body">
        {/* Line numbers */}
        <div className="anvil-ed-linenums" ref={lineNumsRef} style={{ paddingLeft: arrowGutterW }}>
          {lines.map((_, i) => {
            if (hiddenLines.has(i)) return <div key={i} className="anvil-ed-linenum hidden" />
            const lineNum = i + 1, isActive = lineNum === activeLine
            const hasError = lintErrors.some(e => e.line === i && e.severity === 'error')
            const hasWarning = !hasError && lintErrors.some(e => e.line === i && e.severity === 'warning')
            const foldRegion = foldRegions.find(r => r.start === i)
            const isFolded = foldedLines.has(i)
            const hasBp = breakpoints?.has(lineNum)
            return (
              <div key={i} className={`anvil-ed-linenum ${isActive ? 'active' : ''} ${hasError ? 'has-error' : ''} ${hasWarning ? 'has-warning' : ''} ${hasBp ? 'has-bp' : ''}`}>
                {foldRegion ? (
                  <span className={`anvil-ed-fold-toggle ${isFolded ? 'folded' : ''}`} onClick={() => toggleFold(i)}>{isFolded ? '+' : '-'}</span>
                ) : <span className="anvil-ed-fold-spacer" />}
                <span className="anvil-ed-linenum-n" onClick={() => onToggleBreakpoint?.(lineNum)} style={{ cursor: 'pointer' }}>
                  {hasBp && <span className="anvil-ed-bp-dot" />}
                  {lineNum}
                </span>
                {isActive && <span className="anvil-ed-rip"><i className="fa-solid fa-chevron-right" /></span>}
              </div>
            )
          })}
          <svg className="anvil-ed-jump-arrows" style={{ height: lines.length * 20 + 16, width: arrowGutterW }}>
            {jumpArrows.map((a, i) => {
              const fromY = a.from * 20 + 18, toY = a.to * 20 + 18, isCurrentJump = a.from === activeLine - 1
              const svgW = arrowGutterW, x0 = svgW - 4, xIndent = Math.max(3, svgW - 10 - a.level * 5)
              const col = isCurrentJump ? '#4a9eff' : 'rgba(255,255,255,0.1)', sw = isCurrentJump ? 1.5 : 1
              return (
                <g key={i}>
                  <path d={`M ${x0} ${fromY} H ${xIndent} V ${toY} H ${x0}`} fill="none" stroke={col} strokeWidth={sw} />
                  <polygon points={`${x0},${toY - 3} ${x0},${toY + 3} ${svgW},${toY}`} fill={col} />
                </g>
              )
            })}
          </svg>
        </div>

        {/* Editor content */}
        <div className="anvil-ed-content">
          <div className="anvil-ed-highlight-layer" ref={highlightLayerRef} style={{ transform: `translate(${-scrollLeft}px, ${-scrollTop}px)` }}>
            {activeLine > 0 && <div className="anvil-ed-active-line" style={{ top: `${(activeLine - 1) * 20 + 8}px` }} />}
            {(errorLine ?? 0) > 0 && <div className="anvil-ed-error-line" style={{ top: `${(errorLine! - 1) * 20 + 8}px` }} />}
            {scopeDivs}
            {findDivs}
            {errorUnderlines}
            <pre className="anvil-ed-highlight" ref={highlightRef} aria-hidden="true" onMouseMove={handleMouseMove} onMouseLeave={handleMouseLeave} onClick={handleEditorClick}>
              <code>{highlightedContent}</code>
            </pre>
          </div>
          <textarea ref={textareaRef} className="anvil-ed-textarea" value={code} onChange={handleInput} onKeyDown={handleKeyDown} onScroll={syncScroll} onBlur={() => setTimeout(() => setAcVisible(false), 150)} spellCheck={false} autoComplete="off" autoCorrect="off" autoCapitalize="off" />
        </div>
      </div>

      {/* Autocomplete */}
      {acVisible && acItems.length > 0 && (
        <div className="anvil-ac-popup" ref={acRef} style={{ top: acPos.top, left: acPos.left }}>
          <div className="anvil-ac-list">
            {acItems.map((item, i) => (
              <div key={item.label + item.kind} className={`anvil-ac-item ${i === acIndex ? 'active' : ''}`} onMouseDown={e => { e.preventDefault(); applyCompletion(item) }} onMouseEnter={() => setAcIndex(i)}>
                <span className={`anvil-ac-icon ${kindClass(item.kind)}`}>{kindIcon(item.kind)}</span>
                <span className="anvil-ac-label"><span className="anvil-ac-match">{item.label.slice(0, acPrefix.length)}</span>{item.label.slice(acPrefix.length)}</span>
              </div>
            ))}
          </div>
          {acItems[acIndex] && (
            <div className="anvil-ac-detail">
              <div className="anvil-ac-detail-title">{acItems[acIndex].label}</div>
              <div className="anvil-ac-detail-desc">{acItems[acIndex].detail}</div>
            </div>
          )}
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div className="anvil-ed-tooltip" ref={tooltipRef} style={{ top: tooltip.y, left: tooltip.x }}>
          <div className="anvil-ed-tooltip-cat">{tooltip.cat}</div>
          <div className="anvil-ed-tooltip-syntax">{tooltip.syntax}</div>
          <div className="anvil-ed-tooltip-desc">{tooltip.text}</div>
        </div>
      )}

      {/* Status bar */}
      {(errCount > 0 || warnCount > 0) && (
        <div className="anvil-ed-status-bar">
          {errCount > 0 && <span className="anvil-ed-status-item err"><i className="fa-solid fa-circle-xmark" /> {errCount} error{errCount > 1 ? 's' : ''}</span>}
          {warnCount > 0 && <span className="anvil-ed-status-item warn"><i className="fa-solid fa-triangle-exclamation" /> {warnCount} warning{warnCount > 1 ? 's' : ''}</span>}
        </div>
      )}
    </div>
  )
}
