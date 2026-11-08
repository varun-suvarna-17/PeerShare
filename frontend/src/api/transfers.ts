import { api } from './client'
import type {
  ApiResponse,
  PendingTransfer,
  ProtocolId,
  TransferConfig,
  TransferDetails,
  TransferReport,
} from '../types/api'

export async function requestTransfer(payload: {
  file_id: string
  protocol: ProtocolId
  configuration?: Partial<TransferConfig>
}): Promise<{ transfer_id: string; status: string }> {
  const { data } = await api.post<ApiResponse<{ transfer_id: string; status: string }>>(
    '/api/transfers/request',
    payload,
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Transfer request failed')
  return data.data
}

export async function listPendingTransfers(): Promise<PendingTransfer[]> {
  const { data } = await api.get<ApiResponse<{ transfers: PendingTransfer[] }>>(
    '/api/transfers/pending',
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to load pending transfers')
  return data.data.transfers
}

export async function acceptTransfer(transferId: string): Promise<void> {
  const { data } = await api.post<ApiResponse>(`/api/transfers/${transferId}/accept`, {})
  if (!data.success) throw new Error(data.message || 'Failed to accept transfer')
}

export async function rejectTransfer(transferId: string, reason?: string): Promise<void> {
  const { data } = await api.post<ApiResponse>(`/api/transfers/${transferId}/reject`, {
    reason: reason || 'Receiver rejected the transfer',
  })
  if (!data.success) throw new Error(data.message || 'Failed to reject transfer')
}

export async function startTransfer(transferId: string): Promise<{
  transfer_id: string
  status: string
  protocol: ProtocolId
}> {
  const { data } = await api.post<
    ApiResponse<{ transfer_id: string; status: string; protocol: ProtocolId }>
  >(`/api/transfers/${transferId}/start`, {})
  if (!data.success || !data.data) throw new Error(data.message || 'Failed to start transfer')
  return data.data
}

export async function cancelTransfer(transferId: string, reason?: string): Promise<void> {
  const { data } = await api.post<ApiResponse>(`/api/transfers/${transferId}/cancel`, {
    reason: reason || 'User cancelled the transfer',
  })
  if (!data.success) throw new Error(data.message || 'Failed to cancel transfer')
}

export async function getTransfer(transferId: string): Promise<TransferDetails> {
  const { data } = await api.get<ApiResponse<TransferDetails>>(`/api/transfers/${transferId}`)
  if (!data.success || !data.data) throw new Error(data.message || 'Transfer not found')
  return data.data
}

export async function getTransferReport(transferId: string): Promise<TransferReport> {
  const { data } = await api.get<ApiResponse<TransferReport>>(
    `/api/transfers/${transferId}/report`,
  )
  if (!data.success || !data.data) throw new Error(data.message || 'Report unavailable')
  return data.data
}
