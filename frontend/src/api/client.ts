import axios from 'axios'

const DEFAULT_API_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000'
const STORAGE_KEY_API_URL = 'peershare_api_base_url'

export function getApiBaseUrl(): string {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_API_URL)
    if (stored && stored.trim().length > 0) {
      return stored.trim().replace(/\/$/, '')
    }
  } catch {
    // ignore local storage error
  }
  return DEFAULT_API_URL
}

export function setApiBaseUrl(url: string): void {
  try {
    const clean = url.trim().replace(/\/$/, '')
    if (clean) {
      localStorage.setItem(STORAGE_KEY_API_URL, clean)
    } else {
      localStorage.removeItem(STORAGE_KEY_API_URL)
    }
  } catch {
    // ignore
  }
}

export const API_BASE_URL = getApiBaseUrl()

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 20000,
  headers: {
    Accept: 'application/json',
  },
})

// Dynamically use current configured URL
api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl()
  return config
})

export function wsBaseUrl(): string {
  const current = getApiBaseUrl()
  try {
    const url = new URL(current)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return url.origin
  } catch {
    return 'ws://127.0.0.1:8000'
  }
}
