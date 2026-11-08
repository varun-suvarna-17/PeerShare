import type { ReactNode } from 'react'

interface StatusBadgeProps {
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'
  children: ReactNode
}

const tones: Record<NonNullable<StatusBadgeProps['tone']>, string> = {
  neutral: 'bg-[var(--surface-muted)] text-[var(--text-muted)]',
  success: 'bg-[color-mix(in_oklch,var(--success)_18%,white)] text-[var(--success)]',
  warning: 'bg-[color-mix(in_oklch,var(--warning)_18%,white)] text-[var(--warning)]',
  danger: 'bg-[color-mix(in_oklch,var(--danger)_18%,white)] text-[var(--danger)]',
  info: 'bg-[color-mix(in_oklch,var(--info)_18%,white)] text-[var(--info)]',
}

export function StatusBadge({ tone = 'neutral', children }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  )
}
