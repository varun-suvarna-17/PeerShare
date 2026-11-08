export type DeviceRole = 'SENDER' | 'RECEIVER'

export type ProtocolId = 'stop_and_wait' | 'go_back_n' | 'selective_repeat'

export type TransferStatus =
  | 'pending'
  | 'pending_acceptance'
  | 'transferring'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'accepted'
  | 'rejected'

export type SessionStatus =
  | 'CONNECTING'
  | 'ESTABLISHED'
  | 'DISCONNECTED'
  | 'CLOSED'
  | 'connected'

export type ConnectionStatus =
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'REJECTED'
  | 'EXPIRED'

export type DeviceStatus = 'ONLINE' | 'OFFLINE' | 'CONNECTED'

export type DiscoveryMethod = 'ZEROCONF' | 'MANUAL'

export interface ApiResponse<T = Record<string, unknown> | null> {
  success: boolean
  message: string
  data: T
  error_code?: string | null
}

export interface NetworkStatus {
  local_ip: string
  api_port: number
  udp_port: number
  device_id: string
  device_name: string
  role: DeviceRole
}

export interface DiscoveredDevice {
  device_id: string
  device_name: string
  ip_address: string
  api_port: number
  udp_port: number
  status: DeviceStatus
  discovery_method: DiscoveryMethod
}

export interface PinInfo {
  pin: string
  ip_address: string
  expires_in: number
}

export interface ConnectResult {
  connection_id: string
  status: ConnectionStatus | string
  receiver_name?: string
}

export interface PendingConnection {
  connection_id: string
  sender_device_id: string
  sender_device_name: string
  sender_ip: string
  discovery_method: DiscoveryMethod
  requested_at: string
  expires_at: string
}

export interface SessionInfo {
  session_id: string
  status: SessionStatus | string
  local_role: DeviceRole
  peer_ip: string
  peer_api_port?: number
  local_udp_port?: number
  peer_udp_port?: number
  receiver_ready?: boolean
}

export interface EstablishSessionResult {
  session_id: string
  status: string
  peer_ip: string
  peer_api_port: number
  peer_udp_port: number
  session_token?: string
}

export interface SelectedFileInfo {
  file_id: string
  file_name: string
  file_size: number
  file_type: string
  file_sha256: string
  total_frames: number
}

export interface ProtocolOption {
  id: ProtocolId
  name: string
}

export interface TransferConfig {
  protocol?: ProtocolId
  sender_window_size?: number
  receiver_window_size?: number
  window_size?: number
  timeout_ms: number
  max_retries: number
  packet_loss_percentage: number
  frame_delay_ms: number
}

export interface PendingTransfer {
  transfer_id: string
  file_name: string
  file_size: number
  protocol: ProtocolId
  status: TransferStatus | string
}

export interface TransferDetails {
  transfer_id: string
  file_name: string
  file_size?: number
  protocol: ProtocolId
  status: TransferStatus | string
  progress_percentage?: number
  integrity_verified?: boolean
  total_frames?: number
}

export interface TransferReport {
  transfer_id: string
  status: TransferStatus | string
  protocol: ProtocolId
  total_frames: number
  total_transmissions?: number
  integrity_verified: boolean
  reconstructed_path?: string | null
  duration_seconds?: number
  throughput_kbps?: number
  total_acks?: number
  total_retransmissions?: number
  frames_received?: number
}

export interface HistoryEntry {
  id: string
  transferId: string
  fileName: string
  fileSize: number
  role: DeviceRole
  peerLabel: string
  protocol: ProtocolId
  status: TransferStatus | string
  integrityVerified?: boolean
  completedAt: string
}
