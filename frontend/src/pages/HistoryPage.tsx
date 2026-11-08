import { useEffect } from 'react'
import { History as HistoryIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { Spinner } from '../components/ui/Spinner'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Button } from '../components/ui/Button'
import { ROUTES, transferPath } from '../constants/routes'
import { PROTOCOL_LABELS } from '../constants/protocols'
import { useHistoryStore } from '../stores/historyStore'
import { formatBytes, formatDateTime } from '../utils/format'

function statusTone(status: string) {
  if (status === 'completed') return 'success' as const
  if (status === 'failed' || status === 'cancelled') return 'danger' as const
  return 'neutral' as const
}

export function HistoryPage() {
  const entries = useHistoryStore((s) => s.entries)
  const loading = useHistoryStore((s) => s.loading)
  const error = useHistoryStore((s) => s.error)
  const hydrate = useHistoryStore((s) => s.hydrate)
  const clear = useHistoryStore((s) => s.clear)

  useEffect(() => {
    hydrate()
  }, [hydrate])

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold italic text-[var(--text)]">
            Transfer history
          </h1>
          <p className="mt-2 text-[var(--text-muted)]">
            Stored locally in this browser. The backend does not yet expose a history API.
          </p>
        </div>
        {entries.length > 0 ? (
          <Button variant="secondary" size="sm" onClick={clear}>
            Clear history
          </Button>
        ) : null}
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {loading ? <Spinner label="Loading history…" /> : null}

      {!loading && entries.length === 0 ? (
        <EmptyState
          title="No transfers yet"
          description="Completed send and receive sessions on this device will appear here."
          icon={<HistoryIcon className="h-8 w-8" />}
          action={
            <Link to={ROUTES.home}>
              <Button>Go home</Button>
            </Link>
          }
        />
      ) : null}

      <ul className="space-y-3">
        {entries.map((entry) => (
          <li key={entry.id}>
            <Link
              to={transferPath(entry.transferId)}
              className="block rounded-[20px] border border-[var(--border)] bg-[var(--bg-light)] px-5 py-4 transition hover:border-[var(--primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] shadow-2xs"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-[var(--text)]">{entry.fileName}</p>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">
                    {entry.role === 'SENDER' ? 'Sent to' : 'Received from'} {entry.peerLabel} ·{' '}
                    {PROTOCOL_LABELS[entry.protocol] || entry.protocol}
                  </p>
                </div>
                <StatusBadge tone={statusTone(String(entry.status))}>
                  {String(entry.status)}
                </StatusBadge>
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-sm text-[var(--text-muted)]">
                <span>{formatBytes(entry.fileSize)}</span>
                <span>{formatDateTime(entry.completedAt)}</span>
                {entry.integrityVerified != null ? (
                  <span>{entry.integrityVerified ? 'Integrity verified' : 'Integrity failed'}</span>
                ) : null}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
