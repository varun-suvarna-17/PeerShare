import { create } from 'zustand'
import { DEFAULT_CONFIG } from '../constants/protocols'
import type {
  PendingTransfer,
  ProtocolId,
  TransferConfig,
  TransferDetails,
  TransferReport,
} from '../types/api'
import type { FlyingPacket, NetworkMetrics, TransferProgressData, WsEvent } from '../types/events'

const emptyMetrics = (): NetworkMetrics => ({
  framesSent: 0,
  framesReceived: 0,
  acksSent: 0,
  acksReceived: 0,
  framesLost: 0,
  acksLost: 0,
  framesCorrupted: 0,
  timeouts: 0,
  retransmissions: 0,
  framesBuffered: 0,
  framesDiscarded: 0,
  windowBase: 0,
  windowSize: 4,
  frameStatuses: {},
  flyingPackets: [],
  recentTimeouts: [],
  lastWindowUpdate: null,
  lastEventAt: null,
})

interface TransferState {
  protocol: ProtocolId
  config: TransferConfig
  activeTransferId: string | null
  transfer: TransferDetails | null
  pendingTransfers: PendingTransfer[]
  progress: TransferProgressData
  metrics: NetworkMetrics
  report: TransferReport | null
  recentEvents: WsEvent[]
  statusMessage: string | null
  error: string | null
  startedAt: number | null
  setProtocol: (protocol: ProtocolId) => void
  setConfig: (config: Partial<TransferConfig>) => void
  setActiveTransferId: (id: string | null) => void
  setTransfer: (transfer: TransferDetails | null) => void
  setPendingTransfers: (transfers: PendingTransfer[]) => void
  setProgress: (progress: Partial<TransferProgressData>) => void
  setReport: (report: TransferReport | null) => void
  setStatusMessage: (message: string | null) => void
  setError: (error: string | null) => void
  markStarted: () => void
  applyEvent: (event: WsEvent) => void
  cleanExpiredPackets: () => void
  resetTransferRuntime: () => void
  resetAll: () => void
}

