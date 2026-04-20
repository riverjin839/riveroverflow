import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, TrendingUp, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import api from '../../presenters/api'

type NewsItem = { title: string; office: string; url: string; published: string }
type DiscItem = { report_name: string; url: string; rcept_dt: string }
type LimitUpItem = {
  symbol: string
  name: string
  close: number
  change_pct: number
  volume: number
  trading_value: number
  category: 'limit_up' | 'surge'
  reason: string | null
  news: NewsItem[]
  disclosures: DiscItem[]
}
type Payload = {
  date: string
  limit_up_count: number
  surge_count: number
  total_trading_value: number
  items: LimitUpItem[]
  generated_at: string
}

function formatWon(n: number): string {
  if (n >= 1_0000_0000_0000) return `${(n / 1_0000_0000_0000).toFixed(2)}조`
  if (n >= 1_0000_0000) return `${(n / 1_0000_0000).toFixed(1)}억`
  if (n >= 1_0000) return `${(n / 1_0000).toFixed(0)}만`
  return n.toLocaleString()
}

export default function LimitUpPage() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [date, setDate] = useState('')
  const [tab, setTab] = useState<'all' | 'limit_up' | 'surge'>('limit_up')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  async function fetchData(force = false) {
    setLoading(true)
    setErr(null)
    try {
      const params: Record<string, string | boolean> = {}
      if (date) params.date = date
      if (force) params.force = true
      const r = await api.get<Payload>('/api/v1/hanriver/limit-up', { params })
      setData(r.data)
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(false)
  }, [])

  const items = data?.items ?? []
  const filtered = tab === 'all' ? items : items.filter((i) => i.category === tab)

  function toggle(sym: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(sym)) next.delete(sym)
      else next.add(sym)
      return next
    })
  }

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <TrendingUp size={22} className="text-red-400" />
            오늘의 상한가 & 급등주
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            pykrx 일일 등락률 + 네이버 뉴스 + DART 공시 + Claude 상승 이유 분석
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="date"
            className="input"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            placeholder="YYYY-MM-DD"
          />
          <button className="btn-primary" onClick={() => fetchData(false)} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> 조회
          </button>
          <button className="btn-ghost text-sm" onClick={() => fetchData(true)} disabled={loading}>
            재분석
          </button>
        </div>
      </header>

      {data && (
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="기준일" value={data.date} color="text-slate-200" />
          <Stat label="상한가" value={`${data.limit_up_count}종목`} color="text-red-400" />
          <Stat label="급등 (≥10%)" value={`${data.surge_count}종목`} color="text-amber-400" />
          <Stat label="합산 거래대금" value={formatWon(data.total_trading_value)} color="text-brand-500" />
        </section>
      )}

      {err && <div className="text-red-400 text-sm">{err}</div>}

      <div className="flex gap-1 border-b border-surface-border">
        {(
          [
            { k: 'limit_up', l: `상한가 (${data?.limit_up_count ?? 0})` },
            { k: 'surge', l: `급등 (${data?.surge_count ?? 0})` },
            { k: 'all', l: `전체 (${items.length})` },
          ] as const
        ).map((t) => (
          <button
            key={t.k}
            onClick={() => setTab(t.k)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 -mb-px',
              tab === t.k ? 'border-brand-500 text-brand-500' : 'border-transparent text-slate-400 hover:text-white',
            )}
          >
            {t.l}
          </button>
        ))}
      </div>

      <section className="space-y-2">
        {loading && !data && (
          <div className="text-center py-8 text-slate-500 text-sm">
            수집·분석 중 (상한가 많은 날은 최대 30초)…
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <div className="text-center py-8 text-slate-500 text-sm">해당 조건의 종목 없음</div>
        )}
        {filtered.map((it) => {
          const open = expanded.has(it.symbol)
          return (
            <article
              key={it.symbol}
              className="bg-surface-card border border-surface-border rounded-lg overflow-hidden"
            >
              <button
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-surface"
                onClick={() => toggle(it.symbol)}
              >
                {open ? <ChevronDown size={16} className="text-slate-500" /> : <ChevronRight size={16} className="text-slate-500" />}
                <Badge category={it.category} />
                <Link
                  to={`/hanriver/stock/${it.symbol}`}
                  className="text-sm font-semibold text-brand-500 hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {it.name}
                </Link>
                <span className="text-xs text-slate-500 font-mono">{it.symbol}</span>
                <span className="flex-1" />
                <span className="text-sm tabular-nums text-slate-200">{it.close.toLocaleString()}</span>
                <span className="text-sm tabular-nums font-semibold text-red-400 w-20 text-right">
                  +{it.change_pct.toFixed(2)}%
                </span>
                <span className="text-xs tabular-nums text-slate-400 w-24 text-right">
                  {formatWon(it.trading_value)}
                </span>
              </button>

              {open && (
                <div className="border-t border-surface-border p-4 space-y-3 bg-surface/60">
                  {it.reason && (
                    <div>
                      <div className="text-xs text-slate-500 mb-1">AI 상승 이유 분석</div>
                      <p className="text-sm text-slate-200 leading-relaxed">{it.reason}</p>
                    </div>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="text-xs text-slate-500 mb-1">관련 뉴스</div>
                      <ul className="text-xs space-y-1">
                        {it.news.length > 0 ? (
                          it.news.map((n, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-slate-600 w-12 shrink-0">{n.office}</span>
                              <a
                                href={n.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-slate-300 hover:text-brand-500 truncate"
                              >
                                {n.title}
                              </a>
                            </li>
                          ))
                        ) : (
                          <li className="text-slate-600">(수집된 뉴스 없음)</li>
                        )}
                      </ul>
                    </div>
                    <div>
                      <div className="text-xs text-slate-500 mb-1">최근 7일 공시</div>
                      <ul className="text-xs space-y-1">
                        {it.disclosures.length > 0 ? (
                          it.disclosures.map((d, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-slate-600 w-16 shrink-0">{d.rcept_dt}</span>
                              <a
                                href={d.url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-slate-300 hover:text-brand-500 truncate"
                              >
                                {d.report_name}
                              </a>
                            </li>
                          ))
                        ) : (
                          <li className="text-slate-600">(공시 없음)</li>
                        )}
                      </ul>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-xs text-slate-400 pt-2 border-t border-surface-border">
                    <div>거래량: <span className="text-slate-200 tabular-nums">{it.volume.toLocaleString()}</span></div>
                    <div>거래대금: <span className="text-slate-200 tabular-nums">{it.trading_value.toLocaleString()}원</span></div>
                    <div>종가: <span className="text-slate-200 tabular-nums">{it.close.toLocaleString()}원</span></div>
                  </div>
                </div>
              )}
            </article>
          )
        })}
      </section>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-surface-card border border-surface-border rounded p-3">
      <div className="text-xs text-slate-500">{label}</div>
      <div className={clsx('text-lg font-semibold mt-1 tabular-nums', color ?? 'text-slate-200')}>{value}</div>
    </div>
  )
}

function Badge({ category }: { category: 'limit_up' | 'surge' }) {
  if (category === 'limit_up') {
    return (
      <span className="text-xs font-semibold px-2 py-0.5 rounded border bg-red-500/20 text-red-300 border-red-500/40 shrink-0">
        상한
      </span>
    )
  }
  return (
    <span className="text-xs font-semibold px-2 py-0.5 rounded border bg-amber-500/20 text-amber-300 border-amber-500/40 shrink-0">
      급등
    </span>
  )
}
