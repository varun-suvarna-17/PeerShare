import { useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AlertCircle, ArrowLeft, ArrowRight, Laptop, Radio, Server } from 'lucide-react'
import type { FlyingPacket, NetworkMetrics } from '../../types/events'
import { useTransferStore } from '../../stores/transferStore'

interface PacketFlowVisualizerProps {
  metrics: NetworkMetrics
  senderLabel?: string
  receiverLabel?: string
  protocolName?: string
}

function PacketItem({ packet }: { packet: FlyingPacket }) {
  const isToReceiver = packet.direction === 'to_receiver'

  // Determine styling and label based on packet type
  let badgeColor = 'bg-[var(--primary)] text-white border-transparent'
  let label = `Frame #${packet.frameIndex ?? 0}`
  let isDrop = false

  if (packet.type === 'RETRANSMIT') {
    badgeColor = 'bg-[var(--warning)] text-[var(--text)] border-amber-500 font-semibold'
    label = `Retransmit #${packet.frameIndex ?? 0}`
  } else if (packet.type === 'LOST_FRAME') {
    badgeColor = 'bg-[var(--danger)] text-white border-red-600'
    label = `Dropped Frame #${packet.frameIndex ?? 0}`
    isDrop = true
  } else if (packet.type === 'CORRUPTED') {
    badgeColor = 'bg-purple-700 text-white border-purple-800'
    label = `CRC Corrupt #${packet.frameIndex ?? 0}`
  } else if (packet.type === 'ACK') {
    badgeColor = 'bg-[var(--success)] text-white border-green-600'
    label = `ACK #${packet.frameIndex ?? packet.ackNumber ?? 0}`
  } else if (packet.type === 'LOST_ACK') {
    badgeColor = 'bg-[var(--danger)] text-white border-red-600'
    label = `Lost ACK #${packet.frameIndex ?? 0}`
    isDrop = true
  }

  // Animation values:
  // If to_receiver: starts at 5%, goes to 92% (or stops at 48% if drop)
  // If to_sender: starts at 92%, goes to 5% (or stops at 48% if drop)
  const initialX = isToReceiver ? '5%' : '90%'
  const targetX = isDrop ? '48%' : isToReceiver ? '90%' : '5%'

  return (
    <motion.div
      key={packet.id}
      initial={{ left: initialX, opacity: 0, scale: 0.8 }}
      animate={{
        left: targetX,
        opacity: isDrop ? [0, 1, 1, 0] : [0, 1, 1, 0.9],
        scale: isDrop ? [0.8, 1.1, 1, 0.4] : 1,
      }}
      transition={{
        duration: isDrop ? 1.6 : 2.2,
        ease: 'easeInOut',
      }}
      className={`absolute top-1/2 -translate-y-1/2 z-10 flex items-center gap-1.5 px-3 py-1 rounded-full text-xs shadow-md border pointer-events-none whitespace-nowrap ${badgeColor}`}
    >
      {isDrop ? (
        <AlertCircle className="w-3.5 h-3.5 shrink-0 animate-bounce" />
      ) : (
        <Radio className="w-3 h-3 shrink-0" />
      )}
      <span>{label}</span>
      {packet.sequenceNumber !== undefined && (
        <span className="opacity-80 text-[10px] ml-0.5">seq {packet.sequenceNumber}</span>
      )}
    </motion.div>
  )
}

