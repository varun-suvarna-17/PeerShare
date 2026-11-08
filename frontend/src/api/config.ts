import { api } from './client'
import type { ApiResponse, ProtocolId, ProtocolOption, TransferConfig } from '../types/api'

export async function listProtocols(): Promise<ProtocolOption[]> {
  const { data } = await api.get<ApiResponse<{ protocols: ProtocolOption[] }>>('/api/protocols')
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to load protocols')
  return data.data.protocols
}

export async function getConfig(protocol: ProtocolId): Promise<TransferConfig> {
  const { data } = await api.get<ApiResponse<TransferConfig>>('/api/config', {
    params: { protocol },
  })
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to load config')
  return data.data
}

export async function updateConfig(
  protocol: ProtocolId,
  config: Partial<TransferConfig>,
): Promise<void> {
  const { data } = await api.put<ApiResponse>('/api/config', config, {
    params: { protocol },
  })
  if (!data.success) throw new Error(data.message || 'Failed to update config')
}
