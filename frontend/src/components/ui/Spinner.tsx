interface SpinnerProps {
  label?: string
  className?: string
}

export function Spinner({ label = 'Loading', className = '' }: SpinnerProps) {
  return (
    <div className={`inline-flex items-center gap-2 text-sm text-[var(--text-muted)] ${className}`} role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--border-muted)] border-t-[var(--primary)]" />
      {label ? <span>{label}</span> : <span className="sr-only">Loading</span>}
    </div>
  )
}
