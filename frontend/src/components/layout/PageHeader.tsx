import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

interface PageHeaderProps {
  title: string
  subtitle?: string
  backTo?: string
}

export function PageHeader({ title, subtitle, backTo }: PageHeaderProps) {
  const navigate = useNavigate()

  return (
    <div className="mb-8">
      <div className="flex items-start gap-3">
        <button
          type="button"
          onClick={() => (backTo ? navigate(backTo) : navigate(-1))}
          className="mt-1 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-[var(--text)] transition hover:bg-[color-mix(in_oklch,var(--primary)_8%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]"
          aria-label="Go back"
        >
          <ArrowLeft className="h-5 w-5" strokeWidth={2.25} />
        </button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text)] md:text-[2rem]">
            {title}
          </h1>
          {subtitle ? <p className="mt-1 text-base text-[var(--text-muted)]">{subtitle}</p> : null}
        </div>
      </div>
    </div>
  )
}
