export function formatBytes(bytes: number | undefined | null): string {
  if (bytes == null || Number.isNaN(bytes)) return '—'
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const value = bytes / 1024 ** i
  return `${value < 10 && i > 0 ? value.toFixed(1) : Math.round(value)} ${units[i]}`
}

export function formatSpeed(bytesPerSecond: number | undefined | null): string {
  if (bytesPerSecond == null || !Number.isFinite(bytesPerSecond) || bytesPerSecond <= 0) {
    return 'Unavailable'
  }
  return `${formatBytes(bytesPerSecond)}/s`
}

export function formatDuration(seconds: number | undefined | null): string {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return 'Unavailable'
  if (seconds < 1) return '<1s'
  const s = Math.round(seconds)
  const m = Math.floor(s / 60)
  const rem = s % 60
  if (m === 0) return `${rem}s`
  return `${m}m ${rem}s`
}

export function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function formatPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${Math.min(100, Math.max(0, Math.round(value)))}%`
}
