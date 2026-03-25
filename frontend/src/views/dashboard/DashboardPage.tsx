import { useEffect } from 'react'
import { TrendingUp, TrendingDown, Zap, Activity } from 'lucide-react'
import { usePortfolio } from '../../presenters/usePortfolio'
import { useRealtimeStore } from '../../models/realtimeStore'
import { formatKRW, formatPct, getPctColor } from '../../presenters/format'
import StockChart from './StockChart'
import RecentTrades from './RecentTrades'

export default function DashboardPage() {
  const { balance, positions, loading } = usePortfolio()
  const recentTrades = useRealtimeStore((s) => s.recentTrades)

  if (loading && !balance) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">로딩 중...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">대시보드</h1>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          label="총 평가금액"
          value={formatKRW(balance?.total_value)}
          icon={<Activity size={18} />}
        />
        <SummaryCard
          label="예수금"
          value={formatKRW(balance?.cash)}
          icon={<TrendingUp size={18} />}
        />
        <SummaryCard
          label="평가손익"
          value={formatKRW(balance?.profit_loss)}
          valueClass={getPctColor(balance?.profit_loss_pct ?? 0)}
          icon={<TrendingDown size={18} />}
        />
        <SummaryCard
          label="수익률"
          value={formatPct(balance?.profit_loss_pct ?? 0)}
          valueClass={getPctColor(balance?.profit_loss_pct ?? 0)}
          icon={<Zap size={18} />}
        />
      </div>

      {/* Chart + trades */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <StockChart symbol="005930" name="삼성전자" />
        </div>
        <div>
          <RecentTrades trades={recentTrades.slice(0, 10)} />
        </div>
      </div>

      {/* Positions */}
      {positions.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-slate-300 mb-3">보유 종목</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-surface-border">
                  <th className="text-left pb-2">종목</th>
                  <th className="text-right pb-2">수량</th>
                  <th className="text-right pb-2 hidden sm:table-cell">평균단가</th>
                  <th className="text-right pb-2">현재가</th>
                  <th className="text-right pb-2">수익률</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr key={p.symbol} className="border-b border-surface-border/50">
                    <td className="py-2">
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-slate-500">{p.symbol}</div>
                    </td>
                    <td className="text-right font-mono">{p.quantity.toLocaleString()}</td>
                    <td className="text-right font-mono hidden sm:table-cell">
                      {formatKRW(p.avg_price)}
                    </td>
                    <td className="text-right font-mono">{formatKRW(p.current_price)}</td>
                    <td className={`text-right font-mono ${getPctColor(p.profit_loss_pct)}`}>
                      {formatPct(p.profit_loss_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function SummaryCard({
  label,
  value,
  valueClass = 'text-white',
  icon,
}: {
  label: string
  value: string
  valueClass?: string
  icon: React.ReactNode
}) {
  return (
    <div className="card space-y-2">
      <div className="flex items-center justify-between text-slate-400">
        <span className="text-xs">{label}</span>
        {icon}
      </div>
      <div className={`text-lg font-bold font-mono ${valueClass}`}>{value}</div>
    </div>
  )
}
