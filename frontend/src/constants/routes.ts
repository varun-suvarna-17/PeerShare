export const ROUTES = {
  home: '/',
  send: '/send',
  sendConnect: '/send/connect',
  sendConfigure: '/send/configure',
  receive: '/receive',
  transfer: '/transfer/:transferId',
  history: '/history',
  settings: '/settings',
} as const

export function transferPath(transferId: string): string {
  return `/transfer/${transferId}`
}
