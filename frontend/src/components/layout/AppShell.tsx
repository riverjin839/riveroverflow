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
  Star,
  Bot,
  ScrollText,
  BookOpen,
  Clock,
  FlaskRound,
  Sparkles,
  Menu,
  X,
  LogOut,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useAuthStore } from '../../models/authStore'
import { useRealtimeStore } from '../../models/realtimeStore'
import clsx from 'clsx'

type Item = { to: string; icon: typeof LayoutDashboard; label: string }
type Section = { key: string; label: string; items: Item[] }

const SECTIONS: Section[] = [
  {
    key: 'hanriver',
    label: 'HANRIVER',
    items: [
      { to: '/hanriver',             icon: Waves,       label: '시황 대시보드' },
      { to: '/hanriver/limit-up',    icon: TrendingUp,  label: '오늘의 상한가' },
      { to: '/hanriver/pattern-scan', icon: Sparkles,   label: '선취매 스캐너' },
      { to: '/hanriver/watchlist',   icon: Star,        label: '관심/알림' },
      { to: '/hanriver/signals',    icon: Bot,         label: 'AI 시그널' },
      { to: '/hanriver/reports',    icon: ScrollText,  label: 'AI 리포트' },
      { to: '/hanriver/journal',    icon: BookOpen,    label: '매매 일지' },
      { to: '/hanriver/replay',     icon: Clock,       label: '복기' },
      { to: '/hanriver/backtest',   icon: FlaskRound,  label: '백테스트' },
    ],
  },
  {
    key: 'trading',
    label: 'RIVERFLOW · 자동매매',
    items: [
      { to: '/dashboard',  icon: LayoutDashboard, label: '대시보드' },
      { to: '/portfolio',  icon: Briefcase,        label: '포트폴리오' },
      { to: '/strategies', icon: Zap,              label: '전략' },
      { to: '/screener',   icon: TrendingUp,       label: '신고가 스크리너' },
      { to: '/research',   icon: FlaskConical,     label: '오토리서치' },
      { to: '/reports',    icon: Newspaper,        label: '증권사 리포트' },
      { to: '/ontology',   icon: Network,          label: '온톨로지' },
      { to: '/analytics',  icon: BarChart3,        label: '분석' },
      { to: '/settings',   icon: Settings,         label: '설정' },
    ],
  },
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
          className="fixed inset-0 z-20 bg-black/20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 w-64 flex flex-col bg-surface-card border-r border-surface-border',
          'transition-transform duration-200 ease-in-out',
          'lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Brand + traffic lights */}
        <div className="flex items-center gap-3 h-12 px-4 border-b border-surface-border">
          <div className="traffic-lights">
            <span className="traffic-light red" />
            <span className="traffic-light yellow" />
            <span className="traffic-light green" />
          </div>
          <span className="text-[15px] font-semibold text-ink tracking-tight">
            HAN<span className="text-brand-600">RIVER</span>
          </span>
          <button
            className="ml-auto lg:hidden text-ink-muted hover:text-ink"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        {/* Connection status */}
        <div className="px-4 py-2 border-b border-surface-border">
          <div className="flex items-center gap-2 text-[11px]">
            {connected ? (
              <>
                <Wifi size={12} className="text-traffic-green" />
                <span className="text-ink-muted">실시간 연결됨</span>
              </>
            ) : (
              <>
                <WifiOff size={12} className="text-ink-subtle" />
                <span className="text-ink-subtle">연결 끊김</span>
              </>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-5 overflow-y-auto">
          {SECTIONS.map((sec) => (
            <div key={sec.key}>
              <div className="px-3 pb-1.5 eyebrow">{sec.label}</div>
              <div className="space-y-0.5">
                {sec.items.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    end={to === '/hanriver' || to === '/dashboard'}
                    onClick={() => setSidebarOpen(false)}
                    className={({ isActive }) =>
                      clsx(
                        'flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors',
                        isActive
                          ? 'bg-ink text-white shadow-mac'
                          : 'text-ink-muted hover:text-ink hover:bg-surface-inner',
                      )
                    }
                  >
                    <Icon size={15} />
                    {label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom: logout */}
        <div className="p-3 border-t border-surface-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-[13px] text-ink-muted hover:text-ink hover:bg-surface-inner transition-colors"
          >
            <LogOut size={15} />
            로그아웃
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar (mobile) */}
        <header className="lg:hidden flex items-center justify-between h-12 px-4 bg-surface-card border-b border-surface-border">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-ink-muted hover:text-ink"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-semibold text-ink">
            HAN<span className="text-brand-600">RIVER</span>
          </span>
          <div className="w-8" />
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="container mx-auto px-5 py-6 max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
