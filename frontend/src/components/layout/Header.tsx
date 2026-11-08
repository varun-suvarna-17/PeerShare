import { Clock, Settings, WifiOff } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'
import { useAppStore } from '../../stores/appStore'
import { useConnectionStore } from '../../stores/connectionStore'
import { BrandLogo } from './BrandLogo'

export function Header() {
  const location = useLocation()
  const network = useAppStore((s) => s.network)
  const backendOnline = useAppStore((s) => s.backendOnline)
  const session = useConnectionStore((s) => s.session)

  return (
    <header className="w-full px-6 pt-6 pb-2 md:px-12 md:pt-8">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
        <BrandLogo />

        {/* Right Actions */}
        <div className="flex items-center gap-3">
          {session ? (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1 rounded-full bg-emerald-100/80 text-emerald-900 border border-emerald-300 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span>Peer: {session.peer_ip}</span>
            </span>
          ) : null}

          {backendOnline === false ? (
            <Link
              to={ROUTES.settings}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-100 text-rose-800 border border-rose-300 text-xs font-medium"
            >
              <WifiOff className="w-3.5 h-3.5" />
              <span>Offline</span>
            </Link>
          ) : network ? (
            <Link
              to={ROUTES.settings}
              title="Backend Diagnostics"
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--bg-light)] text-[var(--text)] border border-[var(--border)] text-xs font-medium hover:border-[var(--primary)] transition"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-mono">{network.local_ip}</span>
            </Link>
          ) : null}

          {/* History link matching mockup */}
          <Link
            to={ROUTES.history}
            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-semibold transition ${
              location.pathname === ROUTES.history
                ? 'bg-[var(--primary)] text-white shadow-xs'
                : 'text-[var(--text)] hover:bg-[var(--bg-light)]'
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>History</span>
          </Link>

          <Link
            to={ROUTES.settings}
            title="Settings"
            className="p-2 rounded-full text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--bg-light)] transition"
            aria-label="Settings"
          >
            <Settings className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </header>
  )
}
