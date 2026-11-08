import { useEffect } from 'react'
import { ArrowDown, ArrowUp, ShieldCheck } from 'lucide-react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { ROUTES, transferPath } from '../constants/routes'
import { PROTOCOL_LABELS } from '../constants/protocols'
import { useAppStore } from '../stores/appStore'
import { useHistoryStore } from '../stores/historyStore'
import { formatBytes } from '../utils/format'

export function HomePage() {
  const network = useAppStore((s) => s.network)
  const networkError = useAppStore((s) => s.networkError)
  const entries = useHistoryStore((s) => s.entries)
  const hydrate = useHistoryStore((s) => s.hydrate)

  useEffect(() => {
    hydrate()
  }, [hydrate])

  const recentEntries = entries.slice(0, 3)

  return (
    <div className="mx-auto max-w-4xl flex flex-col items-center justify-center min-h-[calc(100vh-140px)] py-8 space-y-12">
      {/* Central Heading */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="text-center"
      >
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight text-[var(--text)]">
          What would you like to do?
        </h1>
        {network && (
          <p className="mt-3 text-xs sm:text-sm text-[var(--text-muted)] flex items-center justify-center gap-1.5 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
            <span>Ready on {network.local_ip} · {network.device_name}</span>
          </p>
        )}
        {networkError && (
          <p className="mt-2 text-xs text-[var(--danger)]">{networkError}</p>
        )}
      </motion.div>

      {/* Two Large Circular Action Buttons matching reference mockup */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-12 sm:gap-16 md:gap-24 w-full">
        {/* Send Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          className="flex flex-col items-center text-center group"
        >
          <Link to={ROUTES.send} className="focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--primary)] rounded-full">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.96 }}
              className="w-36 h-36 md:w-44 md:h-44 rounded-full bg-[var(--primary)] text-white flex items-center justify-center shadow-lg transition-shadow duration-200 group-hover:shadow-2xl relative"
            >
              <div className="absolute inset-0 rounded-full border-4 border-white/20" />
              <ArrowUp className="w-14 h-14 md:w-16 md:h-16 stroke-[2.75]" />
            </motion.div>
          </Link>
          <h2 className="mt-5 text-xl md:text-2xl font-bold text-[var(--text)] tracking-tight">
            Send
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)] max-w-[200px]">
            Share files with another laptop
          </p>
        </motion.div>

        {/* Receive Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.15 }}
          className="flex flex-col items-center text-center group"
        >
          <Link to={ROUTES.receive} className="focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[var(--secondary)] rounded-full">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.96 }}
              className="w-36 h-36 md:w-44 md:h-44 rounded-full bg-[var(--secondary)] text-white flex items-center justify-center shadow-lg transition-shadow duration-200 group-hover:shadow-2xl relative"
            >
              <div className="absolute inset-0 rounded-full border-4 border-white/20" />
              <ArrowDown className="w-14 h-14 md:w-16 md:h-16 stroke-[2.75]" />
            </motion.div>
          </Link>
          <h2 className="mt-5 text-xl md:text-2xl font-bold text-[var(--text)] tracking-tight">
            Receive
          </h2>
          <p className="mt-1 text-sm text-[var(--text-muted)] max-w-[200px]">
            Get files from another laptop
          </p>
        </motion.div>
      </div>

      {/* Recent Transfers (if any) */}
      {recentEntries.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          className="w-full max-w-xl pt-6 border-t border-[var(--border)]"
        >
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="text-xs uppercase font-bold tracking-wider text-[var(--text-muted)]">
              Recent Transfers
            </span>
            <Link to={ROUTES.history} className="text-xs font-semibold text-[var(--primary)] hover:underline">
              View all ({entries.length})
            </Link>
          </div>

          <div className="space-y-2">
            {recentEntries.map((entry) => (
              <Link
                key={entry.id}
                to={transferPath(entry.transferId)}
                className="flex items-center justify-between p-3.5 rounded-2xl bg-[var(--bg-light)] border border-[var(--border)] hover:border-[var(--primary)] transition shadow-2xs"
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--text)]">{entry.fileName}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {entry.role === 'SENDER' ? 'Sent' : 'Received'} · {formatBytes(entry.fileSize)} ·{' '}
                    {PROTOCOL_LABELS[entry.protocol] || entry.protocol}
                  </p>
                </div>
                {entry.integrityVerified && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-emerald-800 bg-emerald-100/70 px-2.5 py-0.5 rounded-full border border-emerald-300">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                    Verified
                  </span>
                )}
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  )
}
