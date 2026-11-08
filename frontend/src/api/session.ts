import { api } from './client'
import type { ApiResponse, EstablishSessionResult, SessionInfo } from '../types/api'

export async function getSession(): Promise<SessionInfo | null> {
  const { data } = await api.get<ApiResponse<SessionInfo | null>>('/api/session')
  if (!data.success) throw new Error(data.message || 'Failed to load session')
  return data.data
}

export async function endSession(): Promise<void> {
  const { data } = await api.delete<ApiResponse>('/api/session')
  if (!data.success) throw new Error(data.message || 'Failed to end session')
}

export async function establishSession(payload: {
  target_ip?: string
  target_port?: number
  device_id?: string
}): Promise<EstablishSessionResult> {
  const { data } = await api.post<ApiResponse<EstablishSessionResult>>(
    '/api/session/establish',
    payload,
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to establish session')
  return data.data
}
