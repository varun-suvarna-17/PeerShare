import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowLeft, KeyRound, RefreshCw } from 'lucide-react'
import { motion } from 'motion/react'
import { useNavigate } from 'react-router-dom'
import {
  connectDevice,
  discoverDevices,
  listDevices,
  pollPeerConnectionStatus,
} from '../api/devices'
import { establishSession } from '../api/session'
import { ConnectionStatusPanel } from '../components/connection/ConnectionStatus'
import { ManualConnectForm } from '../components/connection/ManualConnectForm'
import { RadarDiscoveryView } from '../components/connection/RadarDiscoveryView'
import { ErrorBanner } from '../components/ui/ErrorBanner'
import { ROUTES } from '../constants/routes'
import { useAppStore } from '../stores/appStore'
import { useConnectionStore } from '../stores/connectionStore'
import { useFileStore } from '../stores/fileStore'
import { formatBytes } from '../utils/format'
import { getErrorMessage } from '../utils/errors'
import type { DiscoveredDevice } from '../types/api'

export function ConnectPage() {
  const navigate = useNavigate()
  const network = useAppStore((s) => s.network)
  const primary = useFileStore((s) => s.files.find((f) => f.uploaded)?.uploaded ?? null)
  const {
    phase,
    devices,
    selectedDevice,
    error,
    setPhase,
    setDevices,
    setSelectedDevice,
    setConnectResult,
    setTarget,
    setSession,
    setError,
  } = useConnectionStore()

  const [busy, setBusy] = useState(false)
  const [showManualPin, setShowManualPin] = useState(false)
  const pollRef = useRef<number | null>(null)

  useEffect(() => {
    if (!primary) navigate(ROUTES.send, { replace: true })
  }, [navigate, primary])

  const refreshDevices = useCallback(async () => {
    setPhase('discovering')
    setError(null)
    try {
      await discoverDevices()
      const list = await listDevices()
      setDevices(list)
      setPhase('idle')
    } catch (err) {
      setError(getErrorMessage(err, 'Discovery failed'))
      setPhase('failed')
    }
  }, [setDevices, setError, setPhase])

  useEffect(() => {
    void refreshDevices()
    const id = window.setInterval(() => {
      void listDevices()
        .then(setDevices)
        .catch(() => undefined)
    }, 4000)
    return () => window.clearInterval(id)
  }, [refreshDevices, setDevices])

  useEffect(
    () => () => {
      if (pollRef.current) window.clearInterval(pollRef.current)
    },
    [],
  )

  const waitForApprovalThenEstablish = async (
    connectionId: string,
    ip: string,
    port: number,
    deviceId?: string,
  ) => {
    setPhase('awaiting_approval')
    setTarget(ip, port)

    await new Promise<void>((resolve, reject) => {
      let attempts = 0
      pollRef.current = window.setInterval(() => {
        void (async () => {
          attempts += 1
          try {
            const status = await pollPeerConnectionStatus(ip, port, connectionId)
            if (status === 'APPROVED') {
              if (pollRef.current) window.clearInterval(pollRef.current)
              pollRef.current = null
              resolve()
            } else if (status === 'REJECTED' || status === 'EXPIRED') {
              if (pollRef.current) window.clearInterval(pollRef.current)
              pollRef.current = null
              reject(new Error(`Connection ${status.toLowerCase()}`))
            } else if (attempts > 60) {
              if (pollRef.current) window.clearInterval(pollRef.current)
              pollRef.current = null
              reject(new Error('Timed out waiting for receiver approval'))
            }
          } catch (err) {
            if (attempts > 60) {
              if (pollRef.current) window.clearInterval(pollRef.current)
              pollRef.current = null
              reject(err)
            }
          }
        })()
      }, 2000)
    })

    setPhase('establishing')
    const session = await establishSession({
      target_ip: ip,
      target_port: port,
      device_id: deviceId,
    })
    setSession({
      session_id: session.session_id,
      status: session.status,
      local_role: 'SENDER',
      peer_ip: session.peer_ip,
      peer_api_port: session.peer_api_port,
      peer_udp_port: session.peer_udp_port,
      receiver_ready: false,
    })
    setPhase('connected')
    navigate(ROUTES.sendConfigure)
  }

  const handleConnectDevice = async (device: DiscoveredDevice) => {
    setBusy(true)
    setError(null)
    setSelectedDevice(device)
    setPhase('connecting')
    try {
      const result = await connectDevice({
        device_id: device.device_id,
        api_port: device.api_port,
      })
      setConnectResult(result)
      await waitForApprovalThenEstablish(
        result.connection_id,
        device.ip_address,
        device.api_port,
        device.device_id,
      )
    } catch (err) {
      setPhase('failed')
      setError(getErrorMessage(err, 'Could not connect to device'))
    } finally {
      setBusy(false)
    }
  }

  const handleManualConnect = async (values: {
    ip_address: string
    pin: string
    api_port: number
  }) => {
    setBusy(true)
    setError(null)
    setPhase('connecting')
    try {
      const result = await connectDevice(values)
      setConnectResult(result)
      await waitForApprovalThenEstablish(result.connection_id, values.ip_address, values.api_port)
    } catch (err) {
      setPhase('failed')
      setError(getErrorMessage(err, 'Manual connection failed'))
    } finally {
      setBusy(false)
    }
  }

  const isConnecting = phase === 'connecting' || phase === 'awaiting_approval' || phase === 'establishing'

  return (
    <div className="mx-auto max-w-3xl flex flex-col min-h-[calc(100vh-160px)] justify-between space-y-6 pb-6">
      <div className="space-y-6">
        {/* Header matching reference mockup */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <button
              type="button"
              onClick={() => navigate(ROUTES.send)}
              className="mt-1 p-2 rounded-full text-[var(--text)] hover:bg-[var(--bg-light)] transition focus-visible:outline-none"
              aria-label="Go back to file selection"
            >
              <ArrowLeft className="w-6 h-6 stroke-[2.25]" />
            </button>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-[var(--text)]">Connect to Device</h1>
              <p className="mt-1 text-sm text-[var(--text-muted)]">
                Find the device you want to share with.
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => void refreshDevices()}
            disabled={busy}
            title="Scan for receivers"
            className="p-2.5 rounded-full hover:bg-[var(--bg-light)] text-[var(--text)] transition"
          >
            <RefreshCw className={`w-4 h-4 ${phase === 'discovering' ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {error ? <ErrorBanner message={error} onDismiss={() => setError(null)} /> : null}

        {/* Status banner when connecting / awaiting approval */}
        {isConnecting && (
          <ConnectionStatusPanel
            phase={phase}
            detail={
              phase === 'awaiting_approval'
                ? 'Waiting for the receiver to approve your connection request…'
                : selectedDevice
                  ? `Selected ${selectedDevice.device_name}`
                  : null
            }
          />
        )}

        {/* Animated Radar Orbit View matching reference mockup */}
        {!showManualPin ? (
          <div className="space-y-6">
            <RadarDiscoveryView
              devices={devices}
              selectedDevice={selectedDevice}
              onSelect={(d) => {
                setSelectedDevice(d)
              }}
              discovering={phase === 'discovering' || devices.length === 0}
              thisLaptopName={network?.device_name || 'This laptop'}
            />

            {/* Subtitle & PIN option below radar */}
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-bold tracking-tight text-[var(--text)]">
                {devices.length === 0
                  ? 'Searching for nearby laptops…'
                  : `${devices.length} ${devices.length === 1 ? 'device' : 'devices'} found`}
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                {devices.length > 0
                  ? 'Tap the laptop you want to share with.'
                  : 'Ensure the receiver is on the same Wi-Fi and has Receive mode open.'}
              </p>

              <button
                type="button"
                onClick={() => setShowManualPin(true)}
                className="mt-3 text-sm font-semibold text-[var(--text)] hover:underline inline-flex items-center gap-1.5 focus-visible:outline-none"
              >
                <KeyRound className="w-4 h-4 text-[var(--primary)]" />
                <span>Can't find the device? Use a PIN instead</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4 max-w-md mx-auto pt-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-[var(--text)]">Manual IP & PIN Fallback</span>
              <button
                type="button"
                onClick={() => setShowManualPin(false)}
                className="text-xs text-[var(--primary)] hover:underline"
              >
                Back to Radar
              </button>
            </div>
            <ManualConnectForm onSubmit={handleManualConnect} loading={busy} />
          </div>
        )}
      </div>

      {/* Bottom Bar matching reference mockup */}
      <div className="pt-6 border-t border-[var(--border)] flex flex-wrap items-center justify-between gap-4">
        <div className="text-sm font-medium text-[var(--text-muted)]">
          {primary ? (
            <span>
              Sending 1 file · <strong className="font-mono text-[var(--text)]">{formatBytes(primary.file_size)}</strong>
            </span>
          ) : (
            <span>No file selected</span>
          )}
        </div>

        <motion.button
          whileHover={{ scale: selectedDevice && !busy ? 1.02 : 1 }}
          whileTap={{ scale: selectedDevice && !busy ? 0.98 : 1 }}
          type="button"
          onClick={() => {
            if (selectedDevice && !busy) {
              void handleConnectDevice(selectedDevice)
            }
          }}
          disabled={!selectedDevice || busy}
          className={`rounded-full px-9 py-3.5 text-base font-semibold text-white shadow-sm transition ${
            !selectedDevice || busy
              ? 'bg-[#d8a48c] cursor-not-allowed opacity-60'
              : 'bg-[var(--primary)] hover:bg-[var(--primary-hover)] cursor-pointer'
          }`}
        >
          {busy ? 'Connecting…' : 'Connect'}
        </motion.button>
      </div>
    </div>
  )
}
