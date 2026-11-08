import { create } from 'zustand'
import type { SelectedFileInfo } from '../types/api'

export interface LocalSelectedFile {
  localId: string
  file: File
  uploaded?: SelectedFileInfo
  uploading?: boolean
  error?: string | null
}

interface FileState {
  files: LocalSelectedFile[]
  addFiles: (files: File[]) => void
  removeFile: (localId: string) => void
  clearFiles: () => void
  setUploaded: (localId: string, uploaded: SelectedFileInfo) => void
  setUploading: (localId: string, uploading: boolean, error?: string | null) => void
  primaryUploaded: () => SelectedFileInfo | null
  totalSize: () => number
}

export const useFileStore = create<FileState>((set, get) => ({
  files: [],
  addFiles: (incoming) =>
    set((state) => {
      const next = [...state.files]
      for (const file of incoming) {
        const exists = next.some(
          (f) => f.file.name === file.name && f.file.size === file.size && f.file.lastModified === file.lastModified,
        )
        if (!exists) {
          next.push({
            localId: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
            file,
            uploading: false,
            error: null,
          })
        }
      }
      return { files: next }
    }),
  removeFile: (localId) => set((state) => ({ files: state.files.filter((f) => f.localId !== localId) })),
  clearFiles: () => set({ files: [] }),
  setUploaded: (localId, uploaded) =>
    set((state) => ({
      files: state.files.map((f) =>
        f.localId === localId ? { ...f, uploaded, uploading: false, error: null } : f,
      ),
    })),
  setUploading: (localId, uploading, error = null) =>
    set((state) => ({
      files: state.files.map((f) => (f.localId === localId ? { ...f, uploading, error } : f)),
    })),
  primaryUploaded: () => get().files.find((f) => f.uploaded)?.uploaded ?? null,
  totalSize: () => get().files.reduce((sum, f) => sum + f.file.size, 0),
}))
