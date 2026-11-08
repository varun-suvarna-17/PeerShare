import axios from 'axios'
import { api } from './client'
import type {
  ApiResponse,
  ConnectResult,
  ConnectionStatus,
  DiscoveredDevice,
  PendingConnection,
  PinInfo,
} from '../types/api'

export async function discoverDevices(): Promise<void> {
  const { data } = await api.post<ApiResponse>('/api/devices/discover')
  if (!data.success) throw new Error(data.message || 'Discovery failed')
}

export async function listDevices(): Promise<DiscoveredDevice[]> {
  const { data } = await api.get<ApiResponse<{ devices: DiscoveredDevice[] }>>('/api/devices')
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to list devices')
  return data.data.devices
}

export async function generatePin(): Promise<PinInfo> {
  const { data } = await api.post<ApiResponse<PinInfo>>('/api/devices/pin', {})
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to generate PIN')
  return data.data
}

export async function connectDevice(payload: {
  device_id?: string
  ip_address?: string
  pin?: string
  api_port?: number
}): Promise<ConnectResult> {
  const { data } = await api.post<ApiResponse<ConnectResult>>('/api/devices/connect', payload)
  if (!data.success || !data.data) throw new Error(data.message || 'Connection failed')
  return data.data
}

export async function listPendingConnections(): Promise<PendingConnection[]> {
  const { data } = await api.get<ApiResponse<{ connections: PendingConnection[] }>>(
    '/api/connections/pending',
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to load connections')
  return data.data.connections
}

export async function approveConnection(connectionId: string): Promise<void> {
  const { data } = await api.post<ApiResponse>(`/api/connections/${connectionId}/approve`)
  if (!data.success) throw new Error(data.message || 'Failed to approve connection')
}

export async function rejectConnection(connectionId: string): Promise<void> {
  const { data } = await api.post<ApiResponse>(`/api/connections/${connectionId}/reject`)
  if (!data.success) throw new Error(data.message || 'Failed to reject connection')
}

/** Poll peer-side connection status (no local proxy exists for this). */
export async function pollPeerConnectionStatus(
  peerIp: string,
  peerApiPort: number,
  connectionId: string,
): Promise<ConnectionStatus | string> {
  const { data } = await axios.get<ApiResponse<{ connection_id: string; status: string }>>(
    `http://${peerIp}:${peerApiPort}/peer/connect/${connectionId}/status`,
    { timeout: 5000 },
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to check connection status')
  return data.data.status
}
