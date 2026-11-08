import { useEffect, useRef, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { getConfig, listProtocols, updateConfig } from '../api/config'
import { getSession } from '../api/session'
import { requestTransfer, startTransfer } from '../api/transfers'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { Spinner } from '../components/ui/Spinner'
import { PROTOCOL_LABELS } from '../constants/protocols'
import { ROUTES, transferPath } from '../constants/routes'
import { useConnectionStore } from '../stores/connectionStore'
import { useFileStore } from '../stores/fileStore'
import { useTransferStore } from '../stores/transferStore'
import { getErrorMessage } from '../utils/errors'
import type { ProtocolId, ProtocolOption } from '../types/api'

export function ConfigureTransferPage() {
  const navigate = useNavigate()
  const primary = useFileStore((s) => s.files.find((f) => f.uploaded)?.uploaded ?? null)
  const session = useConnectionStore((s) => s.session)
  const setSession = useConnectionStore((s) => s.setSession)
  const protocol = useTransferStore((s) => s.protocol)
  const config = useTransferStore((s) => s.config)
  const setProtocol = useTransferStore((s) => s.setProtocol)
  const setConfig = useTransferStore((s) => s.setConfig)
  const setActiveTransferId = useTransferStore((s) => s.setActiveTransferId)
  const setTransfer = useTransferStore((s) => s.setTransfer)
  const setStatusMessage = useTransferStore((s) => s.setStatusMessage)
  const markStarted = useTransferStore((s) => s.markStarted)
  const resetTransferRuntime = useTransferStore((s) => s.resetTransferRuntime)

  const [protocols, setProtocols] = useState<ProtocolOption[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [waitingAccept, setWaitingAccept] = useState(false)
  const waitIntervalRef = useRef<number | null>(null)

  useEffect(
    () => () => {
      if (waitIntervalRef.current) window.clearInterval(waitIntervalRef.current)
    },
    [],
  )

  useEffect(() => {
    if (!primary) {
      navigate(ROUTES.send, { replace: true })
      return
    }
    if (!session) {
      navigate(ROUTES.sendConnect, { replace: true })
    }
  }, [navigate, primary, session])

  useEffect(() => {
    void (async () => {
      try {
        const [list, cfg] = await Promise.all([listProtocols(), getConfig(protocol)])
        setProtocols(list)
        setConfig({
          window_size: cfg.sender_window_size ?? cfg.window_size ?? 4,
          timeout_ms: cfg.timeout_ms,
          max_retries: cfg.max_retries,
          packet_loss_percentage: cfg.packet_loss_percentage,
          frame_delay_ms: cfg.frame_delay_ms,
        })
      } catch (err) {
        setError(getErrorMessage(err, 'Failed to load protocol settings'))
      }
    })()
  }, [protocol, setConfig])

  const onProtocolChange = async (next: ProtocolId) => {
    setProtocol(next)
    try {
      const cfg = await getConfig(next)
      setConfig({
        window_size: next === 'stop_and_wait' ? 1 : (cfg.sender_window_size ?? cfg.window_size ?? 4),
        timeout_ms: cfg.timeout_ms,
        max_retries: cfg.max_retries,
        packet_loss_percentage: cfg.packet_loss_percentage,
        frame_delay_ms: cfg.frame_delay_ms,
      })
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleSend = async () => {
    if (!primary) return
    setBusy(true)
    setError(null)
    resetTransferRuntime()
    try {
      const windowSize = protocol === 'stop_and_wait' ? 1 : config.window_size || 4
      await updateConfig(protocol, {
        window_size: windowSize,
        timeout_ms: config.timeout_ms,
        max_retries: config.max_retries,
        packet_loss_percentage: config.packet_loss_percentage,
        frame_delay_ms: config.frame_delay_ms,
      })

      const result = await requestTransfer({
        file_id: primary.file_id,
        protocol,
        configuration: {
          window_size: windowSize,
          timeout_ms: config.timeout_ms,
          max_retries: config.max_retries,
          packet_loss_percentage: config.packet_loss_percentage,
          frame_delay_ms: config.frame_delay_ms,
        },
      })

      setActiveTransferId(result.transfer_id)
      setTransfer({
        transfer_id: result.transfer_id,
        file_name: primary.file_name,
        file_size: primary.file_size,
        protocol,
        status: result.status,
      })
      setStatusMessage('Waiting for the receiver to accept…')
      setWaitingAccept(true)

      const started = await new Promise<boolean>((resolve, reject) => {
        let attempts = 0
        waitIntervalRef.current = window.setInterval(() => {
          void (async () => {
            attempts += 1
            try {
              const current = await getSession()
              if (current) setSession(current)
              if (current?.receiver_ready) {
                if (waitIntervalRef.current) window.clearInterval(waitIntervalRef.current)
                waitIntervalRef.current = null
                await startTransfer(result.transfer_id)
                markStarted()
                resolve(true)
              } else if (attempts > 90) {
                if (waitIntervalRef.current) window.clearInterval(waitIntervalRef.current)
                waitIntervalRef.current = null
                reject(new Error('Timed out waiting for receiver acceptance'))
              }
            } catch (err) {
              if (attempts > 90) {
                if (waitIntervalRef.current) window.clearInterval(waitIntervalRef.current)
                waitIntervalRef.current = null
                reject(err)
              }
            }
          })()
        }, 1500)
      })

      if (started) navigate(transferPath(result.transfer_id))
    } catch (err) {
      setError(getErrorMessage(err, 'Could not start transfer request'))
      setWaitingAccept(false)
    } finally {
      setBusy(false)
    }
  }

  const protocolOptions =
    protocols.length > 0
      ? protocols
      : (Object.keys(PROTOCOL_LABELS) as ProtocolId[]).map((id) => ({
          id,
          name: PROTOCOL_LABELS[id],
        }))

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={() => navigate(ROUTES.sendConnect)}
          className="mt-1 p-2 rounded-full text-[var(--text)] hover:bg-[var(--bg-light)] transition focus-visible:outline-none"
          aria-label="Go back to device connection"
        >
          <ArrowLeft className="w-6 h-6 stroke-[2.25]" />
        </button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text)]">
            Configure Transfer
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Connected to {session?.peer_ip || 'peer'}. Choose an ARQ protocol and simulation parameters.
          </p>
        </div>
      </div>

      {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

      <section className="space-y-3 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
        <h2 className="text-lg font-bold text-[var(--text)]">File to Transfer</h2>
        <p className="text-base font-semibold text-[var(--text)]">{primary?.file_name}</p>
        <p className="text-xs text-[var(--text-muted)] font-mono">
          {primary?.file_size != null ? `${primary.file_size} bytes` : ''} · {primary?.total_frames}{' '}
          frames
        </p>
      </section>

      <section className="space-y-4 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs">
        <h2 className="text-lg font-bold text-[var(--text)]">ARQ Protocol</h2>
        <div className="grid gap-3">
          {protocolOptions.map((option) => (
            <label
              key={option.id}
              className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3.5 transition ${
                protocol === option.id
                  ? 'border-[var(--primary)] bg-white ring-2 ring-[var(--primary)] shadow-xs'
                  : 'border-[var(--border)] bg-white/60 hover:border-[var(--primary)]'
              }`}
            >
              <input
                type="radio"
                name="protocol"
                checked={protocol === option.id}
                onChange={() => void onProtocolChange(option.id)}
                className="accent-[var(--primary)] w-4 h-4"
              />
              <span className="font-semibold text-sm text-[var(--text)]">{option.name}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="grid gap-4 rounded-[24px] border border-[var(--border)] bg-[var(--bg-light)] p-6 shadow-xs sm:grid-cols-2">
        <label className="text-sm">
          <span className="mb-1.5 block font-semibold text-xs text-[var(--text)]">Window Size (N)</span>
          <input
            type="number"
            min={1}
            disabled={protocol === 'stop_and_wait'}
            value={protocol === 'stop_and_wait' ? 1 : config.window_size || 4}
            onChange={(e) => setConfig({ window_size: Number(e.target.value) })}
            className="h-11 w-full rounded-xl border border-[var(--border)] bg-white px-4 font-mono outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1.5 block font-semibold text-xs text-[var(--text)]">Timeout (ms)</span>
          <input
            type="number"
            min={50}
            value={config.timeout_ms}
            onChange={(e) => setConfig({ timeout_ms: Number(e.target.value) })}
            className="h-11 w-full rounded-xl border border-[var(--border)] bg-white px-4 font-mono outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1.5 block font-semibold text-xs text-[var(--text)]">Max Retries</span>
          <input
            type="number"
            min={0}
            value={config.max_retries}
            onChange={(e) => setConfig({ max_retries: Number(e.target.value) })}
            className="h-11 w-full rounded-xl border border-[var(--border)] bg-white px-4 font-mono outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1.5 block font-semibold text-xs text-[var(--text)]">Simulated Loss (%)</span>
          <input
            type="number"
            min={0}
            max={100}
            step={1}
            value={config.packet_loss_percentage}
            onChange={(e) => setConfig({ packet_loss_percentage: Number(e.target.value) })}
            className="h-11 w-full rounded-xl border border-[var(--border)] bg-white px-4 font-mono outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
        <label className="text-sm sm:col-span-2">
          <span className="mb-1.5 block font-semibold text-xs text-[var(--text)]">Frame Delay Pacing (ms)</span>
          <input
            type="number"
            min={0}
            value={config.frame_delay_ms}
            onChange={(e) => setConfig({ frame_delay_ms: Number(e.target.value) })}
            className="h-11 w-full rounded-xl border border-[var(--border)] bg-white px-4 font-mono outline-none focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/20"
          />
        </label>
      </section>

      {waitingAccept ? (
        <Spinner label="Waiting for receiver to accept, then starting transfer…" />
      ) : null}

      <div className="flex justify-end">
        <Button size="lg" onClick={() => void handleSend()} disabled={busy || waitingAccept}>
          {busy || waitingAccept ? 'Working…' : 'Send transfer request'}
        </Button>
      </div>
    </div>
  )
}
