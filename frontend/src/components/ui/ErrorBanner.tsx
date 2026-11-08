import { AlertCircle } from 'lucide-react'

interface ErrorBannerProps {
  message: string
  onDismiss?: () => void
}

export function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-2xl border border-[color-mix(in_oklch,var(--danger)_35%,white)] bg-[color-mix(in_oklch,var(--danger)_10%,white)] px-4 py-3 text-sm text-[var(--danger)]"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <p className="flex-1">{message}</p>
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-full px-2 text-xs font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--danger)]"
        >
          Dismiss
        </button>
      ) : null}
    </div>
  )
}
