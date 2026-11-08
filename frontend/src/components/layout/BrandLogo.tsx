import { Link } from 'react-router-dom'
import { ROUTES } from '../../constants/routes'

interface BrandLogoProps {
  compact?: boolean
}

export function BrandLogo({ compact = false }: BrandLogoProps) {
  return (
    <Link to={ROUTES.home} className="inline-flex items-center gap-3 group focus-visible:outline-none">
      <span
        className={`inline-flex items-center justify-center rounded-full bg-[var(--primary)] text-white shadow-sm transition-transform duration-200 group-hover:scale-105 ${
          compact ? 'h-9 w-9' : 'h-11 w-11'
        }`}
        aria-hidden
      >
        <svg
          viewBox="0 0 24 24"
          className={compact ? 'h-5 w-5' : 'h-6 w-6'}
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M7 8h10M17 8l-3-3M17 8l-3 3" />
          <path d="M17 16H7M7 16l3-3M7 16l3 3" />
        </svg>
      </span>
      <span
        className={`font-bold tracking-tight text-[var(--text)] transition-opacity duration-200 group-hover:opacity-90 ${
          compact ? 'text-xl' : 'text-2xl'
        }`}
      >
        PeerShare
      </span>
    </Link>
  )
}
