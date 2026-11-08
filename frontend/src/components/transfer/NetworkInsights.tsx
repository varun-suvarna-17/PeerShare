import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import type { NetworkMetrics, WsEvent } from '../../types/events'

interface NetworkInsightsProps {
  metrics: NetworkMetrics
  events: WsEvent[]
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl bg-[var(--surface-muted)] px-4 py-3">
      <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--text)]">{value}</p>
    </div>
  )
}

export function NetworkInsights({ metrics, events }: NetworkInsightsProps) {
  const [open, setOpen] = useState(false)
  const packetLoss =
    metrics.framesSent + metrics.framesLost > 0
      ? `${((metrics.framesLost / (metrics.framesSent + metrics.framesLost)) * 100).toFixed(1)}%`
      : 'Unavailable'

  return (
    <section className="rounded-[20px] border border-[var(--border-muted)] bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--primary)]"
        aria-expanded={open}
      >
        <div>
          <h3 className="text-base font-semibold text-[var(--text)]">Network Insights</h3>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Live ARQ metrics from backend events
          </p>
        </div>
        <ChevronDown
          className={`h-5 w-5 text-[var(--text-muted)] transition ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>

      {open ? (
        <div className="border-t border-[var(--border-muted)] px-5 py-5">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Metric label="Packets sent" value={metrics.framesSent} />
            <Metric label="Packets received" value={metrics.framesReceived} />
            <Metric label="ACKs sent" value={metrics.acksSent} />
            <Metric label="ACKs received" value={metrics.acksReceived} />
            <Metric label="Packet loss (sim)" value={packetLoss} />
            <Metric label="Retransmissions" value={metrics.retransmissions} />
            <Metric label="Timeouts" value={metrics.timeouts} />
            <Metric label="Buffered / discarded" value={`${metrics.framesBuffered} / ${metrics.framesDiscarded}`} />
          </div>

          <div className="mt-5 rounded-2xl bg-[var(--surface-muted)] px-4 py-3">
            <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Sliding window
            </p>
            <p className="mt-1 break-all font-mono text-sm text-[var(--text)]">
              {metrics.lastWindowUpdate
                ? JSON.stringify(metrics.lastWindowUpdate)
                : 'Unavailable — no WINDOW_UPDATED events yet'}
            </p>
          </div>

          <div className="mt-5">
            <p className="mb-2 text-sm font-medium text-[var(--text)]">Recent events</p>
            {events.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">No network events yet.</p>
            ) : (
              <ul className="max-h-56 space-y-2 overflow-y-auto text-sm">
                {events.slice(0, 20).map((event) => (
                  <li
                    key={event.event_id}
                    className="flex items-start justify-between gap-3 rounded-xl bg-[var(--surface-muted)] px-3 py-2"
                  >
                    <span className="font-medium text-[var(--text)]">{event.event}</span>
                    <span className="shrink-0 text-xs text-[var(--text-muted)]">
                      seq {event.event_seq}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </section>
  )
}
