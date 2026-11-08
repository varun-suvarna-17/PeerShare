import { useState, type FormEvent } from 'react'
import { Button } from '../ui/Button'

interface ManualConnectFormProps {
  onSubmit: (values: { ip_address: string; pin: string; api_port: number }) => Promise<void> | void
  loading?: boolean
}

export function ManualConnectForm({ onSubmit, loading }: ManualConnectFormProps) {
  const [ip, setIp] = useState('127.0.0.1')
  const [pin, setPin] = useState('')
  const [port, setPort] = useState('8000')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    await onSubmit({
      ip_address: ip.trim(),
      pin: pin.trim(),
      api_port: Number(port) || 8000,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 rounded-[20px] border border-[var(--border-muted)] bg-white p-6">
      <div>
        <h3 className="text-lg font-semibold text-[var(--text)]">Connect with IP + PIN</h3>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Use this when Zeroconf discovery is blocked on the network.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1.5 block font-medium text-[var(--text)]">Receiver IP</span>
          <input
            required
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            className="h-11 w-full rounded-2xl border border-[var(--border-muted)] bg-white px-4 text-[var(--text)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-[color-mix(in_oklch,var(--primary)_25%,white)]"
            placeholder="192.168.1.12"
            autoComplete="off"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1.5 block font-medium text-[var(--text)]">API port</span>
          <input
            required
            value={port}
            onChange={(e) => setPort(e.target.value)}
            inputMode="numeric"
            className="h-11 w-full rounded-2xl border border-[var(--border-muted)] bg-white px-4 text-[var(--text)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-[color-mix(in_oklch,var(--primary)_25%,white)]"
            placeholder="8000"
          />
        </label>
      </div>

      <label className="block text-sm">
        <span className="mb-1.5 block font-medium text-[var(--text)]">6-digit PIN</span>
        <input
          required
          value={pin}
          onChange={(e) => setPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
          inputMode="numeric"
          pattern="\d{6}"
          maxLength={6}
          className="h-11 w-full rounded-2xl border border-[var(--border-muted)] bg-white px-4 font-mono tracking-[0.3em] text-[var(--text)] outline-none transition focus:border-[var(--primary)] focus:ring-2 focus:ring-[color-mix(in_oklch,var(--primary)_25%,white)]"
          placeholder="482193"
          autoComplete="one-time-code"
        />
      </label>

      <Button type="submit" disabled={loading || pin.length !== 6} fullWidth>
        {loading ? 'Connecting…' : 'Connect'}
      </Button>
    </form>
  )
}
