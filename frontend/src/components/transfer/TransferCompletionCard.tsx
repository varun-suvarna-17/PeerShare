import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { CheckCircle2, HardDrive, ShieldAlert, ShieldCheck, XCircle } from 'lucide-react'
import type { TransferDetails, TransferReport } from '../../types/api'
import { PROTOCOL_LABELS } from '../../constants/protocols'
import { ROUTES } from '../../constants/routes'
import { formatBytes, formatSpeed } from '../../utils/format'
import { Button } from '../ui/Button'

interface TransferCompletionCardProps {
  transfer: TransferDetails | null
  report: TransferReport | null
  elapsedSeconds?: number | null
}

export function TransferCompletionCard({
  transfer,
  report,
  elapsedSeconds,
}: TransferCompletionCardProps) {
  const isCompleted = transfer?.status === 'completed'
  const isFailed = transfer?.status === 'failed' || transfer?.status === 'cancelled'

  if (!isCompleted && !isFailed) return null

  const verified = report?.integrity_verified ?? transfer?.integrity_verified
  const duration = report?.duration_seconds ?? elapsedSeconds ?? 0
  const speed =
    report?.throughput_kbps != null
      ? report.throughput_kbps * 1024 / 8
      : duration > 0 && transfer?.file_size
      ? transfer.file_size / duration
      : null

  const totalFrames = report?.total_frames ?? 0
  const totalTransmissions = report?.total_transmissions ?? totalFrames
  const retransmits = totalTransmissions - totalFrames

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`rounded-[24px] border p-6 md:p-8 shadow-sm ${
        isCompleted
          ? 'border-emerald-300 bg-emerald-50/40'
          : 'border-rose-300 bg-rose-50/40'
      }`}
    >
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div
            className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
              isCompleted
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-rose-600 text-white shadow-sm'
            }`}
          >
            {isCompleted ? <CheckCircle2 className="w-7 h-7" /> : <XCircle className="w-7 h-7" />}
          </div>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-[var(--text)]">
              {isCompleted ? 'File Transfer Complete!' : 'Transfer Failed or Cancelled'}
            </h2>
            <p className="text-sm text-[var(--text-muted)] mt-0.5">
              {transfer?.file_name} · {formatBytes(transfer?.file_size)}
            </p>
          </div>
        </div>

        {/* Integrity Badge */}
        {isCompleted && (
          <div
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold shadow-2xs border ${
              verified
                ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                : 'bg-rose-100 text-rose-800 border-rose-300'
            }`}
          >
            {verified ? <ShieldCheck className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
            <span>{verified ? 'SHA-256 Integrity Verified' : 'Integrity Check Failed'}</span>
          </div>
        )}
      </div>

      {/* Summary Metrics Table */}
      <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-3 bg-white p-4 rounded-2xl border border-[var(--border-muted)]">
        <div>
          <span className="text-[11px] uppercase tracking-wider text-[var(--text-muted)] font-medium">
            Protocol
          </span>
          <p className="mt-1 font-semibold text-[var(--text)] text-sm">
            {transfer?.protocol ? PROTOCOL_LABELS[transfer.protocol] : '—'}
          </p>
        </div>
        <div>
          <span className="text-[11px] uppercase tracking-wider text-[var(--text-muted)] font-medium">
            Total Duration
          </span>
          <p className="mt-1 font-semibold text-[var(--text)] text-sm">
            {duration > 0 ? `${duration.toFixed(2)}s` : '< 1s'}
          </p>
        </div>
        <div>
          <span className="text-[11px] uppercase tracking-wider text-[var(--text-muted)] font-medium">
            Effective Speed
          </span>
          <p className="mt-1 font-semibold text-[var(--text)] text-sm">{formatSpeed(speed)}</p>
        </div>
        <div>
          <span className="text-[11px] uppercase tracking-wider text-[var(--text-muted)] font-medium">
            Transmissions
          </span>
          <p className="mt-1 font-semibold text-[var(--text)] text-sm">
            {totalTransmissions}{' '}
            <span className="text-xs text-[var(--text-muted)] font-normal">
              ({retransmits > 0 ? `+${retransmits} retries` : '0 retries'})
            </span>
          </p>
        </div>
      </div>

      {/* Saved file path on receiver */}
      {report?.reconstructed_path && (
        <div className="mt-4 flex items-center gap-2.5 p-3 rounded-xl bg-white border border-[var(--border-muted)] text-xs font-mono text-[var(--text)]">
          <HardDrive className="w-4 h-4 text-[var(--primary)] shrink-0" />
          <span className="truncate">Saved to: {report.reconstructed_path}</span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Link to={ROUTES.send}>
          <Button size="md">Send another file</Button>
        </Link>
        <Link to={ROUTES.history}>
          <Button variant="secondary" size="md">
            View in history
          </Button>
        </Link>
        <Link to={ROUTES.home}>
          <Button variant="ghost" size="md">
            Dashboard
          </Button>
        </Link>
      </div>
    </motion.div>
  )
}
