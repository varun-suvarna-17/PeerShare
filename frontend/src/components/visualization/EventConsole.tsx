import { useState, useRef, useEffect } from 'react'
import { ChevronDown, ChevronUp, Filter, Pause, Play, Terminal } from 'lucide-react'
import type { WsEvent } from '../../types/events'

interface EventConsoleProps {
  events: WsEvent[]
}

type EventFilter = 'all' | 'frames' | 'acks' | 'loss' | 'lifecycle'

function getEventBadgeClass(name: string) {
  if (name.includes('LOST') || name.includes('FAILED') || name.includes('CORRUPTED')) {
    return 'bg-rose-100 text-rose-700 border-rose-300'
  }
  if (name.includes('TIMEOUT') || name.includes('RETRANSMITTED') || name.includes('DISCARDED')) {
    return 'bg-amber-100 text-amber-800 border-amber-300'
  }
  if (name.includes('ACK')) {
    return 'bg-emerald-100 text-emerald-800 border-emerald-300'
  }
  if (name.includes('COMPLETED') || name.includes('APPROVED')) {
    return 'bg-emerald-100 text-emerald-800 border-emerald-300'
  }
  if (name.includes('FRAME')) {
    return 'bg-blue-100 text-blue-800 border-blue-300'
  }
  return 'bg-stone-100 text-stone-700 border-stone-300'
}

function formatNarrative(event: WsEvent): string {
  const d = (event.data || {}) as Record<string, unknown>
  switch (event.event) {
    case 'FRAME_SENT':
      return `Sent frame #${d.frame_index} (seq ${d.sequence_number}, ${d.payload_length ?? 1024} B). Base: ${d.window_base ?? '?'}`
    case 'FRAME_RETRANSMITTED':
      return `Retransmitted frame #${d.frame_index} (seq ${d.sequence_number}). Base: ${d.window_base ?? '?'}`
    case 'FRAME_LOST':
      return `Simulated packet loss on frame #${d.frame_index} (seq ${d.sequence_number})`
    case 'FRAME_CORRUPTED':
      return `Simulated CRC corruption on frame #${d.frame_index} (seq ${d.sequence_number})`
    case 'FRAME_RECEIVED':
      return `Received valid frame #${d.frame_index} (seq ${d.sequence_number})`
    case 'FRAME_BUFFERED':
      return `Buffered out-of-order frame #${d.frame_index} (total buffered: ${d.buffered_count})`
    case 'FRAME_DISCARDED':
      return `Discarded frame #${d.frame_index} (reason: ${d.reason})`
    case 'ACK_SENT':
      return `Sent ACK #${d.frame_index ?? d.ack_number} (${d.ack_type ?? 'ACK'})`
    case 'ACK_RECEIVED':
      return `Received ACK #${d.frame_index ?? d.ack_number}. New window base: ${d.window_base ?? '?'}`
    case 'ACK_LOST':
      return `Simulated drop on ACK for frame #${d.frame_index}`
    case 'TIMEOUT':
      return `Timeout expired! Frames: ${Array.isArray(d.timed_out_frames) ? d.timed_out_frames.join(', ') : 'all in-flight'}`
    case 'WINDOW_UPDATED':
      return `Window slid to base #${d.window_base} (size ${d.window_size})`
    case 'TRANSFER_PROGRESS':
      return `Progress: ${d.progress_percentage}% (${d.acknowledged_frames ?? 0}/${d.total_frames ?? 0} frames)`
    case 'INTEGRITY_CHECK_COMPLETED':
      return `SHA-256 integrity verified successfully`
    case 'TRANSFER_COMPLETED':
      return `Transfer finished in ${typeof d.duration_seconds === 'number' ? d.duration_seconds.toFixed(2) : '?'}s`
    default:
      return JSON.stringify(d)
  }
}

