import AsmEditor from './editor/AsmEditor'

interface Props {
  code: string
  onChange: (code: string) => void
  activeLine: number
  errorLine: number
  breakpoints: Set<number>
  onToggleBreakpoint: (line: number) => void
}

export function EditorPanel({ code, onChange, activeLine, errorLine, breakpoints, onToggleBreakpoint }: Props) {
  return (
    <div className="anvil-editor-area">
      <AsmEditor
        code={code}
        onChange={onChange}
        activeLine={activeLine}
        errorLine={errorLine}
        breakpoints={breakpoints}
        onToggleBreakpoint={onToggleBreakpoint}
      />
    </div>
  )
}
