import { Activity, AlertTriangle, ArrowDownUp, CheckCircle, Clock, Percent, ShieldAlert } from 'lucide-react'
import type { NetworkMetrics } from '../../types/events'

interface TransferStatsGridProps {
  metrics: NetworkMetrics
  totalFrames?: number
}

function StatCard({
  label,
  value,
  subvalue,
  icon: Icon,
  tone = 'default',
}: {
  label: string
  value: string | number
  subvalue?: string
  icon: React.ComponentType<{ className?: string }>
  tone?: 'default' | 'success' | 'warning' | 'danger'
}) {
  let iconToneClass = 'bg-[var(--surface-muted)] text-[var(--primary)]'
  if (tone === 'success') iconToneClass = 'bg-emerald-50 text-emerald-600'
  if (tone === 'warning') iconToneClass = 'bg-amber-50 text-amber-600'
  if (tone === 'danger') iconToneClass = 'bg-rose-50 text-rose-600'

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--bg-light)] p-4 flex items-start gap-3.5 shadow-2xs">
      <div className={`p-2.5 rounded-xl shrink-0 ${iconToneClass}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-[var(--text-muted)] truncate">{label}</p>
        <p className="mt-1 text-xl font-bold tracking-tight text-[var(--text)]">{value}</p>
        {subvalue && <p className="mt-0.5 text-[11px] text-[var(--text-muted)]">{subvalue}</p>}
      </div>
    </div>
  )
}

export function TransferStatsGrid({ metrics, totalFrames = 0 }: TransferStatsGridProps) {
  const totalAttempts = metrics.framesSent + metrics.retransmissions
  const retransmitRate =
    metrics.framesSent > 0
      ? `${((metrics.retransmissions / metrics.framesSent) * 100).toFixed(1)}%`
      : '0.0%'

  const totalDrops = metrics.framesLost + metrics.acksLost
  const lossRate =
    totalAttempts > 0
      ? `${((metrics.framesLost / totalAttempts) * 100).toFixed(1)}%`
      : '0.0%'

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
      <StatCard
        label="Frames Sent / Unique"
        value={`${metrics.framesSent} / ${totalFrames}`}
        subvalue={`Transmissions: ${totalAttempts}`}
        icon={ArrowDownUp}
        tone="default"
      />
      <StatCard
        label="ACKs Handled"
        value={metrics.acksReceived}
        subvalue={`Sent: ${metrics.acksSent}`}
        icon={CheckCircle}
        tone="success"
      />
      <StatCard
        label="Retransmissions"
        value={metrics.retransmissions}
        subvalue={`Retry Rate: ${retransmitRate}`}
        icon={Percent}
        tone={metrics.retransmissions > 0 ? 'warning' : 'default'}
      />
      <StatCard
        label="Simulated Loss"
        value={totalDrops}
        subvalue={`Data: ${metrics.framesLost} · ACK: ${metrics.acksLost} (${lossRate})`}
        icon={ShieldAlert}
        tone={totalDrops > 0 ? 'danger' : 'default'}
      />
      <StatCard
        label="Timeouts"
        value={metrics.timeouts}
        subvalue="ARQ Timer Expirations"
        icon={Clock}
        tone={metrics.timeouts > 0 ? 'warning' : 'default'}
      />
      <StatCard
        label="CRC Corrupted"
        value={metrics.framesCorrupted}
        subvalue="Failed CRC32 check"
        icon={AlertTriangle}
        tone={metrics.framesCorrupted > 0 ? 'danger' : 'default'}
      />
      <StatCard
        label="Buffered Out-of-Order"
        value={metrics.framesBuffered}
        subvalue="Selective Repeat buffer"
        icon={Activity}
        tone="default"
      />
      <StatCard
        label="Discarded / Duplicate"
        value={metrics.framesDiscarded}
        subvalue="Out of window or duplicate"
        icon={AlertTriangle}
        tone={metrics.framesDiscarded > 0 ? 'warning' : 'default'}
      />
    </div>
  )
}
