import type { ReactNode } from 'react'
import { Header } from './Header'

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col">
      <Header />
      <main className="flex-1 mx-auto w-full max-w-5xl px-4 py-8 md:px-8 md:py-10">
        {children}
      </main>
    </div>
  )
}
