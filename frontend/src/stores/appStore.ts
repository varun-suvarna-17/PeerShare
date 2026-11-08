import { create } from 'zustand'
import type { DeviceRole, NetworkStatus } from '../types/api'

interface AppState {
  role: DeviceRole | null
  network: NetworkStatus | null
  networkError: string | null
  backendOnline: boolean | null
  wsStatus: 'connecting' | 'open' | 'closed' | 'error'
  setRole: (role: DeviceRole | null) => void
  setNetwork: (network: NetworkStatus | null) => void
  setNetworkError: (error: string | null) => void
  setBackendOnline: (online: boolean | null) => void
  setWsStatus: (status: AppState['wsStatus']) => void
  resetApp: () => void
}

export const useAppStore = create<AppState>((set) => ({
  role: null,
  network: null,
  networkError: null,
  backendOnline: null,
  wsStatus: 'closed',
  setRole: (role) => set({ role }),
  setNetwork: (network) => set({ network, role: network?.role ?? null }),
  setNetworkError: (networkError) => set({ networkError }),
  setBackendOnline: (backendOnline) => set({ backendOnline }),
  setWsStatus: (wsStatus) => set({ wsStatus }),
  resetApp: () =>
    set({
      role: null,
      network: null,
      networkError: null,
      backendOnline: null,
      wsStatus: 'closed',
    }),
}))
