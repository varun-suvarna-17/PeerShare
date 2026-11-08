import { api } from './client'
import type { ApiResponse, DeviceRole, NetworkStatus } from '../types/api'

export async function getNetworkStatus(): Promise<NetworkStatus> {
  const { data } = await api.get<ApiResponse<NetworkStatus>>('/api/network/status')
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to load network status')
  return data.data
}

export async function setRole(role: DeviceRole): Promise<{ role: DeviceRole; device_id: string }> {
  const { data } = await api.post<ApiResponse<{ role: DeviceRole; device_id: string }>>(
    '/api/role',
    { role },
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to set role')
  return data.data
}
