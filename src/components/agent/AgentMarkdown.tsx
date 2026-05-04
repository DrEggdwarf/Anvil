/* Markdown-ish renderer — light-weight (no heavy deps). Handles paragraphs,
   inline code, fenced code blocks. ADR-023. */

import { Fragment } from 'react'

interface Props {
  text: string
}

export function AgentMarkdown({ text }: Props) {
  if (!text) return null
  const blocks = text.split(/```/)
  return (
    <div className="anvil-agent-md">
      {blocks.map((block, i) =>
        i % 2 === 1 ? (
          <pre key={i} className="anvil-agent-md-code">
            {stripLang(block)}
          </pre>
        ) : (
          <Fragment key={i}>{renderInline(block)}</Fragment>
        ),
      )}
    </div>
  )
}

function stripLang(block: string): string {
  // Drop optional language hint on first line.
  const nl = block.indexOf('\n')
  if (nl < 0) return block
  const first = block.slice(0, nl).trim()
  if (/^[a-zA-Z0-9_+-]{1,20}$/.test(first)) return block.slice(nl + 1)
  return block
}

function renderInline(block: string) {
  const paragraphs = block.split(/\n{2,}/)
  return paragraphs.map((p, i) => (
    <p key={i} className="anvil-agent-md-p">
      {renderCodeAndText(p)}
    </p>
  ))
}

function renderCodeAndText(text: string) {
  const parts = text.split(/(`[^`]+`)/g)
  return parts.map((part, i) =>
    part.startsWith('`') && part.endsWith('`') ? (
      <code key={i} className="anvil-agent-md-inline-code">
        {part.slice(1, -1)}
      </code>
    ) : (
      <Fragment key={i}>
        {part.split('\n').map((line, j, arr) => (
          <Fragment key={j}>
            {line}
            {j < arr.length - 1 && <br />}
          </Fragment>
        ))}
      </Fragment>
    ),
  )
}
