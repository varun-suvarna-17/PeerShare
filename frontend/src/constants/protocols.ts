import type { ProtocolId, TransferConfig } from '../types/api'

export const PROTOCOL_LABELS: Record<ProtocolId, string> = {
  stop_and_wait: 'Stop-and-Wait (One-Bit)',
  go_back_n: 'Go-Back-N',
  selective_repeat: 'Selective Repeat',
}

export const DEFAULT_CONFIG: TransferConfig = {
  window_size: 4,
  timeout_ms: 1000,
  max_retries: 5,
  packet_loss_percentage: 0,
  frame_delay_ms: 100,
}

export const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
