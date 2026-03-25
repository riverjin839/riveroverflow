import { useEffect, useState } from 'react'
import { BarChart3 } from 'lucide-react'
import api from '../../presenters/api'
import { formatKRW } from '../../presenters/format'
import clsx from 'clsx'

interface Trade {
  id: string
  symbol: string
  name: string
  side: string
  quantity: number
  price: number
  total_value: number
  status: string
  strategy_id: string | null
  signal_reason: string | null
  created_at: string
}

interface Stats {
  total_trades: number
  total_sell_value: number
}

export default function AnalyticsPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.get('/api/v1/trades?limit=100'),
      api.get('/api/v1/trades/stats'),
    ])
      .then(([tradesRes, statsRes]) => {
        setTrades(tradesRes.data.trades)
        setStats(statsRes.data)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const buyCount = trades.filter((t) => t.side === 'buy').length
  const sellCount = trades.filter((t) => t.side === 'sell').length

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">거래 분석</h1>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <p className="text-xs text-slate-400">총 거래 횟수</p>
          <p className="text-2xl font-bold mt-1">{stats?.total_trades ?? 0}</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400">매수</p>
          <p className="text-2xl font-bold text-up mt-1">{buyCount}</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400">매도</p>
          <p className="text-2xl font-bold text-down mt-1">{sellCount}</p>
        </div>
        <div className="card">
          <p className="text-xs text-slate-400">총 매도금액</p>
          <p className="text-lg font-bold font-mono mt-1">
            {formatKRW(stats?.total_sell_value)}
          </p>
        </div>
      </div>

      {/* Trade history */}
      <div className="card">
        <h2 className="text-sm font-semibold mb-4">거래 내역</h2>
        {loading ? (
          <div className="text-center text-slate-500 py-8">로딩 중...</div>
        ) : trades.length === 0 ? (
          <div className="text-center text-slate-500 py-12">
            <BarChart3 size={32} className="mx-auto mb-3 opacity-30" />
            <p>거래 내역이 없습니다</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-surface-border text-left">
                  <th className="pb-3 pr-3">일시</th>
                  <th className="pb-3 pr-3">종목</th>
                  <th className="pb-3 pr-3">구분</th>
                  <th className="pb-3 pr-3 text-right">수량</th>
                  <th className="pb-3 pr-3 text-right">단가</th>
                  <th className="pb-3 text-right hidden md:table-cell">전략</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr
                    key={t.id}
                    className="border-b border-surface-border/40 hover:bg-surface-border/20"
                  >
                    <td className="py-2.5 pr-3 text-xs text-slate-400">
                      {new Date(t.created_at).toLocaleString('ko-KR', {
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-2.5 pr-3">
                      <span className="font-medium">{t.symbol}</span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <span
                        className={clsx(
                          'text-xs font-bold',
                          t.side === 'buy' ? 'text-up' : 'text-down'
                        )}
                      >
                        {t.side === 'buy' ? '매수' : '매도'}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right font-mono">
                      {t.quantity.toLocaleString()}
                    </td>
                    <td className="py-2.5 pr-3 text-right font-mono">
                      {formatKRW(t.price)}
                    </td>
                    <td className="py-2.5 text-right hidden md:table-cell">
                      <span className="text-xs text-slate-500">
                        {t.strategy_id?.slice(0, 8) ?? '-'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
