import clsx from 'clsx'
import type { NewsItem } from '../../presenters/useHanriver'

type Props = {
  items: NewsItem[]
  loading: boolean
}

function importanceBadge(imp: string) {
  const map: Record<string, { label: string; cls: string }> = {
    high: { label: '상', cls: 'bg-red-500/20 text-red-300 border-red-500/40' },
    medium: { label: '중', cls: 'bg-amber-500/20 text-amber-300 border-amber-500/40' },
    low: { label: '하', cls: 'bg-slate-500/20 text-slate-300 border-slate-500/40' },
    unknown: { label: '?', cls: 'bg-slate-700/40 text-slate-400 border-slate-600/40' },
  }
  const v = map[imp] ?? map.unknown
  return (
    <span
      className={clsx(
        'text-[10px] font-semibold px-1.5 py-0.5 rounded border',
        v.cls,
      )}
    >
      {v.label}
    </span>
  )
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

const SOURCE_LABEL: Record<string, string> = {
  hankyung: '한경',
  dart: 'DART',
}

export default function NewsFeed({ items, loading }: Props) {
  return (
    <section className="bg-surface-card rounded-lg border border-surface-border p-4">
      <h2 className="text-sm font-semibold text-slate-200 mb-3">뉴스 & 공시</h2>
      <ul className="divide-y divide-surface-border">
        {loading && items.length === 0
          ? Array.from({ length: 5 }).map((_, i) => (
              <li key={i} className="h-10 bg-surface-border/30 animate-pulse my-1" />
            ))
          : items.map((n) => (
              <li key={n.id} className="py-2 flex items-center gap-3">
                <span className="text-xs text-slate-500 tabular-nums w-12 shrink-0">
                  {formatTime(n.published_at)}
                </span>
                <span className="text-xs text-slate-400 w-12 shrink-0">
                  {SOURCE_LABEL[n.source] ?? n.source}
                </span>
                <a
                  href={n.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-slate-200 hover:text-brand-500 truncate flex-1"
                >
                  {n.title}
                </a>
                {importanceBadge(n.importance)}
              </li>
            ))}
      </ul>
    </section>
  )
}
