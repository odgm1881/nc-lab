import { Spin } from 'antd'
import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { useAuth } from './auth/AuthContext'
import { AppLayout } from './components/AppLayout'
import { LoginPage } from './pages/LoginPage'

const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })),
)
const ImportPage = lazy(() =>
  import('./pages/ImportPage').then((module) => ({ default: module.ImportPage })),
)
const VariationsPage = lazy(() =>
  import('./pages/VariationsPage').then((module) => ({ default: module.VariationsPage })),
)
const CatalogPage = lazy(() =>
  import('./pages/CatalogPage').then((module) => ({ default: module.CatalogPage })),
)
const CardDetailPage = lazy(() =>
  import('./pages/CardDetailPage').then((module) => ({ default: module.CardDetailPage })),
)
const OperatorPage = lazy(() =>
  import('./pages/OperatorPage').then((module) => ({ default: module.OperatorPage })),
)
const PilotsPage = lazy(() =>
  import('./pages/PilotsPage').then((module) => ({ default: module.PilotsPage })),
)
const PilotDetailPage = lazy(() =>
  import('./pages/PilotDetailPage').then((module) => ({ default: module.PilotDetailPage })),
)
const ValidationRulesPage = lazy(() =>
  import('./pages/ValidationRulesPage').then((module) => ({ default: module.ValidationRulesPage })),
)
const IntegrationPage = lazy(() =>
  import('./pages/IntegrationPage').then((module) => ({ default: module.IntegrationPage })),
)
const TeamPage = lazy(() =>
  import('./pages/TeamPage').then((module) => ({ default: module.TeamPage })),
)

const pageFallback = (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: 320 }}>
    <Spin size="large" />
  </div>
)

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', height: '100dvh' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  const canEdit = user.role !== 'viewer'
  const canManageTeam = Boolean(
    user.client_id && ['client', 'client_admin', 'admin'].includes(user.role),
  )

  return (
    <AppLayout>
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/pilots" element={<PilotsPage />} />
          <Route path="/pilots/:id" element={<PilotDetailPage />} />
          {canEdit && <Route path="/import" element={<ImportPage />} />}
          {canEdit && <Route path="/variations" element={<VariationsPage />} />}
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/catalog/:id" element={<CardDetailPage />} />
          <Route path="/integration" element={<IntegrationPage />} />
          {canManageTeam && <Route path="/team" element={<TeamPage />} />}
          {(user.role === 'operator' || user.role === 'admin') && (
            <>
              <Route path="/operator" element={<OperatorPage />} />
              <Route path="/validation-rules" element={<ValidationRulesPage />} />
            </>
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppLayout>
  )
}
