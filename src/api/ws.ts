/**
 * WebSocket client — connects to backend WS endpoint and dispatches typed messages.
 * Handles reconnection, heartbeat, and message routing.
 */

const WS_BASE = window.__TAURI__ ? 'ws://127.0.0.1:8000' : `ws://${location.host}`

export type WSMessageType = 'command' | 'subscribe' | 'unsubscribe' | 'ping' | 'result' | 'event' | 'error' | 'pong'

export interface WSMessage {
  type: WSMessageType
  session_id?: string
  request_id: string
  payload: Record<string, unknown>
}

type MessageHandler = (msg: WSMessage) => void

export class AnvilWS {
  private ws: WebSocket | null = null
  private handlers = new Map<string, Set<MessageHandler>>()
  private globalHandlers = new Set<MessageHandler>()
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private _sessionType: string
  private _sessionId: string
  private _connected = false

  constructor(sessionType: string, sessionId: string) {
    this._sessionType = sessionType
    this._sessionId = sessionId
  }

  get connected() { return this._connected }

  connect(): void {
    if (this.ws) return
    const url = `${WS_BASE}/ws/${this._sessionType}/${this._sessionId}`
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this._connected = true
      this.startHeartbeat()
    }

    this.ws.onmessage = (ev) => {
      try {
        const msg: WSMessage = JSON.parse(ev.data)
        // Route to command-specific handlers
        const cmd = msg.payload?.command as string | undefined
        if (cmd) {
          const set = this.handlers.get(cmd)
          if (set) set.forEach(h => h(msg))
        }
        // Route to type-specific handlers
        const typeSet = this.handlers.get(msg.type)
        if (typeSet) typeSet.forEach(h => h(msg))
        // Global handlers
        this.globalHandlers.forEach(h => h(msg))
      } catch { /* ignore parse errors */ }
    }

    this.ws.onclose = () => {
      this._connected = false
      this.stopHeartbeat()
      this.ws = null
      // Auto-reconnect after 2s
      this.reconnectTimer = setTimeout(() => this.connect(), 2000)
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
    this.ws?.close()
    this.ws = null
    this._connected = false
  }

  /** Send a command to the backend */
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
    }, 30_000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}
