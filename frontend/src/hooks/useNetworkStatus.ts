import { useCallback, useEffect } from 'react'
import { getNetworkStatus } from '../api/network'
import { useAppStore } from '../stores/appStore'
import { getErrorMessage } from '../utils/errors'

export function useNetworkStatus(pollMs = 10000): {
  refresh: () => Promise<void>
} {
  const setNetwork = useAppStore((s) => s.setNetwork)
  const setNetworkError = useAppStore((s) => s.setNetworkError)
  const setBackendOnline = useAppStore((s) => s.setBackendOnline)

  const refresh = useCallback(async () => {
    try {
      const status = await getNetworkStatus()
      setNetwork(status)
      setNetworkError(null)
      setBackendOnline(true)
    } catch (error) {
      setBackendOnline(false)
      setNetworkError(getErrorMessage(error, 'Backend unavailable'))
    }
  }, [setBackendOnline, setNetwork, setNetworkError])

  useEffect(() => {
    void refresh()
    const id = window.setInterval(() => {
      void refresh()
    }, pollMs)
    return () => window.clearInterval(id)
  }, [pollMs, refresh])

  return { refresh }
}
