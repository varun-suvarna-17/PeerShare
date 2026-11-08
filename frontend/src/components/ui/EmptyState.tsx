import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: ReactNode
  action?: ReactNode
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--border-muted)] bg-[var(--surface-muted)] px-6 py-14 text-center">
      {icon ? <div className="mb-4 text-[var(--text-muted)]">{icon}</div> : null}
      <h3 className="text-lg font-semibold text-[var(--text)]">{title}</h3>
      {description ? (
        <p className="mt-2 max-w-md text-sm text-[var(--text-muted)]">{description}</p>
      ) : null}
      {action ? <div className="mt-6">{action}</div> : null}
    </div>
  )
}