export function PacketFlowVisualizer({
  metrics,
  senderLabel = 'Sender Laptop',
  receiverLabel = 'Receiver Laptop',
  protocolName,
}: PacketFlowVisualizerProps) {
  const cleanExpiredPackets = useTransferStore((s) => s.cleanExpiredPackets)

  useEffect(() => {
    const timer = setInterval(() => {
      cleanExpiredPackets()
    }, 1000)
    return () => clearInterval(timer)
  }, [cleanExpiredPackets])

  const hasRecentTimeout = metrics.recentTimeouts.length > 0
  const dataPackets = metrics.flyingPackets.filter((p) => p.direction === 'to_receiver')
  const ackPackets = metrics.flyingPackets.filter((p) => p.direction === 'to_sender')

  return (
    <div className="rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-5 md:p-6 shadow-xs overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)] flex items-center gap-2">
            <Radio className="w-5 h-5 text-[var(--primary)] animate-pulse" />
            Live Packet Transmission Channel
          </h2>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">
            Real UDP datagrams & ACK frames tracked from backend WebSocket events
          </p>
        </div>
        {protocolName && (
          <span className="px-3 py-1 rounded-full bg-[var(--surface-muted)] text-xs font-medium text-[var(--text)] border border-[var(--border-muted)]">
            {protocolName}
          </span>
        )}
      </div>

      {/* Main Flow Stage */}
      <div className="relative grid grid-cols-12 gap-2 items-center py-4 px-2 bg-[var(--surface-muted)] rounded-2xl border border-[var(--border-muted)]">
        {/* SENDER NODE */}
        <div className="col-span-3 flex flex-col items-center text-center p-3 rounded-xl bg-white border border-[var(--border-muted)] shadow-xs relative transition-all">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-colors ${
              hasRecentTimeout
                ? 'bg-red-100 text-[var(--danger)] ring-4 ring-red-200 animate-pulse'
                : 'bg-[color-mix(in_oklch,var(--primary)_15%,white)] text-[var(--primary)]'
            }`}
          >
            <Laptop className="w-6 h-6" />
          </div>
          <span className="mt-2 text-xs font-semibold text-[var(--text)] truncate max-w-full">
            {senderLabel}
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--primary)] mt-0.5">
            Sender
          </span>
          <div className="mt-2 w-full pt-2 border-t border-[var(--border-muted)] flex justify-around text-[10px] text-[var(--text-muted)]">
            <div>
              <span className="block font-semibold text-[var(--text)]">{metrics.framesSent}</span>
              Sent
            </div>
            <div>
              <span className="block font-semibold text-[var(--text)]">
                {metrics.retransmissions}
              </span>
              Retries
            </div>
          </div>
          {hasRecentTimeout && (
            <div className="absolute -top-2 left-1/2 -translate-x-1/2 bg-[var(--danger)] text-white text-[10px] px-2 py-0.5 rounded-full font-bold shadow-xs whitespace-nowrap flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> Timeout!
            </div>
          )}
        </div>

        {/* CHANNEL LANES (CENTER) */}
        <div className="col-span-6 flex flex-col justify-center gap-6 relative px-1 h-36">
          {/* Data Track (Left to Right) */}
          <div className="relative h-14 bg-white/70 rounded-xl border border-dashed border-[var(--border-muted)] flex items-center px-3">
            <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 h-0.5 bg-gradient-to-r from-[var(--primary)] via-blue-300 to-[var(--primary)] opacity-30" />
            <div className="absolute top-1 left-3 text-[10px] font-medium text-[var(--text-muted)] flex items-center gap-1">
              <span>Data Channel (UDP)</span>
              <ArrowRight className="w-3 h-3 text-[var(--primary)]" />
            </div>

            {/* Flying Data Packets */}
            <AnimatePresence>
              {dataPackets.map((pkt) => (
                <PacketItem key={pkt.id} packet={pkt} />
              ))}
            </AnimatePresence>

            {dataPackets.length === 0 && (
              <span className="text-[11px] text-[var(--text-muted)] italic mx-auto opacity-60">
                Channel idle
              </span>
            )}
          </div>

          {/* ACK Track (Right to Left) */}
          <div className="relative h-14 bg-white/70 rounded-xl border border-dashed border-[var(--border-muted)] flex items-center px-3">
            <div className="absolute inset-x-4 top-1/2 -translate-y-1/2 h-0.5 bg-gradient-to-l from-[var(--success)] via-emerald-300 to-[var(--success)] opacity-30" />
            <div className="absolute top-1 right-3 text-[10px] font-medium text-[var(--text-muted)] flex items-center gap-1">
              <ArrowLeft className="w-3 h-3 text-[var(--success)]" />
              <span>ACK Feedback</span>
            </div>

            {/* Flying ACK Packets */}
            <AnimatePresence>
              {ackPackets.map((pkt) => (
                <PacketItem key={pkt.id} packet={pkt} />
              ))}
            </AnimatePresence>

            {ackPackets.length === 0 && (
              <span className="text-[11px] text-[var(--text-muted)] italic mx-auto opacity-60">
                Awaiting ACKs
              </span>
            )}
          </div>
        </div>

        {/* RECEIVER NODE */}
        <div className="col-span-3 flex flex-col items-center text-center p-3 rounded-xl bg-white border border-[var(--border-muted)] shadow-xs relative">
          <div className="w-12 h-12 rounded-full bg-[color-mix(in_oklch,var(--secondary)_15%,white)] text-[var(--secondary)] flex items-center justify-center">
            <Server className="w-6 h-6" />
          </div>
          <span className="mt-2 text-xs font-semibold text-[var(--text)] truncate max-w-full">
            {receiverLabel}
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-[var(--secondary)] mt-0.5">
            Receiver
          </span>
          <div className="mt-2 w-full pt-2 border-t border-[var(--border-muted)] flex justify-around text-[10px] text-[var(--text-muted)]">
            <div>
              <span className="block font-semibold text-[var(--text)]">
                {metrics.framesReceived}
              </span>
              Received
            </div>
            <div>
              <span className="block font-semibold text-[var(--text)]">{metrics.acksSent}</span>
              ACKs
            </div>
          </div>
        </div>
      </div>

      {/* Visual Legend */}
      <div className="mt-4 pt-3 border-t border-[var(--border-muted)] flex flex-wrap items-center justify-between text-xs text-[var(--text-muted)] gap-3">
        <span className="font-medium text-[var(--text)]">Legend:</span>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--primary)]" />
            <span>Data Frame</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--warning)]" />
            <span>Retransmission</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--success)]" />
            <span>ACK</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--danger)]" />
            <span>Simulated Loss</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-purple-700" />
            <span>CRC Corruption</span>
          </div>
        </div>
      </div>
    </div>
  )
}
