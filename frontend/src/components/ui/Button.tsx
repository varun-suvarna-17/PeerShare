import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost'
type Size = 'md' | 'lg' | 'sm'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  children: ReactNode
  fullWidth?: boolean
}

const variants: Record<Variant, string> = {
  primary:
    'bg-[var(--primary)] text-white hover:opacity-90 disabled:opacity-40 focus-visible:ring-[var(--primary)]',
  secondary:
    'bg-[var(--surface-muted)] text-[var(--text)] border border-[var(--border-muted)] hover:bg-[var(--bg-dark)] disabled:opacity-40 focus-visible:ring-[var(--border)]',
  danger:
    'bg-[var(--danger)] text-white hover:opacity-90 disabled:opacity-40 focus-visible:ring-[var(--danger)]',
  ghost:
    'bg-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-muted)] disabled:opacity-40 focus-visible:ring-[var(--border)]',
}

const sizes: Record<Size, string> = {
  sm: 'h-9 px-4 text-sm',
  md: 'h-11 px-5 text-sm',
  lg: 'h-13 px-7 text-base min-h-12',
}

export function Button({
  variant = 'primary',
  size = 'md',
  fullWidth,
  className = '',
  children,
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
