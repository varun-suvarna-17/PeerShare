import { create } from 'zustand'
import type { HistoryEntry } from '../types/api'

const STORAGE_KEY = 'peershare.transferHistory'

function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as HistoryEntry[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function persist(entries: HistoryEntry[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
}

interface HistoryState {
  entries: HistoryEntry[]
  loading: boolean
  error: string | null
  hydrate: () => void
  addEntry: (entry: HistoryEntry) => void
  clear: () => void
}

export const useHistoryStore = create<HistoryState>((set, get) => ({
  entries: [],
  loading: false,
  error: null,
  hydrate: () => {
    set({ loading: true, error: null })
    try {
      set({ entries: loadHistory(), loading: false })
    } catch {
      set({ loading: false, error: 'Could not load transfer history' })
    }
  },
  addEntry: (entry) => {
    const existing = get().entries.filter((e) => e.transferId !== entry.transferId)
    const entries = [entry, ...existing].slice(0, 50)
    persist(entries)
    set({ entries })
  },
  clear: () => {
    persist([])
    set({ entries: [] })
  },
}))
