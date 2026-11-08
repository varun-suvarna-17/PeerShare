import { wsBaseUrl } from '../api/client'
import type { WsEvent } from '../types/events'

type EventHandler = (event: WsEvent) => void
type StatusHandler = (status: 'connecting' | 'open' | 'closed' | 'error') => void

export class GlobalEventSocket {
  private socket: WebSocket | null = null
  private lastEventSeq = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private intentionalClose = false
  private handlers = new Set<EventHandler>()
  private statusHandlers = new Set<StatusHandler>()
  private reconnectAttempts = 0

  connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.intentionalClose = false
    this.emitStatus('connecting')

    const socket = new WebSocket(`${wsBaseUrl()}/ws/events`)
    this.socket = socket

    socket.onopen = () => {
      this.reconnectAttempts = 0
      this.emitStatus('open')
      if (this.lastEventSeq > 0) {
        socket.send(JSON.stringify({ type: 'replay', last_event_seq: this.lastEventSeq }))
      }
    }

    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data as string) as WsEvent
        if (typeof event.event_seq === 'number') {
          this.lastEventSeq = Math.max(this.lastEventSeq, event.event_seq)
        }
        this.handlers.forEach((handler) => handler(event))
      } catch {
        // Ignore malformed payloads
      }
    }

    socket.onerror = () => {
      this.emitStatus('error')
    }

    socket.onclose = () => {
      this.emitStatus('closed')
      this.socket = null
      if (!this.intentionalClose) this.scheduleReconnect()
    }
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
    }
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler)
    return () => {
      this.statusHandlers.delete(handler)
    }
  }

  disconnect(): void {
    this.intentionalClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.socket?.close()
    this.socket = null
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000)
    this.reconnectAttempts += 1
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }

  private emitStatus(status: 'connecting' | 'open' | 'closed' | 'error'): void {
    this.statusHandlers.forEach((handler) => handler(status))
  }
}

export const globalEventSocket = new GlobalEventSocket()
