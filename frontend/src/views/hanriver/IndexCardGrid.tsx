import clsx from 'clsx'
import type { Quote } from '../../presenters/useHanriver'

type Props = {
  title: string
  quotes: Quote[]
  loading: boolean
  columns?: number
}

function formatPrice(p: number): string {
  if (p >= 1000) return p.toLocaleString('ko-KR', { maximumFractionDigits: 2 })
  return p.toLocaleString('ko-KR', { maximumFractionDigits: 3 })
}

function changeClass(change: number | null | undefined): string {
  if (change == null) return 'text-slate-400'
  if (change > 0) return 'text-red-400'
  if (change < 0) return 'text-blue-400'
  return 'text-slate-400'
}

function formatChange(change: number | null | undefined): string {
  if (change == null) return '-'
  const sign = change > 0 ? '+' : ''
  return `${sign}${change.toFixed(2)}%`
}

export default function IndexCardGrid({ title, quotes, loading, columns = 4 }: Props) {
  return (
    <section className="bg-surface-card rounded-lg border border-surface-border p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
        {quotes[0]?.stale && (
          <span className="text-xs text-amber-400">stub 데이터</span>
        )}
      </div>
      <div
        className={clsx('grid gap-3', {
          'grid-cols-2 md:grid-cols-4': columns === 4,
          'grid-cols-2 md:grid-cols-4 lg:grid-cols-8': columns === 8,
          'grid-cols-2 md:grid-cols-3 lg:grid-cols-6': columns === 6,
        })}
      >
        {loading && quotes.length === 0 ? (
          Array.from({ length: columns }).map((_, i) => (
            <div
              key={i}
              className="h-20 bg-surface-border/40 rounded animate-pulse"
            />
          ))
        ) : quotes.length === 0 ? (
          <div className="col-span-full text-sm text-slate-500 py-4 text-center">
            데이터 없음
          </div>
        ) : (
          quotes.map((q) => (
            <div
              key={q.code}
              className="rounded-md border border-surface-border bg-surface p-3"
            >
              <div className="text-xs text-slate-400 truncate">{q.name}</div>
              <div className="mt-1 text-lg font-semibold text-white">
                {formatPrice(q.price)}
              </div>
              <div className={clsx('text-xs mt-0.5', changeClass(q.change_pct))}>
                {formatChange(q.change_pct)}
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
