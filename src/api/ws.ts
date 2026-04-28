/**
 * WebSocket client — connects to backend WS endpoint and dispatches typed messages.
 * Handles reconnection, heartbeat, request/response correlation, and routing.
 *
 * Sprint 17-F groundwork: ADR-016 token plumbing + Promise-based request() so
 * useAnvilSession (or any future hook) can switch from REST to WS for stepping
 * without rewriting its call sites. Final integration into useAnvilSession is
 * deferred to a sprint with e2e harness.
 */

import { WS_HEARTBEAT_MS, WS_RECONNECT_MS } from '../config'

const WS_BASE = window.__TAURI__ ? 'ws://127.0.0.1:8000' : `ws://${location.host}`

// How long a request() awaits a matching result before rejecting.
// 30s covers the slowest GDB step (e.g. record-replay rewind on a long history).
const WS_REQUEST_TIMEOUT_MS = 30_000

export type WSMessageType = 'command' | 'subscribe' | 'unsubscribe' | 'ping' | 'result' | 'event' | 'error' | 'pong'

export interface WSMessage {
  type: WSMessageType
  session_id?: string
  request_id: string
  payload: Record<string, unknown>
}

type MessageHandler = (msg: WSMessage) => void

interface PendingRequest {
  resolve: (msg: WSMessage) => void
  reject: (err: Error) => void
  timer: ReturnType<typeof setTimeout>
}

export class AnvilWS {
  private ws: WebSocket | null = null
  private handlers = new Map<string, Set<MessageHandler>>()
  private globalHandlers = new Set<MessageHandler>()
  private pending = new Map<string, PendingRequest>()
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _sessionType: string
  private _sessionId: string
  // ADR-016: required to open the WS — server rejects with HTTP 403 otherwise.
  private _token: string
  private _connected = false

  constructor(sessionType: string, sessionId: string, token: string) {
    this._sessionType = sessionType
    this._sessionId = sessionId
    this._token = token
  }

  get connected() { return this._connected }

  connect(): void {
    if (this.ws) return
    const url = `${WS_BASE}/ws/${this._sessionType}/${this._sessionId}?token=${encodeURIComponent(this._token)}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this._connected = true
      this.startHeartbeat()
    }

    this.ws.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data)

        // 1. Resolve a pending request() awaiting this exact request_id.
        const pending = this.pending.get(msg.request_id)
        if (pending) {
          this.pending.delete(msg.request_id)
          clearTimeout(pending.timer)
          if (msg.type === 'error') {
            pending.reject(new Error(String(msg.payload?.message ?? msg.payload?.code ?? 'WS error')))
          } else {
            pending.resolve(msg)
          }
        }

        // 2. Fan out to subscribers (both command-name and message-type).
        const cmd = msg.payload?.command as string | undefined
        if (cmd) {
          const set = this.handlers.get(cmd)
          if (set) set.forEach(h => h(msg))
        }
        const typeSet = this.handlers.get(msg.type)
        if (typeSet) typeSet.forEach(h => h(msg))
        this.globalHandlers.forEach(h => h(msg))
      } catch { /* ignore parse errors */ }
    }

    this.ws.onclose = () => {
      this._connected = false
      this.stopHeartbeat()
      this.ws = null
      this.reconnectTimer = setTimeout(() => this.connect(), WS_RECONNECT_MS)
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.stopHeartbeat()
    // Reject every pending request so callers don't wait forever after a manual close.
    for (const [, pending] of this.pending) {
      clearTimeout(pending.timer)
      pending.reject(new Error('WS disconnected'))
    }
    this.pending.clear()
    this.ws?.close()
    this.ws = null
    this._connected = false
  }

  /** Send a command without awaiting a response. Returns the request_id for manual correlation. */
  send(command: string, args: Record<string, unknown> = {}): string {
    const requestId = crypto.randomUUID().replace(/-/g, '')
    const msg: WSMessage = {
      type: 'command',
      session_id: this._sessionId,
      request_id: requestId,
      payload: { command, ...args },
    }
    this.ws?.send(JSON.stringify(msg))
    return requestId
  }

  /** Send a command and resolve with the matching `result` (or reject on `error` / timeout).
   *
   *  Drop-in replacement for the equivalent REST endpoint, e.g.
   *    `await ws.request('step_into')`  ↔  `await api.gdbStepInto(sid)`
   *  The backend handler returns a result message correlated by `request_id`.
   */
  request(command: string, args: Record<string, unknown> = {}): Promise<WSMessage> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error('WS not connected'))
    }
    return new Promise<WSMessage>((resolve, reject) => {
      const requestId = crypto.randomUUID().replace(/-/g, '')
      const timer = setTimeout(() => {
        this.pending.delete(requestId)
        reject(new Error(`WS request timed out: ${command}`))
      }, WS_REQUEST_TIMEOUT_MS)
      this.pending.set(requestId, { resolve, reject, timer })
      const msg: WSMessage = {
        type: 'command',
        session_id: this._sessionId,
        request_id: requestId,
        payload: { command, ...args },
      }
      this.ws!.send(JSON.stringify(msg))
    })
  }

  /** Listen to messages matching a command name or message type */
  on(key: string, handler: MessageHandler): () => void {
    let set = this.handlers.get(key)
    if (!set) {
      set = new Set()
      this.handlers.set(key, set)
    }
    set.add(handler)
    return () => { set!.delete(handler) }
  }

  /** Listen to all messages */
  onAny(handler: MessageHandler): () => void {
    this.globalHandlers.add(handler)
    return () => { this.globalHandlers.delete(handler) }
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({
          type: 'ping',
          request_id: crypto.randomUUID().replace(/-/g, ''),
          payload: {},
        }))
      }
    }, WS_HEARTBEAT_MS)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}
