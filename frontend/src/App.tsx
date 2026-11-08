import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { ROUTES } from './constants/routes'
import { useGlobalEvents } from './hooks/useGlobalEvents'
import { useNetworkStatus } from './hooks/useNetworkStatus'
import { ConfigureTransferPage } from './pages/ConfigureTransferPage'
import { ConnectPage } from './pages/ConnectPage'
import { HistoryPage } from './pages/HistoryPage'
import { HomePage } from './pages/HomePage'
import { ReceivePage } from './pages/ReceivePage'
import { SendFilesPage } from './pages/SendFilesPage'
import { SettingsPage } from './pages/SettingsPage'
import { TransferProgressPage } from './pages/TransferProgressPage'

function AppProviders() {
  useNetworkStatus()
  useGlobalEvents()

  return (
    <AppShell>
      <Routes>
        <Route path={ROUTES.home} element={<HomePage />} />
        <Route path={ROUTES.send} element={<SendFilesPage />} />
        <Route path={ROUTES.sendConnect} element={<ConnectPage />} />
        <Route path={ROUTES.sendConfigure} element={<ConfigureTransferPage />} />
        <Route path={ROUTES.receive} element={<ReceivePage />} />
        <Route path={ROUTES.transfer} element={<TransferProgressPage />} />
        <Route path={ROUTES.history} element={<HistoryPage />} />
        <Route path={ROUTES.settings} element={<SettingsPage />} />
        <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProviders />
    </BrowserRouter>
  )
}
