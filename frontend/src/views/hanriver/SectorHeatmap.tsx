import clsx from 'clsx'
import type { Quote } from '../../presenters/useHanriver'

type Props = {
  quotes: Quote[]
  loading: boolean
}

function cellClass(change: number | null): string {
  if (change == null) return 'bg-slate-700/50 text-slate-300'
  if (change >= 2) return 'bg-red-500/70 text-white'
  if (change >= 1) return 'bg-red-500/50 text-white'
  if (change > 0) return 'bg-red-500/25 text-red-100'
  if (change <= -2) return 'bg-blue-500/70 text-white'
  if (change <= -1) return 'bg-blue-500/50 text-white'
  if (change < 0) return 'bg-blue-500/25 text-blue-100'
  return 'bg-slate-600/40 text-slate-200'
}

export default function SectorHeatmap({ quotes, loading }: Props) {
  return (
    <section className="bg-surface-card rounded-lg border border-surface-border p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200">업종 히트맵</h2>
        {quotes[0]?.stale && (
          <span className="text-xs text-amber-400">stub 데이터</span>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {loading && quotes.length === 0 ? (
          Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-20 bg-surface-border/40 animate-pulse rounded" />
          ))
        ) : quotes.length === 0 ? (
          <div className="col-span-full text-sm text-slate-500 py-4 text-center">
            데이터 없음
          </div>
        ) : (
          quotes.map((q) => (
            <div
              key={q.code}
              className={clsx(
                'rounded p-3 flex flex-col items-center justify-center min-h-[80px]',
                cellClass(q.change_pct ?? null),
              )}
            >
              <div className="text-sm font-semibold">{q.name}</div>
              <div className="text-xs mt-1 tabular-nums">
                {q.change_pct != null
                  ? `${q.change_pct > 0 ? '+' : ''}${q.change_pct.toFixed(2)}%`
                  : '-'}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
