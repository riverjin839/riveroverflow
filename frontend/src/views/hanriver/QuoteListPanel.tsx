import clsx from 'clsx'
import type { Quote } from '../../presenters/useHanriver'

type Props = {
  title: string
  quotes: Quote[]
  loading: boolean
}

function changeClass(change: number | null | undefined): string {
  if (change == null) return 'text-slate-400'
  if (change > 0) return 'text-red-400'
  if (change < 0) return 'text-blue-400'
  return 'text-slate-400'
}

export default function QuoteListPanel({ title, quotes, loading }: Props) {
  return (
    <section className="bg-surface-card rounded-lg border border-surface-border p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
        {quotes[0]?.stale && (
          <span className="text-xs text-amber-400">stub 데이터</span>
        )}
      </div>
      <ul className="divide-y divide-surface-border">
        {loading && quotes.length === 0
          ? Array.from({ length: 4 }).map((_, i) => (
              <li key={i} className="h-8 bg-surface-border/30 animate-pulse my-1.5" />
            ))
          : quotes.map((q) => (
              <li
                key={q.code}
                className="py-2 flex items-center justify-between text-sm"
              >
                <span className="text-slate-300 truncate">{q.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-white tabular-nums">
                    {q.price.toLocaleString('ko-KR', { maximumFractionDigits: 3 })}
                  </span>
                  <span
                    className={clsx(
                      'tabular-nums text-xs w-16 text-right',
                      changeClass(q.change_pct),
                    )}
                  >
                    {q.change_pct != null
                      ? `${q.change_pct > 0 ? '+' : ''}${q.change_pct.toFixed(2)}%`
                      : '-'}
                  </span>
                </div>
              </li>
            ))}
      </ul>
    </section>
  )
}
