import { useEffect } from 'react'
import { globalEventSocket } from '../ws/eventSocket'
import { useAppStore } from '../stores/appStore'
import { useConnectionStore } from '../stores/connectionStore'
import { useTransferStore } from '../stores/transferStore'
import type { PendingTransfer } from '../types/api'
import type { WsEvent } from '../types/events'

export function useGlobalEvents(): void {
  const setWsStatus = useAppStore((s) => s.setWsStatus)
  const setPendingTransfers = useTransferStore((s) => s.setPendingTransfers)
  const applyEvent = useTransferStore((s) => s.applyEvent)

  useEffect(() => {
    globalEventSocket.connect()
    const offStatus = globalEventSocket.onStatus(setWsStatus)
    const offEvent = globalEventSocket.subscribe((event: WsEvent) => {
      if (event.event === 'CONNECTION_REQUEST') {
        // Receive page polls pending connections; event is a nudge signal.
        useConnectionStore.getState().setPhase('awaiting_approval')
      }

      if (event.event === 'TRANSFER_REQUEST' && event.transfer_id) {
        const current = useTransferStore.getState().pendingTransfers
        const exists = current.some((t) => t.transfer_id === event.transfer_id)
        if (!exists) {
          const incoming: PendingTransfer = {
            transfer_id: event.transfer_id,
            file_name: String(event.data.file_name ?? 'Incoming file'),
            file_size: Number(event.data.file_size ?? 0),
            protocol: (event.data.protocol as PendingTransfer['protocol']) || 'selective_repeat',
            status: 'pending',
          }
          setPendingTransfers([incoming, ...current])
        }
      }

      if (event.transfer_id && event.transfer_id === useTransferStore.getState().activeTransferId) {
        applyEvent(event)
      }

      if (
        event.event === 'TRANSFER_ACCEPTED' ||
        event.event === 'TRANSFER_REJECTED' ||
        event.event === 'SESSION_ESTABLISHED' ||
        event.event === 'SESSION_ENDED'
      ) {
        applyEvent(event)
      }
    })

    return () => {
      offStatus()
      offEvent()
    }
  }, [applyEvent, setPendingTransfers, setWsStatus])
}
