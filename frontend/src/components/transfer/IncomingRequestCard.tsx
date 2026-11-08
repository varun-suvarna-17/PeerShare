import type { PendingTransfer } from '../../types/api'
import { PROTOCOL_LABELS } from '../../constants/protocols'
import { formatBytes } from '../../utils/format'
import { Button } from '../ui/Button'

interface IncomingRequestCardProps {
  transfer: PendingTransfer
  onAccept: () => void
  onReject: () => void
  busy?: boolean
}

export function IncomingRequestCard({
  transfer,
  onAccept,
  onReject,
  busy,
}: IncomingRequestCardProps) {
  return (
    <div className="rounded-[20px] border border-[var(--border-muted)] bg-white p-6 shadow-sm">
      <p className="text-sm font-medium uppercase tracking-wide text-[var(--text-muted)]">
        Incoming transfer
      </p>
      <h2 className="mt-2 font-[family-name:var(--font-display)] text-2xl font-semibold italic text-[var(--text)]">
        {transfer.file_name}
      </h2>
      <dl className="mt-6 grid gap-4 sm:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Size</dt>
          <dd className="mt-1 text-base font-medium">{formatBytes(transfer.file_size)}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Protocol</dt>
          <dd className="mt-1 text-base font-medium">
            {PROTOCOL_LABELS[transfer.protocol] || transfer.protocol}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Status</dt>
          <dd className="mt-1 text-base font-medium capitalize">{String(transfer.status)}</dd>
        </div>
      </dl>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button onClick={onAccept} disabled={busy}>
          Accept
        </Button>
        <Button variant="danger" onClick={onReject} disabled={busy}>
          Reject
        </Button>
      </div>
    </div>
  )
}
