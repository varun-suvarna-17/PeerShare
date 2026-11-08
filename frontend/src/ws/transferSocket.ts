import { wsBaseUrl } from '../api/client'
import type { WsEvent } from '../types/events'

type EventHandler = (event: WsEvent) => void

export class TransferEventSocket {
  private socket: WebSocket | null = null
  private lastEventSeq = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private intentionalClose = false
  private transferId: string | null = null
  private handlers = new Set<EventHandler>()
  private reconnectAttempts = 0

  connect(transferId: string): void {
    if (this.transferId === transferId && this.socket?.readyState === WebSocket.OPEN) return

    this.disconnect()
    this.intentionalClose = false
    this.transferId = transferId

    const socket = new WebSocket(`${wsBaseUrl()}/ws/transfers/${transferId}`)
    this.socket = socket

    socket.onopen = () => {
      this.reconnectAttempts = 0
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

    socket.onclose = () => {
      this.socket = null
      if (!this.intentionalClose && this.transferId) this.scheduleReconnect()
    }
  }

  subscribe(handler: EventHandler): () => void {
    this.handlers.add(handler)
    return () => {
      this.handlers.delete(handler)
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
    this.transferId = null
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer || !this.transferId) return
    const id = this.transferId
    const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 15000)
    this.reconnectAttempts += 1
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect(id)
    }, delay)
  }
}

export const transferEventSocket = new TransferEventSocket()
