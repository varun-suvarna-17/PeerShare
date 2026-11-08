import type { PinInfo } from '../../types/api'
import { Button } from '../ui/Button'

interface PinDisplayProps {
  pinInfo: PinInfo | null
  remainingSeconds: number | null
  onRefresh: () => void
  loading?: boolean
}

export function PinDisplay({ pinInfo, remainingSeconds, onRefresh, loading }: PinDisplayProps) {
  return (
    <div className="rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
      <h3 className="text-lg font-semibold text-[var(--text)]">Fallback pairing</h3>
      <p className="mt-1 text-sm text-[var(--text-muted)]">
        Share this IP and PIN with the sender if discovery does not find this device.
      </p>

      {pinInfo ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">IP address</p>
            <p className="mt-1 font-mono text-xl text-[var(--text)]">{pinInfo.ip_address}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">PIN</p>
            <p className="mt-1 font-mono text-3xl font-semibold tracking-[0.2em] text-[var(--primary)]">
              {pinInfo.pin}
            </p>
          </div>
        </div>
      ) : (
        <p className="mt-6 text-sm text-[var(--text-muted)]">Generate a PIN to enable manual pairing.</p>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Button onClick={onRefresh} disabled={loading}>
          {pinInfo ? 'Refresh PIN' : 'Generate PIN'}
        </Button>
        {remainingSeconds != null && remainingSeconds > 0 ? (
          <span className="text-sm text-[var(--text-muted)]">Expires in {remainingSeconds}s</span>
        ) : pinInfo ? (
          <span className="text-sm text-[var(--warning)]">PIN expired — generate a new one</span>
        ) : null}
      </div>
    </div>
  )
}
