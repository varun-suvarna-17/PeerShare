import { create } from 'zustand'
import type {
  ConnectResult,
  DiscoveredDevice,
  PendingConnection,
  PinInfo,
  SessionInfo,
} from '../types/api'

export type ConnectionPhase =
  | 'idle'
  | 'discovering'
  | 'connecting'
  | 'awaiting_approval'
  | 'establishing'
  | 'connected'
  | 'failed'

interface ConnectionState {
  phase: ConnectionPhase
  devices: DiscoveredDevice[]
  selectedDevice: DiscoveredDevice | null
  pinInfo: PinInfo | null
  pinGeneratedAt: number | null
  pendingConnections: PendingConnection[]
  connectResult: ConnectResult | null
  targetIp: string | null
  targetPort: number | null
  session: SessionInfo | null
  error: string | null
  setPhase: (phase: ConnectionPhase) => void
  setDevices: (devices: DiscoveredDevice[]) => void
  setSelectedDevice: (device: DiscoveredDevice | null) => void
  setPinInfo: (pinInfo: PinInfo | null) => void
  setPinGeneratedAt: (ts: number | null) => void
  setPendingConnections: (connections: PendingConnection[]) => void
  setConnectResult: (result: ConnectResult | null) => void
  setTarget: (ip: string | null, port: number | null) => void
  setSession: (session: SessionInfo | null) => void
  setError: (error: string | null) => void
  resetConnection: () => void
}

const initial = {
  phase: 'idle' as ConnectionPhase,
  devices: [] as DiscoveredDevice[],
  selectedDevice: null as DiscoveredDevice | null,
  pinInfo: null as PinInfo | null,
  pinGeneratedAt: null as number | null,
  pendingConnections: [] as PendingConnection[],
  connectResult: null as ConnectResult | null,
  targetIp: null as string | null,
  targetPort: null as number | null,
  session: null as SessionInfo | null,
  error: null as string | null,
}

export const useConnectionStore = create<ConnectionState>((set) => ({
  ...initial,
  setPhase: (phase) => set({ phase }),
  setDevices: (devices) => set({ devices }),
  setSelectedDevice: (selectedDevice) => set({ selectedDevice }),
  setPinInfo: (pinInfo) => set({ pinInfo }),
  setPinGeneratedAt: (pinGeneratedAt) => set({ pinGeneratedAt }),
  setPendingConnections: (pendingConnections) => set({ pendingConnections }),
  setConnectResult: (connectResult) => set({ connectResult }),
  setTarget: (targetIp, targetPort) => set({ targetIp, targetPort }),
  setSession: (session) => set({ session, phase: session ? 'connected' : 'idle' }),
  setError: (error) => set({ error }),
  resetConnection: () => set({ ...initial }),
}))
