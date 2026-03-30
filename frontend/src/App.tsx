import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import DashboardPage from './views/dashboard/DashboardPage'
import PortfolioPage from './views/portfolio/PortfolioPage'
import StrategiesPage from './views/strategies/StrategiesPage'
import AnalyticsPage from './views/analytics/AnalyticsPage'
import ScreenerPage from './views/screener/ScreenerPage'
import ResearchPage from './views/research/ResearchPage'
import OntologyPage from './views/ontology/OntologyPage'
import SettingsPage from './views/settings/SettingsPage'
import ReportsPage from './views/reports/ReportsPage'
import LoginPage from './views/auth/LoginPage'
import { useAuthStore } from './models/authStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="strategies" element={<StrategiesPage />} />
          <Route path="screener"  element={<ScreenerPage />} />
          <Route path="research"  element={<ResearchPage />} />
          <Route path="ontology"  element={<OntologyPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="reports"   element={<ReportsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
