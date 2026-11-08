export type WsEventName =
  | 'DEVICE_DISCOVERED'
  | 'CONNECTION_REQUEST'
  | 'CONNECTION_APPROVED'
  | 'CONNECTION_REJECTED'
  | 'SESSION_ESTABLISHED'
  | 'SESSION_ENDED'
  | 'TRANSFER_REQUEST'
  | 'TRANSFER_ACCEPTED'
  | 'TRANSFER_REJECTED'
  | 'TRANSFER_STARTED'
  | 'TRANSFER_PROGRESS'
  | 'TRANSFER_COMPLETED'
  | 'TRANSFER_FAILED'
  | 'TRANSFER_CANCELLED'
  | 'FRAME_SENT'
  | 'FRAME_RECEIVED'
  | 'ACK_SENT'
  | 'ACK_RECEIVED'
  | 'FRAME_LOST'
  | 'ACK_LOST'
  | 'FRAME_CORRUPTED'
  | 'TIMEOUT'
  | 'FRAME_RETRANSMITTED'
  | 'FRAME_BUFFERED'
  | 'FRAME_DISCARDED'
  | 'WINDOW_UPDATED'
  | 'FILE_RECONSTRUCTION_STARTED'
  | 'FILE_RECONSTRUCTION_COMPLETED'
  | 'INTEGRITY_CHECK_STARTED'
  | 'INTEGRITY_CHECK_COMPLETED'
  | 'INTEGRITY_CHECK_FAILED'

export interface WsEvent<T = Record<string, unknown>> {
  event_id: string
  event_seq: number
  device_id: string
  event: WsEventName
  timestamp: string
  session_id: string | null
  transfer_id: string | null
  data: T
}

export interface TransferProgressData {
  bytes_sent?: number
  bytes_received?: number
  total_bytes?: number
  progress_percentage?: number
  current_file?: string
  speed_bps?: number
  eta_seconds?: number
  acknowledged_frames?: number
  total_frames?: number
}

export type FrameSlotStatus =
  | 'pending'
  | 'in_flight'
  | 'acknowledged'
  | 'buffered'
  | 'lost'
  | 'corrupted'
  | 'retransmitted'

export interface FlyingPacket {
  id: string
  type: 'FRAME' | 'ACK' | 'LOST_FRAME' | 'LOST_ACK' | 'CORRUPTED' | 'RETRANSMIT'
  frameIndex?: number
  sequenceNumber?: number
  ackNumber?: number
  ackType?: string
  timestamp: number
  direction: 'to_receiver' | 'to_sender'
}

export interface NetworkMetrics {
  framesSent: number
  framesReceived: number
  acksSent: number
  acksReceived: number
  framesLost: number
  acksLost: number
  framesCorrupted: number
  timeouts: number
  retransmissions: number
  framesBuffered: number
  framesDiscarded: number
  windowBase: number
  windowSize: number
  frameStatuses: Record<number, FrameSlotStatus>
  flyingPackets: FlyingPacket[]
  recentTimeouts: { frameIndex?: number; timestamp: number }[]
  lastWindowUpdate: Record<string, unknown> | null
  lastEventAt: string | null
}
