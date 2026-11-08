import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
  approveConnection,
  generatePin,
  listPendingConnections,
  rejectConnection,
} from '../api/devices'
import { setRole } from '../api/network'
import { getSession } from '../api/session'
import { acceptTransfer, listPendingTransfers, rejectTransfer } from '../api/transfers'
import { ConnectionStatusPanel } from '../components/connection/ConnectionStatus'
import { PinDisplay } from '../components/connection/PinDisplay'
import { IncomingRequestCard } from '../components/transfer/IncomingRequestCard'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { Spinner } from '../components/ui/Spinner'
import { ROUTES, transferPath } from '../constants/routes'
import { useAppStore } from '../stores/appStore'
import { useConnectionStore } from '../stores/connectionStore'
import { useTransferStore } from '../stores/transferStore'
import { getErrorMessage } from '../utils/errors'

export function ReceivePage() {
  const navigate = useNavigate()
  const setRoleStore = useAppStore((s) => s.setRole)
  const network = useAppStore((s) => s.network)
  const {
    phase,
    pinInfo,
    pinGeneratedAt,
    pendingConnections,
    session,
    error,
    setPhase,
    setPinInfo,
    setPinGeneratedAt,
    setPendingConnections,
    setSession,
    setError,
  } = useConnectionStore()
  const pendingTransfers = useTransferStore((s) => s.pendingTransfers)
  const setPendingTransfers = useTransferStore((s) => s.setPendingTransfers)
  const setActiveTransferId = useTransferStore((s) => s.setActiveTransferId)
  const setTransfer = useTransferStore((s) => s.setTransfer)
  const markStarted = useTransferStore((s) => s.markStarted)
  const setStatusMessage = useTransferStore((s) => s.setStatusMessage)

  const [busy, setBusy] = useState(false)
  const [ready, setReady] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  const remainingSeconds = useMemo(() => {
    if (!pinInfo || pinGeneratedAt == null) return null
    return Math.max(0, pinInfo.expires_in - elapsedSeconds)
  }, [elapsedSeconds, pinGeneratedAt, pinInfo])

  const refreshPin = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const info = await generatePin()
      setPinInfo(info)
      setPinGeneratedAt(Date.now())
      setElapsedSeconds(0)
    } catch (err) {
      setError(getErrorMessage(err, 'Could not generate PIN'))
    } finally {
      setBusy(false)
    }
  }, [setError, setPinGeneratedAt, setPinInfo])

  const bootstrap = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      await setRole('RECEIVER')
      setRoleStore('RECEIVER')
      setPhase('discovering')
      await refreshPin()
      const sess = await getSession()
      if (sess) {
        setSession(sess)
        setPhase('connected')
      } else {
        setPhase('idle')
      }
      setReady(true)
    } catch (err) {
      setPhase('failed')
      setError(getErrorMessage(err, 'Could not start receiver mode'))
    } finally {
      setBusy(false)
    }
  }, [refreshPin, setError, setPhase, setRoleStore, setSession])

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  useEffect(() => {
    if (pinGeneratedAt == null) return
    const tick = window.setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - pinGeneratedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(tick)
  }, [pinGeneratedAt])

  useEffect(() => {
    if (!ready) return
    const poll = window.setInterval(() => {
      void (async () => {
        try {
          const [connections, transfers, sess] = await Promise.all([
            listPendingConnections(),
            listPendingTransfers(),
            getSession(),
          ])
          setPendingConnections(connections)
          setPendingTransfers(transfers)
          if (sess) {
            setSession(sess)
            setPhase('connected')
          }
          if (connections.length > 0 && !sess) setPhase('awaiting_approval')
        } catch {
          // Keep UI resilient while backend is momentarily unavailable.
        }
      })()
    }, 2000)
    return () => window.clearInterval(poll)
  }, [ready, setPendingConnections, setPendingTransfers, setPhase, setSession])

  const handleApprove = async (connectionId: string) => {
    setBusy(true)
    setError(null)
    try {
      await approveConnection(connectionId)
      setPendingConnections(pendingConnections.filter((c) => c.connection_id !== connectionId))
      setStatusMessage('Connection approved — waiting for sender to establish session…')
      setPhase('establishing')
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to approve connection'))
    } finally {
      setBusy(false)
    }
  }

  const handleRejectConnection = async (connectionId: string) => {
    setBusy(true)
    try {
      await rejectConnection(connectionId)
      setPendingConnections(pendingConnections.filter((c) => c.connection_id !== connectionId))
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to reject connection'))
    } finally {
      setBusy(false)
    }
  }

  const handleAcceptTransfer = async (transferId: string) => {
    setBusy(true)
    setError(null)
    try {
      const pending = pendingTransfers.find((t) => t.transfer_id === transferId)
      await acceptTransfer(transferId)
      setActiveTransferId(transferId)
      setTransfer(
        pending
          ? {
              transfer_id: pending.transfer_id,
              file_name: pending.file_name,
              file_size: pending.file_size,
              protocol: pending.protocol,
              status: 'accepted',
            }
          : {
              transfer_id: transferId,
              file_name: 'Incoming file',
              protocol: 'selective_repeat',
              status: 'accepted',
            },
      )
      markStarted()
      setStatusMessage('Transfer accepted — waiting for sender to start…')
      setPendingTransfers(pendingTransfers.filter((t) => t.transfer_id !== transferId))
      navigate(transferPath(transferId))
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to accept transfer'))
    } finally {
      setBusy(false)
    }
  }

  const handleRejectTransfer = async (transferId: string) => {
    setBusy(true)
    try {
      await rejectTransfer(transferId)
      setPendingTransfers(pendingTransfers.filter((t) => t.transfer_id !== transferId))
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to reject transfer'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="flex items-start gap-4">
        <button
          type="button"
          onClick={() => navigate(ROUTES.home)}
          className="mt-1 p-2 rounded-full text-[var(--text)] hover:bg-[var(--bg-light)] transition focus-visible:outline-none"
          aria-label="Go back to Home"
        >
          <ArrowLeft className="w-6 h-6 stroke-[2.25]" />
        </button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--text)]">
            Receive Files
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            This laptop is advertising as a receiver on your local network.
          </p>
        </div>
      </div>

      <ConnectionStatusPanel
        phase={phase}
        detail={
          session
            ? `Session with ${session.peer_ip}`
            : network
              ? `Visible as ${network.device_name}`
              : null
        }
      />

      {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

      {!ready && busy ? <Spinner label="Starting receiver mode…" /> : null}

      <PinDisplay
        pinInfo={pinInfo}
        remainingSeconds={remainingSeconds}
        onRefresh={() => void refreshPin()}
        loading={busy}
      />

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Incoming connections</h2>
        {pendingConnections.length === 0 ? (
          <EmptyState
            title="Waiting for a sender"
            description="When someone connects via discovery or IP + PIN, their request will appear here for approval."
          />
        ) : (
          <ul className="space-y-3">
            {pendingConnections.map((connection) => (
              <li
                key={connection.connection_id}
                className="rounded-[20px] border border-[var(--border-muted)] bg-white p-5"
              >
                <p className="font-medium text-[var(--text)]">{connection.sender_device_name}</p>
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  {connection.sender_ip} · {connection.discovery_method}
                </p>
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button onClick={() => void handleApprove(connection.connection_id)} disabled={busy}>
                    Approve
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => void handleRejectConnection(connection.connection_id)}
                    disabled={busy}
                  >
                    Reject
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Incoming transfers</h2>
        {pendingTransfers.length === 0 ? (
          <EmptyState
            title={session ? 'No transfer requests yet' : 'Connect first'}
            description={
              session
                ? 'When the sender requests a file transfer, details will show here.'
                : 'Approve a connection before transfer requests can arrive.'
            }
          />
        ) : (
          pendingTransfers.map((transfer) => (
            <IncomingRequestCard
              key={transfer.transfer_id}
              transfer={transfer}
              busy={busy}
              onAccept={() => void handleAcceptTransfer(transfer.transfer_id)}
              onReject={() => void handleRejectTransfer(transfer.transfer_id)}
            />
          ))
        )}
      </section>
    </div>
  )
}
