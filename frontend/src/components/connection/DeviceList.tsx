import { Laptop } from 'lucide-react'
import type { DiscoveredDevice } from '../../types/api'
import { EmptyState } from '../ui/EmptyState'
import { Spinner } from '../ui/Spinner'

interface DeviceListProps {
  devices: DiscoveredDevice[]
  selectedId?: string | null
  discovering?: boolean
  onSelect: (device: DiscoveredDevice) => void
}

export function DeviceList({ devices, selectedId, discovering, onSelect }: DeviceListProps) {
  if (discovering && devices.length === 0) {
    return <Spinner label="Searching for nearby receivers…" />
  }

  if (devices.length === 0) {
    return (
      <EmptyState
        title="No devices found"
        description="Make sure the receiver is in Receive mode on the same network, or connect with IP and PIN below."
        icon={<Laptop className="h-8 w-8" />}
      />
    )
  }

  return (
    <ul className="space-y-3">
      {devices.map((device) => {
        const selected = device.device_id === selectedId
        return (
          <li key={device.device_id}>
            <button
              type="button"
              onClick={() => onSelect(device)}
              className={`flex w-full items-center gap-4 rounded-2xl border px-4 py-4 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] ${
                selected
                  ? 'border-[var(--primary)] bg-[color-mix(in_oklch,var(--highlight)_35%,white)]'
                  : 'border-[var(--border-muted)] bg-white hover:border-[var(--border)]'
              }`}
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--surface-muted)]">
                <Laptop className="h-5 w-5 text-[var(--primary)]" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-[var(--text)]">{device.device_name}</p>
                <p className="text-sm text-[var(--text-muted)]">
                  {device.ip_address}:{device.api_port} · {device.discovery_method}
                </p>
              </div>
              <span className="text-xs font-medium uppercase tracking-wide text-[var(--success)]">
                {device.status}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
