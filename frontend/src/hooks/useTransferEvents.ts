import { useEffect } from 'react'
import { transferEventSocket } from '../ws/transferSocket'
import { useTransferStore } from '../stores/transferStore'

export function useTransferEvents(transferId: string | undefined): void {
  const applyEvent = useTransferStore((s) => s.applyEvent)

  useEffect(() => {
    if (!transferId) return
    transferEventSocket.connect(transferId)
    const unsubscribe = transferEventSocket.subscribe(applyEvent)
    return () => {
      unsubscribe()
      transferEventSocket.disconnect()
    }
  }, [applyEvent, transferId])
}
