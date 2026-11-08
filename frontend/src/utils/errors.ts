import axios from 'axios'

export function getErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { message?: string; detail?: string | { msg?: string }[] }
      | undefined

    if (typeof data?.message === 'string' && data.message) return data.message
    if (typeof data?.detail === 'string' && data.detail) return data.detail
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) return data.detail[0].msg
    if (error.message === 'Network Error') {
      return 'Backend unavailable. Start the local PeerShare API and try again.'
    }
    return error.message || fallback
  }

  if (error instanceof Error && error.message) return error.message
  return fallback
}
