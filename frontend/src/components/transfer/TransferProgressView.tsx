import type { TransferDetails, TransferReport } from '../../types/api'
import type { NetworkMetrics, TransferProgressData, WsEvent } from '../../types/events'
import { PROTOCOL_LABELS } from '../../constants/protocols'
import { formatBytes, formatDuration, formatPercent, formatSpeed } from '../../utils/format'
import { ProgressBar } from '../ui/ProgressBar'
import { StatusBadge } from '../ui/StatusBadge'
import { PacketFlowVisualizer } from '../visualization/PacketFlowVisualizer'
import { SlidingWindowVisualizer } from '../visualization/SlidingWindowVisualizer'
import { TransferStatsGrid } from '../visualization/TransferStatsGrid'
import { EventConsole } from '../visualization/EventConsole'
import { TransferCompletionCard } from './TransferCompletionCard'

interface TransferProgressViewProps {
  transfer: TransferDetails | null
  progress: TransferProgressData
  metrics: NetworkMetrics
  events: WsEvent[]
  report: TransferReport | null
  startedAt: number | null
  nowMs: number
  statusMessage: string | null
  senderLabel?: string
  receiverLabel?: string
}

function toneForStatus(status?: string) {
  switch (status) {
    case 'completed':
      return 'success' as const
    case 'failed':
    case 'cancelled':
      return 'danger' as const
    case 'transferring':
      return 'info' as const
    case 'pending':
    case 'pending_acceptance':
    case 'accepted':
      return 'warning' as const
    default:
      return 'neutral' as const
  }
}

export function TransferProgressView({
  transfer,
  progress,
  metrics,
  events,
  report,
  startedAt,
  nowMs,
  statusMessage,
  senderLabel = 'Sender Laptop',
  receiverLabel = 'Receiver Laptop',
}: TransferProgressViewProps) {
  const percent = progress.progress_percentage ?? (transfer?.status === 'completed' ? 100 : 0)
  const totalBytes = progress.total_bytes ?? transfer?.file_size
  const transferred = progress.bytes_sent ?? progress.bytes_received
  const elapsedSec =
    startedAt != null && nowMs > startedAt ? (nowMs - startedAt) / 1000 : null
  const derivedSpeed =
    transferred != null && elapsedSec != null && elapsedSec > 0 ? transferred / elapsedSec : null
  const speed = progress.speed_bps ?? derivedSpeed
  const eta =
    progress.eta_seconds ??
    (speed && totalBytes != null && transferred != null && speed > 0
      ? (totalBytes - transferred) / speed
      : null)

  const isTerminal =
    transfer?.status === 'completed' ||
    transfer?.status === 'failed' ||
    transfer?.status === 'cancelled'

  const protocolId = transfer?.protocol || 'selective_repeat'
  const protocolName = PROTOCOL_LABELS[protocolId] || protocolId
  const totalFrames = progress.total_frames ?? report?.total_frames ?? 0

  return (
    <div className="space-y-6">
      {/* Transfer Completion Card (Prominent when finished) */}
      {isTerminal && (
        <TransferCompletionCard
          transfer={transfer}
          report={report}
          elapsedSeconds={elapsedSec}
        />
      )}

      {/* Main Transfer Progress Header Card */}
      <div className="rounded-[28px] border border-[var(--border)] bg-[var(--bg-light)] p-6 md:p-8 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase font-bold tracking-wider text-[var(--text-muted)]">
              File Transmission Status
            </p>
            <h1 className="mt-1 font-[family-name:var(--font-display)] text-3xl font-semibold italic text-[var(--text)]">
              {transfer?.file_name || 'Preparing transfer…'}
            </h1>
          </div>
          <StatusBadge tone={toneForStatus(transfer?.status)}>
            {String(transfer?.status || statusMessage || 'idle')}
          </StatusBadge>
        </div>

        <div className="mt-6 space-y-2.5">
          <div className="flex items-end justify-between gap-3">
            <p className="text-4xl font-bold tracking-tight text-[var(--text)] font-mono">
              {formatPercent(percent)}
            </p>
            <p className="text-sm text-[var(--text-muted)] font-mono">
              {formatBytes(transferred)} / {formatBytes(totalBytes)}
            </p>
          </div>
          <ProgressBar value={percent} label="Overall transfer progress" />
        </div>

        <dl className="mt-6 grid gap-4 grid-cols-2 lg:grid-cols-4 pt-4 border-t border-[var(--border-muted)]">
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Transfer Speed</dt>
            <dd className="mt-1 font-semibold text-sm">{formatSpeed(speed)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Estimated Remaining</dt>
            <dd className="mt-1 font-semibold text-sm">{formatDuration(eta)}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">ARQ Protocol</dt>
            <dd className="mt-1 font-semibold text-sm">{protocolName}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-[var(--text-muted)]">Time Elapsed</dt>
            <dd className="mt-1 font-semibold text-sm font-mono">
              {elapsedSec ? `${elapsedSec.toFixed(1)}s` : '0s'}
            </dd>
          </div>
        </dl>

        {statusMessage && !isTerminal && (
          <p className="mt-4 text-xs font-medium text-[var(--primary)] flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[var(--primary)] animate-pulse" />
            {statusMessage}
          </p>
        )}
      </div>

      {/* Real-time Network Visualizations */}
      <PacketFlowVisualizer
        metrics={metrics}
        senderLabel={senderLabel}
        receiverLabel={receiverLabel}
        protocolName={protocolName}
      />

      <SlidingWindowVisualizer
        metrics={metrics}
        protocol={protocolId}
        totalFrames={totalFrames}
      />

      {/* Live Numerical Transfer Metrics */}
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-[var(--text)] px-1">Detailed Protocol Statistics</h3>
        <TransferStatsGrid metrics={metrics} totalFrames={totalFrames} />
      </div>

      {/* Real-time WebSocket Event Log Console */}
      <EventConsole events={events} />
    </div>
  )
}
