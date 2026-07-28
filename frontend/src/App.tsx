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

const pageFallback = (
  <div style={{ display: 'grid', placeItems: 'center', minHeight: 320 }}>
    <Spin size="large" />
  </div>
)

export default function App() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ display: 'grid', placeItems: 'center', height: '100vh' }}>
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

  return (
    <AppLayout>
      <Suspense fallback={pageFallback}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/variations" element={<VariationsPage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/catalog/:id" element={<CardDetailPage />} />
          {(user.role === 'operator' || user.role === 'admin') && (
            <Route path="/operator" element={<OperatorPage />} />
          )}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </AppLayout>
  )
}
