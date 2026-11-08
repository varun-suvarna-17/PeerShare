import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { cancelTransfer, getTransfer, getTransferReport } from '../api/transfers'
import { TransferProgressView } from '../components/transfer/TransferProgressView'
import { Button } from '../components/ui/Button'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { Spinner } from '../components/ui/Spinner'
import { ROUTES } from '../constants/routes'
import { useTransferEvents } from '../hooks/useTransferEvents'
import { useAppStore } from '../stores/appStore'
import { useConnectionStore } from '../stores/connectionStore'
import { useHistoryStore } from '../stores/historyStore'
import { useTransferStore } from '../stores/transferStore'
import { getErrorMessage } from '../utils/errors'

export function TransferProgressPage() {
  const { transferId } = useParams<{ transferId: string }>()
  useTransferEvents(transferId)

  const role = useAppStore((s) => s.role)
  const session = useConnectionStore((s) => s.session)
  const transfer = useTransferStore((s) => s.transfer)
  const progress = useTransferStore((s) => s.progress)
  const metrics = useTransferStore((s) => s.metrics)
  const events = useTransferStore((s) => s.recentEvents)
  const report = useTransferStore((s) => s.report)
  const startedAt = useTransferStore((s) => s.startedAt)
  const statusMessage = useTransferStore((s) => s.statusMessage)
  const error = useTransferStore((s) => s.error)
  const setTransfer = useTransferStore((s) => s.setTransfer)
  const setReport = useTransferStore((s) => s.setReport)
  const setError = useTransferStore((s) => s.setError)
  const setActiveTransferId = useTransferStore((s) => s.setActiveTransferId)
  const setStatusMessage = useTransferStore((s) => s.setStatusMessage)
  const addHistory = useHistoryStore((s) => s.addEntry)

  const [loading, setLoading] = useState(true)
  const [nowMs, setNowMs] = useState(() => performance.now() + performance.timeOrigin)
  const historySaved = useRef(false)

  useEffect(() => {
    const id = window.setInterval(() => {
      setNowMs(performance.now() + performance.timeOrigin)
    }, 1000)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    if (!transferId) return
    setActiveTransferId(transferId)
    void (async () => {
      try {
        const details = await getTransfer(transferId)
        setTransfer(details)
        setStatusMessage(`Status: ${details.status}`)
        if (details.status === 'completed' || details.status === 'failed') {
          try {
            setReport(await getTransferReport(transferId))
          } catch {
            // Report may be incomplete on failure.
          }
        }
      } catch (err) {
        setError(getErrorMessage(err, 'Could not load transfer'))
      } finally {
        setLoading(false)
      }
    })()
  }, [setActiveTransferId, setError, setReport, setStatusMessage, setTransfer, transferId])

  useEffect(() => {
    if (!transferId) return
    const id = window.setInterval(() => {
      void getTransfer(transferId)
        .then((details) => {
          setTransfer(details)
          if (details.status === 'completed' || details.status === 'failed') {
            void getTransferReport(transferId)
              .then(setReport)
              .catch(() => undefined)
          }
        })
        .catch(() => undefined)
    }, 2500)
    return () => window.clearInterval(id)
  }, [setReport, setTransfer, transferId])

  useEffect(() => {
    if (!transfer || !transferId || historySaved.current) return
    if (transfer.status !== 'completed' && transfer.status !== 'failed' && transfer.status !== 'cancelled') {
      return
    }
    historySaved.current = true
    addHistory({
      id: crypto.randomUUID(),
      transferId,
      fileName: transfer.file_name,
      fileSize: transfer.file_size ?? 0,
      role: role || 'SENDER',
      peerLabel: session?.peer_ip || 'Peer',
      protocol: transfer.protocol,
      status: transfer.status,
      integrityVerified: report?.integrity_verified ?? transfer.integrity_verified,
      completedAt: new Date().toISOString(),
    })
  }, [addHistory, report?.integrity_verified, role, session?.peer_ip, transfer, transferId])

  const handleCancel = async () => {
    if (!transferId) return
    try {
      await cancelTransfer(transferId)
      setStatusMessage('Cancellation requested')
    } catch (err) {
      setError(getErrorMessage(err, 'Could not cancel transfer'))
    }
  }

  if (!transferId) {
    return <ErrorBanner message="Missing transfer id" />
  }

  if (loading && !transfer) {
    return <Spinner label="Loading transfer…" />
  }

  const terminal =
    transfer?.status === 'completed' ||
    transfer?.status === 'failed' ||
    transfer?.status === 'cancelled'

  const senderLabel =
    role === 'RECEIVER'
      ? session?.peer_ip || 'Sender'
      : 'This Device (Sender)'

  const receiverLabel =
    role === 'RECEIVER'
      ? 'This Device (Receiver)'
      : session?.peer_ip || 'Receiver'

  return (
    <div className="space-y-6">
      {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

      <TransferProgressView
        transfer={transfer}
        progress={progress}
        metrics={metrics}
        events={events}
        report={report}
        startedAt={startedAt}
        nowMs={nowMs}
        statusMessage={statusMessage}
        senderLabel={senderLabel}
        receiverLabel={receiverLabel}
      />

      <div className="flex flex-wrap gap-3 pt-2">
        {!terminal ? (
          <Button variant="danger" onClick={() => void handleCancel()}>
            Cancel transfer
          </Button>
        ) : null}
        <Link to={ROUTES.home}>
          <Button variant="secondary">Dashboard</Button>
        </Link>
        <Link to={ROUTES.history}>
          <Button variant="ghost">View history</Button>
        </Link>
      </div>
    </div>
  )
}
