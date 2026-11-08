import { useEffect, useRef } from 'react'
import { motion } from 'motion/react'
import { Check, Clock, Layers, RefreshCw, X } from 'lucide-react'
import type { FrameSlotStatus, NetworkMetrics } from '../../types/events'
import type { ProtocolId } from '../../types/api'

interface SlidingWindowVisualizerProps {
  metrics: NetworkMetrics
  protocol: ProtocolId
  totalFrames?: number
}

function getSlotColor(status: FrameSlotStatus | undefined, isInsideWindow: boolean) {
  switch (status) {
    case 'acknowledged':
      return 'bg-emerald-500 text-white border-emerald-600 shadow-xs'
    case 'buffered':
      return 'bg-purple-600 text-white border-purple-700 shadow-xs animate-pulse'
    case 'retransmitted':
      return 'bg-amber-500 text-white border-amber-600'
    case 'lost':
    case 'corrupted':
      return 'bg-rose-500 text-white border-rose-600'
    case 'in_flight':
      return 'bg-[var(--primary)] text-white border-[var(--primary)] shadow-xs'
    default:
      return isInsideWindow
        ? 'bg-blue-50 text-[var(--primary)] border-blue-300 border-dashed'
        : 'bg-stone-100 text-stone-400 border-stone-200'
  }
}

function getStatusIcon(status: FrameSlotStatus | undefined) {
  switch (status) {
    case 'acknowledged':
      return <Check className="w-3.5 h-3.5" />
    case 'buffered':
      return <Clock className="w-3.5 h-3.5" />
    case 'retransmitted':
      return <RefreshCw className="w-3 h-3 animate-spin" />
    case 'lost':
    case 'corrupted':
      return <X className="w-3.5 h-3.5" />
    default:
      return null
  }
}

export function SlidingWindowVisualizer({
  metrics,
  protocol,
  totalFrames = 10,
}: SlidingWindowVisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const effectiveTotal = Math.max(totalFrames, metrics.windowBase + metrics.windowSize + 2, 8)
  const windowBase = metrics.windowBase
  const windowSize = protocol === 'stop_and_wait' ? 1 : metrics.windowSize || 4
  const windowEnd = windowBase + windowSize

  // Auto-scroll the container to keep current windowBase in view
  useEffect(() => {
    if (!containerRef.current) return
    const slotWidth = 48 + 8 // 48px slot + 8px gap
    const scrollTarget = Math.max(0, (windowBase - 2) * slotWidth)
    containerRef.current.scrollTo({
      left: scrollTarget,
      behavior: 'smooth',
    })
  }, [windowBase])

  const slots = Array.from({ length: effectiveTotal }, (_, i) => {
    const isInside = i >= windowBase && i < windowEnd
    const status = metrics.frameStatuses[i] || (i < windowBase ? 'acknowledged' : 'pending')
    return {
      index: i,
      isInside,
      status,
    }
  })

  return (
    <div className="rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-5 md:p-6 shadow-xs overflow-hidden">
      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)] flex items-center gap-2">
            <Layers className="w-5 h-5 text-[var(--primary)]" />
            Sliding Window Buffer
          </h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Active sender transmission window and per-frame acknowledgement states
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--border-muted)]">
            <span className="text-[var(--text-muted)]">Window Base:</span>{' '}
            <strong className="text-[var(--text)] font-mono">{windowBase}</strong>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--border-muted)]">
            <span className="text-[var(--text-muted)]">Window Size (N):</span>{' '}
            <strong className="text-[var(--text)] font-mono">{windowSize}</strong>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-[var(--surface-muted)] border border-[var(--border-muted)]">
            <span className="text-[var(--text-muted)]">Total Frames:</span>{' '}
            <strong className="text-[var(--text)] font-mono">{totalFrames}</strong>
          </div>
        </div>
      </div>

      {/* Visual Window Bracket & Frame Slots Container */}
      <div className="relative py-4 bg-[var(--surface-muted)] rounded-2xl border border-[var(--border-muted)] px-3">
        {/* Scrollable Frame Track */}
        <div
          ref={containerRef}
          className="flex items-center gap-2 overflow-x-auto py-3 px-2 scrollbar-thin scrollbar-thumb-stone-300"
        >
          {slots.map((slot) => {
            const colorClass = getSlotColor(slot.status, slot.isInside)
            const icon = getStatusIcon(slot.status)

            return (
              <motion.div
                key={slot.index}
                layout
                className="relative flex flex-col items-center shrink-0"
              >
                {/* Frame Slot Card */}
                <div
                  className={`w-12 h-14 rounded-xl border flex flex-col items-center justify-center font-mono transition-all text-xs relative ${colorClass} ${
                    slot.isInside ? 'ring-2 ring-[var(--primary)] ring-offset-2 scale-105' : ''
                  }`}
                >
                  <span className="text-[10px] opacity-75">#{slot.index}</span>
                  <div className="mt-0.5">{icon || <span className="text-[9px]">—</span>}</div>
                </div>

                {/* Subtitle / Indicator */}
                <span className="mt-1.5 text-[9px] font-mono text-[var(--text-muted)]">
                  {slot.index === windowBase ? (
                    <strong className="text-[var(--primary)]">BASE</strong>
                  ) : slot.index === windowEnd - 1 ? (
                    'END'
                  ) : (
                    slot.index
                  )}
                </span>
              </motion.div>
            )
          })}
        </div>

        {/* Window Range Label */}
        <div className="mt-2 text-center text-xs text-[var(--text-muted)]">
          <span className="inline-flex items-center gap-1.5 bg-white px-3 py-1 rounded-full border border-[var(--border-muted)] shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-[var(--primary)]" />
            <span>
              Active Window Range: [Frames <strong>{windowBase}</strong> to{' '}
              <strong>{Math.max(windowBase, windowEnd - 1)}</strong>]
            </span>
          </span>
        </div>
      </div>

      {/* Legend & Help */}
      <div className="mt-4 pt-3 border-t border-[var(--border-muted)] flex flex-wrap items-center justify-between text-xs text-[var(--text-muted)] gap-3">
        <span className="font-medium text-[var(--text)]">Slot States:</span>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-emerald-500 border border-emerald-600 inline-block" />
            <span>ACK'd</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-[var(--primary)] inline-block" />
            <span>In Flight</span>
          </div>
          {protocol === 'selective_repeat' && (
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-purple-600 inline-block" />
              <span>Buffered (Rx)</span>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-amber-500 inline-block" />
            <span>Retransmitted</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-rose-500 inline-block" />
            <span>Lost / Dropped</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-stone-100 border border-stone-200 inline-block" />
            <span>Pending</span>
          </div>
        </div>
      </div>
    </div>
  )
}
