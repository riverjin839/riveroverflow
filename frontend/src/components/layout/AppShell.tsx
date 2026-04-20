import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Briefcase,
  Zap,
  BarChart3,
  Settings,
  TrendingUp,
  FlaskConical,
  Network,
  Newspaper,
  Waves,
  Menu,
  X,
  LogOut,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useAuthStore } from '../../models/authStore'
import { useRealtimeStore } from '../../models/realtimeStore'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/dashboard',  icon: LayoutDashboard, label: '대시보드' },
  { to: '/hanriver',   icon: Waves,            label: 'HANRIVER 시황' },
  { to: '/portfolio',  icon: Briefcase,        label: '포트폴리오' },
  { to: '/strategies', icon: Zap,              label: '전략' },
  { to: '/screener',   icon: TrendingUp,       label: '신고가 스크리너' },
  { to: '/research',   icon: FlaskConical,     label: '오토리서치' },
  { to: '/reports',    icon: Newspaper,        label: '증권사 리포트' },
  { to: '/ontology',   icon: Network,          label: '온톨로지' },
  { to: '/analytics',  icon: BarChart3,        label: '분석' },
  { to: '/settings',   icon: Settings,         label: '설정' },
]

export default function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const logout = useAuthStore((s) => s.logout)
  const connected = useRealtimeStore((s) => s.connected)
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 w-64 flex flex-col bg-surface-card border-r border-surface-border',
          'transition-transform duration-200 ease-in-out',
          'lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-14 px-4 border-b border-surface-border">
          <span className="text-lg font-bold text-white">
            <span className="text-brand-500">River</span>Overflow
          </span>
          <button
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        {/* Connection status */}
        <div className="px-4 py-2 border-b border-surface-border">
          <div className="flex items-center gap-2 text-xs">
            {connected ? (
              <>
                <Wifi size={12} className="text-green-400" />
                <span className="text-green-400">실시간 연결됨</span>
              </>
            ) : (
              <>
                <WifiOff size={12} className="text-slate-500" />
                <span className="text-slate-500">연결 끊김</span>
              </>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-brand-500/10 text-brand-500'
                    : 'text-slate-400 hover:text-white hover:bg-surface-border'
                )
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Bottom: logout */}
        <div className="p-3 border-t border-surface-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-surface-border transition-colors"
          >
            <LogOut size={18} />
            로그아웃
          </button>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar (mobile) */}
        <header className="lg:hidden flex items-center justify-between h-14 px-4 bg-surface-card border-b border-surface-border">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-slate-400 hover:text-white"
          >
            <Menu size={22} />
          </button>
          <span className="text-sm font-bold">
            <span className="text-brand-500">River</span>Overflow
          </span>
          <div className="w-8" /> {/* spacer */}
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-4 py-6 max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
