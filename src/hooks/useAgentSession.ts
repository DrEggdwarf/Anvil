/* Anvil Agent — chat session hook (ADR-023). */

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  agentChatStream,
  agentDeleteSession,
  agentGetSession,
  agentListSessions,
  type AgentChatBody,
  type AgentChunk,
  type AgentMessage,
  type AgentSessionFull,
  type AgentSessionSummary,
  type AgentToolCall,
} from '../api/client'

export type ChatPhase = 'idle' | 'streaming' | 'error'

export interface UIMessage {
  id: string
  role: 'user' | 'assistant' | 'tool'
  content: string
  toolCalls?: AgentToolCall[]
  toolCallId?: string
  pending?: boolean
}

let _localId = 0
const nextId = () => `m${++_localId}`

export function useAgentSession() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<UIMessage[]>([])
  const [phase, setPhase] = useState<ChatPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [recent, setRecent] = useState<AgentSessionSummary[]>([])
  const abortRef = useRef<AbortController | null>(null)

  const loadRecent = useCallback(async () => {
    try {
      const r = await agentListSessions()
      setRecent(r.sessions)
    } catch {
      /* ignore */
    }
  }, [])

  useEffect(() => {
    loadRecent()
  }, [loadRecent])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setSessionId(null)
    setMessages([])
    setPhase('idle')
    setError(null)
  }, [])

  const loadSession = useCallback(async (id: string) => {
    abortRef.current?.abort()
    setError(null)
    const full: AgentSessionFull = await agentGetSession(id)
    setSessionId(full.id)
    setMessages(
      full.messages
        .filter(m => m.role !== 'system')
        .map(m => fromBackendMessage(m)),
    )
    setPhase('idle')
  }, [])

  const removeSession = useCallback(async (id: string) => {
    await agentDeleteSession(id)
    if (sessionId === id) reset()
    await loadRecent()
  }, [sessionId, reset, loadRecent])

  const send = useCallback(async (
    userText: string,
    opts: { module: string; chips: string[]; anvilSessionIds?: Record<string, string>; allowWriteExec?: boolean },
  ) => {
    if (!userText.trim() || phase === 'streaming') return
    setError(null)
    const userMsg: UIMessage = { id: nextId(), role: 'user', content: userText }
    const assistantMsg: UIMessage = { id: nextId(), role: 'assistant', content: '', pending: true }
    setMessages(prev => [...prev, userMsg, assistantMsg])
    setPhase('streaming')

    const body: AgentChatBody = {
      session_id: sessionId,
      module: opts.module,
      chips: opts.chips,
      message: userText,
      anvil_session_ids: opts.anvilSessionIds || {},
      allow_write_exec: opts.allowWriteExec ?? null,
    }

    const ctrl = new AbortController()
    abortRef.current = ctrl
    try {
      for await (const chunk of agentChatStream(body, ctrl.signal)) {
        applyChunk(chunk, assistantMsg.id, setMessages, sid => setSessionId(sid))
      }
      setPhase('idle')
      await loadRecent()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      if (msg.includes('aborted')) {
        setPhase('idle')
      } else {
        setError(msg)
        setPhase('error')
      }
    } finally {
      abortRef.current = null
      setMessages(prev =>
        prev.map(m => (m.id === assistantMsg.id ? { ...m, pending: false } : m)),
      )
    }
  }, [phase, sessionId, loadRecent])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return {
    sessionId,
    messages,
    phase,
    error,
    recent,
    send,
    cancel,
    reset,
    loadSession,
    removeSession,
    refreshRecent: loadRecent,
  }
}

function fromBackendMessage(m: AgentMessage): UIMessage {
  return {
    id: nextId(),
    role: m.role === 'system' ? 'assistant' : m.role,
    content: m.content,
    toolCalls: m.tool_calls,
    toolCallId: m.tool_call_id ?? undefined,
  }
}

function applyChunk(
  chunk: AgentChunk,
  assistantId: string,
  setMessages: React.Dispatch<React.SetStateAction<UIMessage[]>>,
  setSessionId: (id: string) => void,
) {
  switch (chunk.type) {
    case 'session':
      if (typeof chunk.data.session_id === 'string') setSessionId(chunk.data.session_id)
      return
    case 'delta':
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId ? { ...m, content: m.content + (chunk.data.text ?? '') } : m,
        ),
      )
      return
    case 'tool_call': {
      const tc: AgentToolCall = {
        id: String(chunk.data.id),
        name: String(chunk.data.name),
        arguments: (chunk.data.arguments as Record<string, unknown>) || {},
        destructive: !!chunk.data.destructive,
      }
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, toolCalls: [...(m.toolCalls || []), tc] }
            : m,
        ),
      )
      return
    }
    case 'tool_result': {
      const id = String(chunk.data.id)
      setMessages(prev =>
        prev.map(m => {
          if (m.id !== assistantId) return m
          const calls = (m.toolCalls || []).map(tc =>
            tc.id === id
              ? {
                ...tc,
                result: chunk.data.result,
                error: (chunk.data.error as string) || null,
                duration_ms: (chunk.data.duration_ms as number) ?? null,
              }
              : tc,
          )
          return { ...m, toolCalls: calls }
        }),
      )
      return
    }
    case 'error':
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? {
              ...m,
              content:
                  (m.content || '') +
                  `\n\n⚠ ${chunk.data.code || 'ERROR'}: ${chunk.data.message || ''}`,
            }
            : m,
        ),
      )
      return
    case 'done':
      return
  }
}
