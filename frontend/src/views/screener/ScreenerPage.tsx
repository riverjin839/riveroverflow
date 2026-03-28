import { useState } from 'react'
import { TrendingUp, Search, Loader2 } from 'lucide-react'
import { useScreener } from '../../presenters/useScreener'
import type { NewHighResult } from '../../models/screenerStore'
import { formatKRW } from '../../presenters/format'

function HighBadge({ isNewHigh }: { isNewHigh: boolean }) {
  if (!isNewHigh) return null
  return (
    <span className="inline-block px-1.5 py-0.5 text-xs rounded bg-up/20 text-up font-semibold">
      신고가
    </span>
  )
}

function PctBar({ pct }: { pct: number }) {
  const width = Math.max(0, Math.min(100, pct))
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-surface-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-brand-500"
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="text-xs tabular-nums w-14 text-right">{pct.toFixed(1)}%</span>
    </div>
  )
}

function ResultRow({ r }: { r: NewHighResult }) {
  return (
    <tr className={r.is_new_high ? 'bg-up/5' : ''}>
      <td className="px-4 py-3 font-mono text-xs text-slate-400">{r.symbol}</td>
      <td className="px-4 py-3 font-medium text-white">
        <div className="flex items-center gap-2">
          {r.name}
          <HighBadge isNewHigh={r.is_new_high} />
        </div>
      </td>
      <td className="px-4 py-3 text-right tabular-nums">{formatKRW(r.current_price)}</td>
      <td className="px-4 py-3 text-right tabular-nums text-slate-400">
        {formatKRW(r.high_52w)}
      </td>
      <td className="px-4 py-3 min-w-[140px]">
        <PctBar pct={r.high_pct} />
      </td>
      <td className="px-4 py-3 text-right tabular-nums text-slate-400 hidden sm:table-cell">
        {r.volume.toLocaleString()}
      </td>
    </tr>
  )
}

export default function ScreenerPage() {
  const { results, loading, lastScanned, scan } = useScreener()
  const [customSymbols, setCustomSymbols] = useState('')
  const [periodDays, setPeriodDays] = useState(252)
  const [thresholdPct, setThresholdPct] = useState(97)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <TrendingUp size={22} className="text-brand-500" />
            52주 신고가 스크리너
          </h1>
          {lastScanned && (
            <p className="text-xs text-slate-500 mt-0.5">마지막 스캔: {lastScanned}</p>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="card space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-1">
            <label className="block text-xs text-slate-400 mb-1">커스텀 종목 (쉼표 구분)</label>
            <input
              type="text"
              value={customSymbols}
              onChange={(e) => setCustomSymbols(e.target.value)}
              placeholder="005930,000660,035420 (비우면 KOSPI 기본 20종목)"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">기간 (거래일)</label>
            <select
              value={periodDays}
              onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            >
              <option value={60}>60일 (약 3개월)</option>
              <option value={126}>126일 (약 6개월)</option>
              <option value={252}>252일 (52주)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              신고가 근접 기준 (고가 대비 %)
            </label>
            <select
              value={thresholdPct}
              onChange={(e) => setThresholdPct(Number(e.target.value))}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            >
              <option value={95}>95% 이상</option>
              <option value={97}>97% 이상</option>
              <option value={99}>99% 이상</option>
              <option value={100}>신고가 갱신만</option>
            </select>
          </div>
        </div>
        <button
          onClick={() => scan(customSymbols, periodDays, thresholdPct)}
          disabled={loading}
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <Search size={16} />
          )}
          {loading ? '스캔 중...' : '스캔 시작'}
        </button>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
            <span className="text-sm font-semibold text-white">
              스캔 결과
            </span>
            <span className="text-xs text-slate-400">
              {results.length}개 종목
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium">코드</th>
                  <th className="px-4 py-2.5 font-medium">종목명</th>
                  <th className="px-4 py-2.5 font-medium text-right">현재가</th>
                  <th className="px-4 py-2.5 font-medium text-right">52주 고가</th>
                  <th className="px-4 py-2.5 font-medium">고가 대비</th>
                  <th className="px-4 py-2.5 font-medium text-right hidden sm:table-cell">
                    거래량
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {results.map((r) => (
                  <ResultRow key={r.symbol} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && results.length === 0 && lastScanned && (
        <div className="card text-center py-12 text-slate-500">
          <TrendingUp size={40} className="mx-auto mb-3 opacity-30" />
          <p>신고가 근접 종목이 없습니다.</p>
          <p className="text-xs mt-1">기준을 낮추거나 다른 종목을 입력해보세요.</p>
        </div>
      )}

      {!lastScanned && (
        <div className="card text-center py-12 text-slate-500">
          <Search size={40} className="mx-auto mb-3 opacity-30" />
          <p>스캔 버튼을 눌러 신고가 종목을 찾아보세요.</p>
          <p className="text-xs mt-1">기본값: KOSPI 주요 20종목, 52주 기준, 97% 이상</p>
        </div>
      )}
    </div>
  )
}
