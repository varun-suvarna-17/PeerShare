import { api } from './client'
import type { ApiResponse, SelectedFileInfo } from '../types/api'

export async function selectFile(file: File): Promise<SelectedFileInfo> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<ApiResponse<SelectedFileInfo>>('/api/files/select', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
  if (!data.success || !data.data) throw new Error(data.message || 'File selection failed')
  return data.data
}

export async function getFileInfo(fileId: string): Promise<SelectedFileInfo> {
  const { data } = await api.get<ApiResponse<SelectedFileInfo>>(`/api/files/${fileId}`)
  if (!data.success || !data.data) throw new Error(data.message || 'File not found')
  return data.data
}
