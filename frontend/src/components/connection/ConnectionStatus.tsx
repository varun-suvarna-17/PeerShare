import type { ConnectionPhase } from '../../stores/connectionStore'
import { StatusBadge } from '../ui/StatusBadge'
import { Spinner } from '../ui/Spinner'

const labels: Record<ConnectionPhase, { text: string; tone: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }> = {
  idle: { text: 'Ready', tone: 'neutral' },
  discovering: { text: 'Searching', tone: 'info' },
  connecting: { text: 'Connecting', tone: 'info' },
  awaiting_approval: { text: 'Waiting for approval', tone: 'warning' },
  establishing: { text: 'Establishing session', tone: 'info' },
  connected: { text: 'Connected', tone: 'success' },
  failed: { text: 'Connection failed', tone: 'danger' },
}

interface ConnectionStatusProps {
  phase: ConnectionPhase
  detail?: string | null
}

export function ConnectionStatusPanel({ phase, detail }: ConnectionStatusProps) {
  const meta = labels[phase]
  const busy = ['discovering', 'connecting', 'awaiting_approval', 'establishing'].includes(phase)

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-[var(--border-muted)] bg-white px-4 py-3">
      <StatusBadge tone={meta.tone}>{meta.text}</StatusBadge>
      {busy ? <Spinner label="" className="gap-0" /> : null}
      {detail ? <p className="text-sm text-[var(--text-muted)]">{detail}</p> : null}
    </div>
  )
}