export function EventConsole({ events }: EventConsoleProps) {
  const [open, setOpen] = useState(false)
  const [filter, setFilter] = useState<EventFilter>('all')
  const [autoScroll, setAutoScroll] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const filteredEvents = events.filter((e) => {
    if (filter === 'all') return true
    if (filter === 'frames') return e.event.startsWith('FRAME_')
    if (filter === 'acks') return e.event.startsWith('ACK_')
    if (filter === 'loss')
      return (
        e.event.includes('LOST') ||
        e.event.includes('TIMEOUT') ||
        e.event.includes('CORRUPTED') ||
        e.event.includes('DISCARDED')
      )
    if (filter === 'lifecycle')
      return e.event.startsWith('TRANSFER_') || e.event.startsWith('INTEGRITY_')
    return true
  })

  useEffect(() => {
    if (autoScroll && scrollRef.current && open) {
      scrollRef.current.scrollTop = 0
    }
  }, [autoScroll, events.length, open])

  return (
    <div className="rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] shadow-xs overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left transition hover:bg-[var(--surface-muted)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--primary)]"
      >
        <div className="flex items-center gap-2.5">
          <Terminal className="w-5 h-5 text-[var(--primary)]" />
          <div>
            <h3 className="text-sm font-semibold text-[var(--text)]">
              Live WebSocket Event Log ({events.length} events)
            </h3>
            <p className="text-xs text-[var(--text-muted)]">
              Real-time chronological events published by the networking core
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          <span>{open ? 'Hide Log' : 'Show Log'}</span>
          {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {open && (
        <div className="border-t border-[var(--border-muted)] p-4 bg-stone-50">
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3 text-xs">
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              <button
                type="button"
                onClick={() => setFilter('all')}
                className={`px-2.5 py-1 rounded-full border ${
                  filter === 'all'
                    ? 'bg-[var(--primary)] text-white border-transparent'
                    : 'bg-white text-[var(--text-muted)] border-stone-200'
                }`}
              >
                All
              </button>
              <button
                type="button"
                onClick={() => setFilter('frames')}
                className={`px-2.5 py-1 rounded-full border ${
                  filter === 'frames'
                    ? 'bg-[var(--primary)] text-white border-transparent'
                    : 'bg-white text-[var(--text-muted)] border-stone-200'
                }`}
              >
                Frames
              </button>
              <button
                type="button"
                onClick={() => setFilter('acks')}
                className={`px-2.5 py-1 rounded-full border ${
                  filter === 'acks'
                    ? 'bg-[var(--primary)] text-white border-transparent'
                    : 'bg-white text-[var(--text-muted)] border-stone-200'
                }`}
              >
                ACKs
              </button>
              <button
                type="button"
                onClick={() => setFilter('loss')}
                className={`px-2.5 py-1 rounded-full border ${
                  filter === 'loss'
                    ? 'bg-[var(--primary)] text-white border-transparent'
                    : 'bg-white text-[var(--text-muted)] border-stone-200'
                }`}
              >
                Loss & Timeouts
              </button>
              <button
                type="button"
                onClick={() => setFilter('lifecycle')}
                className={`px-2.5 py-1 rounded-full border ${
                  filter === 'lifecycle'
                    ? 'bg-[var(--primary)] text-white border-transparent'
                    : 'bg-white text-[var(--text-muted)] border-stone-200'
                }`}
              >
                Lifecycle
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setAutoScroll((v) => !v)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-white border border-stone-200 text-[var(--text-muted)] hover:text-[var(--text)]"
              >
                {autoScroll ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                {autoScroll ? 'Pause Feed' : 'Resume Feed'}
              </button>
            </div>
          </div>

          {/* Log Stream */}
          <div
            ref={scrollRef}
            className="h-64 overflow-y-auto rounded-xl border border-stone-200 bg-white p-2 font-mono text-xs space-y-1.5 scrollbar-thin"
          >
            {filteredEvents.length === 0 ? (
              <div className="text-center py-10 text-stone-400">No events match this filter.</div>
            ) : (
              filteredEvents.map((e) => {
                const time = new Date(e.timestamp).toLocaleTimeString('en-US', {
                  hour12: false,
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                  fractionalSecondDigits: 3,
                })

                return (
                  <div
                    key={e.event_id}
                    className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-stone-50 transition-colors"
                  >
                    <span className="text-[10px] text-stone-400 shrink-0 pt-0.5">{time}</span>
                    <span className="text-[10px] text-stone-400 shrink-0 pt-0.5 font-bold">
                      #{e.event_seq}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-tight uppercase shrink-0 border ${getEventBadgeClass(
                        e.event,
                      )}`}
                    >
                      {e.event}
                    </span>
                    <span className="text-stone-800 text-[11px] leading-snug break-all flex-1">
                      {formatNarrative(e)}
                    </span>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