export const useTransferStore = create<TransferState>((set, get) => ({
  protocol: 'selective_repeat',
  config: { ...DEFAULT_CONFIG },
  activeTransferId: null,
  transfer: null,
  pendingTransfers: [],
  progress: {},
  metrics: emptyMetrics(),
  report: null,
  recentEvents: [],
  statusMessage: null,
  error: null,
  startedAt: null,
  setProtocol: (protocol) =>
    set((state) => ({
      protocol,
      metrics: {
        ...state.metrics,
        windowSize: protocol === 'stop_and_wait' ? 1 : state.config.window_size || 4,
      },
    })),
  setConfig: (config) =>
    set((state) => {
      const nextConfig = { ...state.config, ...config }
      return {
        config: nextConfig,
        metrics: {
          ...state.metrics,
          windowSize:
            state.protocol === 'stop_and_wait'
              ? 1
              : nextConfig.window_size || state.metrics.windowSize,
        },
      }
    }),
  setActiveTransferId: (activeTransferId) => set({ activeTransferId }),
  setTransfer: (transfer) => set({ transfer }),
  setPendingTransfers: (pendingTransfers) => set({ pendingTransfers }),
  setProgress: (progress) => set((state) => ({ progress: { ...state.progress, ...progress } })),
  setReport: (report) => set({ report }),
  setStatusMessage: (statusMessage) => set({ statusMessage }),
  setError: (error) => set({ error }),
  markStarted: () => set({ startedAt: Date.now() }),

  cleanExpiredPackets: () => {
    const now = Date.now()
    const current = get().metrics.flyingPackets
    const filtered = current.filter((p) => now - p.timestamp < 3000)
    if (filtered.length !== current.length) {
      set((state) => ({
        metrics: { ...state.metrics, flyingPackets: filtered },
      }))
    }
  },

  applyEvent: (event) => {
    const now = Date.now()
    const state = get()
    const metrics: NetworkMetrics = {
      ...state.metrics,
      lastEventAt: event.timestamp,
      frameStatuses: { ...state.metrics.frameStatuses },
      flyingPackets: state.metrics.flyingPackets.filter((p) => now - p.timestamp < 3500),
      recentTimeouts: state.metrics.recentTimeouts.filter((t) => now - t.timestamp < 4000),
    }
    const recentEvents = [event, ...state.recentEvents].slice(0, 100)
    const data = (event.data || {}) as Record<string, unknown>

    const addPacket = (packet: Omit<FlyingPacket, 'id' | 'timestamp'>) => {
      const newPacket: FlyingPacket = {
        ...packet,
        id: crypto.randomUUID(),
        timestamp: now,
      }
      metrics.flyingPackets = [...metrics.flyingPackets, newPacket].slice(-8)
    }

    switch (event.event) {
      case 'FRAME_SENT': {
        metrics.framesSent += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const seq = typeof data.sequence_number === 'number' ? data.sequence_number : undefined
        if (fIdx !== undefined) {
          if (metrics.frameStatuses[fIdx] !== 'acknowledged') {
            metrics.frameStatuses[fIdx] = 'in_flight'
          }
        }
        if (typeof data.window_base === 'number') metrics.windowBase = data.window_base
        if (typeof data.window_size === 'number') metrics.windowSize = data.window_size

        addPacket({
          type: 'FRAME',
          frameIndex: fIdx,
          sequenceNumber: seq,
          direction: 'to_receiver',
        })
        break
      }

      case 'FRAME_RETRANSMITTED': {
        metrics.retransmissions += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const seq = typeof data.sequence_number === 'number' ? data.sequence_number : undefined
        if (fIdx !== undefined) {
          if (metrics.frameStatuses[fIdx] !== 'acknowledged') {
            metrics.frameStatuses[fIdx] = 'retransmitted'
          }
        }
        if (typeof data.window_base === 'number') metrics.windowBase = data.window_base
        if (typeof data.window_size === 'number') metrics.windowSize = data.window_size

        addPacket({
          type: 'RETRANSMIT',
          frameIndex: fIdx,
          sequenceNumber: seq,
          direction: 'to_receiver',
        })
        break
      }

      case 'FRAME_LOST': {
        metrics.framesLost += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const seq = typeof data.sequence_number === 'number' ? data.sequence_number : undefined
        if (fIdx !== undefined && metrics.frameStatuses[fIdx] !== 'acknowledged') {
          metrics.frameStatuses[fIdx] = 'lost'
        }
        addPacket({
          type: 'LOST_FRAME',
          frameIndex: fIdx,
          sequenceNumber: seq,
          direction: 'to_receiver',
        })
        break
      }

      case 'FRAME_CORRUPTED': {
        metrics.framesCorrupted += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const seq = typeof data.sequence_number === 'number' ? data.sequence_number : undefined
        if (fIdx !== undefined && metrics.frameStatuses[fIdx] !== 'acknowledged') {
          metrics.frameStatuses[fIdx] = 'corrupted'
        }
        addPacket({
          type: 'CORRUPTED',
          frameIndex: fIdx,
          sequenceNumber: seq,
          direction: 'to_receiver',
        })
        break
      }

      case 'FRAME_RECEIVED': {
        metrics.framesReceived += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        if (fIdx !== undefined && metrics.frameStatuses[fIdx] === 'pending') {
          metrics.frameStatuses[fIdx] = 'in_flight'
        }
        break
      }

      case 'FRAME_BUFFERED': {
        metrics.framesBuffered += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        if (fIdx !== undefined) {
          metrics.frameStatuses[fIdx] = 'buffered'
        }
        break
      }

      case 'FRAME_DISCARDED': {
        metrics.framesDiscarded += 1
        break
      }

      case 'ACK_SENT': {
        metrics.acksSent += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const ackNum = typeof data.ack_number === 'number' ? data.ack_number : undefined
        const ackType = typeof data.ack_type === 'string' ? data.ack_type : undefined

        addPacket({
          type: 'ACK',
          frameIndex: fIdx,
          ackNumber: ackNum,
          ackType,
          direction: 'to_sender',
        })
        break
      }

      case 'ACK_RECEIVED': {
        metrics.acksReceived += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        if (typeof data.window_base === 'number') {
          metrics.windowBase = data.window_base
        }

        if (fIdx !== undefined) {
          // If cumulative or Go-Back-N, all preceding frames are acknowledged
          if (state.protocol === 'go_back_n') {
            for (let i = 0; i <= fIdx; i++) {
              metrics.frameStatuses[i] = 'acknowledged'
            }
          } else {
            metrics.frameStatuses[fIdx] = 'acknowledged'
          }
        }
        break
      }

      case 'ACK_LOST': {
        metrics.acksLost += 1
        const fIdx = typeof data.frame_index === 'number' ? data.frame_index : undefined
        const ackNum = typeof data.ack_number === 'number' ? data.ack_number : undefined

        addPacket({
          type: 'LOST_ACK',
          frameIndex: fIdx,
          ackNumber: ackNum,
          direction: 'to_sender',
        })
        break
      }

      case 'TIMEOUT': {
        metrics.timeouts += 1
        const timedOutFrames = Array.isArray(data.timed_out_frames)
          ? (data.timed_out_frames as number[])
          : []
        for (const idx of timedOutFrames) {
          metrics.recentTimeouts.push({ frameIndex: idx, timestamp: now })
          if (metrics.frameStatuses[idx] !== 'acknowledged') {
            metrics.frameStatuses[idx] = 'lost'
          }
        }
        if (timedOutFrames.length === 0) {
          metrics.recentTimeouts.push({ timestamp: now })
        }
        break
      }

      case 'WINDOW_UPDATED': {
        if (typeof data.window_base === 'number') metrics.windowBase = data.window_base
        if (typeof data.window_size === 'number') metrics.windowSize = data.window_size
        metrics.lastWindowUpdate = data
        break
      }

      case 'TRANSFER_PROGRESS': {
        const progData = data as TransferProgressData
        if (typeof progData.acknowledged_frames === 'number') {
          const acked = progData.acknowledged_frames
          for (let i = 0; i < acked; i++) {
            metrics.frameStatuses[i] = 'acknowledged'
          }
          if (metrics.windowBase < acked) {
            metrics.windowBase = acked
          }
        }
        set((s) => ({
          progress: { ...s.progress, ...progData },
          metrics,
          recentEvents,
          statusMessage: 'Transfer in progress',
        }))
        return
      }

      case 'INTEGRITY_CHECK_COMPLETED': {
        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Integrity check verified',
          transfer: s.transfer ? { ...s.transfer, integrity_verified: true } : s.transfer,
        }))
        return
      }

      case 'INTEGRITY_CHECK_FAILED': {
        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Integrity check failed',
          error: 'SHA-256 verification failed',
          transfer: s.transfer ? { ...s.transfer, integrity_verified: false } : s.transfer,
        }))
        return
      }

      case 'TRANSFER_STARTED': {
        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Transfer started',
          startedAt: s.startedAt ?? Date.now(),
          transfer: s.transfer ? { ...s.transfer, status: 'transferring' } : s.transfer,
        }))
        return
      }

      case 'TRANSFER_COMPLETED': {
        // Mark all frames as acknowledged
        const total = (state.progress.total_frames ?? state.transfer?.total_frames ?? 0) as number
        if (total > 0) {
          for (let i = 0; i < total; i++) {
            metrics.frameStatuses[i] = 'acknowledged'
          }
          metrics.windowBase = total
        }

        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Transfer completed successfully',
          progress: { ...s.progress, progress_percentage: 100 },
          transfer: s.transfer
            ? { ...s.transfer, status: 'completed', integrity_verified: true }
            : s.transfer,
        }))
        return
      }

      case 'TRANSFER_FAILED': {
        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Transfer failed',
          error: String(data.reason ?? 'Transfer failed'),
          transfer: s.transfer ? { ...s.transfer, status: 'failed' } : s.transfer,
        }))
        return
      }

      case 'TRANSFER_CANCELLED': {
        set((s) => ({
          metrics,
          recentEvents,
          statusMessage: 'Transfer cancelled',
          transfer: s.transfer ? { ...s.transfer, status: 'cancelled' } : s.transfer,
        }))
        return
      }

      default:
        break
    }

    set({ metrics, recentEvents })
  },

  resetTransferRuntime: () =>
    set({
      activeTransferId: null,
      transfer: null,
      progress: {},
      metrics: emptyMetrics(),
      report: null,
      recentEvents: [],
      statusMessage: null,
      error: null,
      startedAt: null,
    }),

  resetAll: () =>
    set({
      protocol: 'selective_repeat',
      config: { ...DEFAULT_CONFIG },
      activeTransferId: null,
      transfer: null,
      pendingTransfers: [],
      progress: {},
      metrics: emptyMetrics(),
      report: null,
      recentEvents: [],
      statusMessage: null,
      error: null,
      startedAt: null,
    }),
}))
