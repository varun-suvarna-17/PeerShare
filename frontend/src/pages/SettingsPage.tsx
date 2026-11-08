import { useState } from 'react'
import { CheckCircle2, Network, Server, Settings, Trash2 } from 'lucide-react'
import { getApiBaseUrl, setApiBaseUrl } from '../api/client'
import { getNetworkStatus } from '../api/network'
import { endSession } from '../api/session'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { useAppStore } from '../stores/appStore'
import { useConnectionStore } from '../stores/connectionStore'
import { useHistoryStore } from '../stores/historyStore'
import { getErrorMessage } from '../utils/errors'

export function SettingsPage() {
  const network = useAppStore((s) => s.network)
  const setNetwork = useAppStore((s) => s.setNetwork)
  const setBackendOnline = useAppStore((s) => s.setBackendOnline)
  const session = useConnectionStore((s) => s.session)
  const resetConnection = useConnectionStore((s) => s.resetConnection)
  const clearHistory = useHistoryStore((s) => s.clear)

  const [apiUrl, setApiUrlState] = useState(() => getApiBaseUrl())
  const [testing, setTesting] = useState(false)
  const [testSuccess, setTestSuccess] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [resetSuccess, setResetSuccess] = useState<string | null>(null)

  const handleSaveAndTest = async (targetUrl?: string) => {
    const urlToTest = targetUrl || apiUrl
    setTesting(true)
    setError(null)
    setTestSuccess(null)
    try {
      setApiBaseUrl(urlToTest)
      setApiUrlState(urlToTest)
      const status = await getNetworkStatus()
      setNetwork(status)
      setBackendOnline(true)
      setTestSuccess(`Connected successfully to ${status.device_name} (${status.local_ip})`)
    } catch (err) {
      setBackendOnline(false)
      setError(getErrorMessage(err, 'Failed to connect to backend at ' + urlToTest))
    } finally {
      setTesting(false)
    }
  }

  const handleClearSession = async () => {
    try {
      await endSession().catch(() => undefined)
      resetConnection()
      setResetSuccess('Active session cleared.')
      setTimeout(() => setResetSuccess(null), 3000)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to clear session'))
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold italic text-[var(--text)] flex items-center gap-2.5">
          <Settings className="w-7 h-7 text-[var(--primary)]" />
          Settings & Diagnostics
        </h1>
        <p className="mt-2 text-[var(--text-muted)]">
          Configure backend API endpoints, inspect device networking parameters, and manage local data.
        </p>
      </div>

      {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}
      {testSuccess ? (
        <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{testSuccess}</span>
        </div>
      ) : null}
      {resetSuccess ? (
        <div className="rounded-2xl border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          <span>{resetSuccess}</span>
        </div>
      ) : null}

      {/* Backend API Target */}
      <section className="space-y-4 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
        <h2 className="text-base font-semibold text-[var(--text)] flex items-center gap-2">
          <Server className="w-5 h-5 text-[var(--primary)]" />
          Backend Server Endpoint
        </h2>
        <p className="text-xs text-[var(--text-muted)]">
          Target URL for backend REST API and WebSocket events. Change this when testing two backend
          instances (e.g. Sender on port 8000, Receiver on port 8001) on the same machine.
        </p>

        <div className="space-y-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={apiUrl}
              onChange={(e) => setApiUrlState(e.target.value)}
              placeholder="http://127.0.0.1:8000"
              className="flex-1 rounded-xl border border-[var(--border-muted)] bg-[var(--surface-muted)] px-3.5 py-2 text-sm font-mono text-[var(--text)] focus:border-[var(--primary)] focus:outline-none"
            />
            <Button
              onClick={() => void handleSaveAndTest()}
              disabled={testing || !apiUrl.trim()}
              size="md"
            >
              {testing ? 'Testing…' : 'Save & Test'}
            </Button>
          </div>

          {/* Quick Presets */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-[var(--text-muted)]">Single-machine presets:</span>
            <button
              type="button"
              onClick={() => void handleSaveAndTest('http://127.0.0.1:8000')}
              className="px-2.5 py-1 rounded-full bg-[var(--surface-muted)] border border-[var(--border-muted)] hover:border-[var(--border)] font-mono text-[11px]"
            >
              Instance A (:8000)
            </button>
            <button
              type="button"
              onClick={() => void handleSaveAndTest('http://127.0.0.1:8001')}
              className="px-2.5 py-1 rounded-full bg-[var(--surface-muted)] border border-[var(--border-muted)] hover:border-[var(--border)] font-mono text-[11px]"
            >
              Instance B (:8001)
            </button>
          </div>
        </div>
      </section>

      {/* Device & Network Diagnostics */}
      <section className="space-y-4 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
        <h2 className="text-base font-semibold text-[var(--text)] flex items-center gap-2">
          <Network className="w-5 h-5 text-[var(--primary)]" />
          Connected Backend Diagnostics
        </h2>

        {network ? (
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">Device Name</span>
              <strong className="text-sm text-[var(--text)]">{network.device_name}</strong>
            </div>
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">Current Role</span>
              <strong className="text-sm text-[var(--text)]">{network.role}</strong>
            </div>
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">Local IP Address</span>
              <strong className="text-sm font-mono text-[var(--text)]">{network.local_ip}</strong>
            </div>
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">REST API Port</span>
              <strong className="text-sm font-mono text-[var(--text)]">{network.api_port}</strong>
            </div>
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">UDP Transport Port</span>
              <strong className="text-sm font-mono text-[var(--text)]">{network.udp_port}</strong>
            </div>
            <div className="p-3 rounded-xl bg-white/70">
              <span className="text-[var(--text-muted)] block">Device ID</span>
              <strong className="text-[11px] font-mono text-[var(--text)] truncate block">
                {network.device_id}
              </strong>
            </div>
          </div>
        ) : (
          <p className="text-xs text-[var(--text-muted)]">
            No backend connected. Check that your FastAPI backend is running.
          </p>
        )}
      </section>

      {/* Session & Data Management */}
      <section className="space-y-4 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
        <h2 className="text-base font-semibold text-[var(--text)] flex items-center gap-2">
          <Trash2 className="w-5 h-5 text-[var(--danger)]" />
          State & Session Management
        </h2>

        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--surface-muted)]">
            <div>
              <p className="text-xs font-semibold text-[var(--text)]">Active Peer Session</p>
              <p className="text-[11px] text-[var(--text-muted)]">
                {session ? `Connected to ${session.peer_ip}` : 'No active session'}
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void handleClearSession()}
              disabled={!session}
            >
              Disconnect Session
            </Button>
          </div>

          <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--surface-muted)]">
            <div>
              <p className="text-xs font-semibold text-[var(--text)]">Transfer History</p>
              <p className="text-[11px] text-[var(--text-muted)]">Clear all saved transfer records</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => clearHistory()}>
              Clear History
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}
