import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, ChevronDown, ChevronRight, Flame, TrendingUp, Coins } from 'lucide-react'
import clsx from 'clsx'
import api from '../../presenters/api'
import MacWindow, { MacMiniCard } from '../../components/MacWindow'

type NewsItem = { title: string; office: string; url: string; published: string }
type DiscItem = { report_name: string; url: string; rcept_dt: string }
type LimitUpItem = {
  symbol: string
  name: string
  market: string
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
  source: string
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

function todayISO(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export default function LimitUpPage() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [date, setDate] = useState(todayISO())
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

  useEffect(() => { fetchData(false) }, [])
  useEffect(() => {
    if (date !== todayISO()) return
    const t = setInterval(() => fetchData(false), 60_000)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date])

  const items = data?.items ?? []
  const filtered = tab === 'all' ? items : items.filter((i) => i.category === tab)

  function toggle(s: string) {
    setExpanded((p) => {
      const n = new Set(p)
      n.has(s) ? n.delete(s) : n.add(s)
      return n
    })
  }

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink tracking-tight">오늘의 상한가</h1>
          <p className="text-xs text-ink-muted mt-1">
            네이버 순위 · DART 공시 · Claude AI 분석
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="date"
            className="input"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
          <button className="btn-primary" onClick={() => fetchData(false)} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            조회
          </button>
          <button className="btn-ghost text-sm" onClick={() => fetchData(true)} disabled={loading}>
            재분석
          </button>
        </div>
      </header>

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MacMiniCard
            icon={<span>●</span>}
            label={`기준일 · ${data.source}`}
            value={data.date}
          />
          <MacMiniCard
            icon={<Flame size={12} className="text-up" />}
            label="상한가"
            value={<span className="text-up">{data.limit_up_count}종목</span>}
          />
          <MacMiniCard
            icon={<TrendingUp size={12} className="text-amber-600" />}
            label="급등 (≥10%)"
            value={<span className="text-amber-600">{data.surge_count}종목</span>}
          />
          <MacMiniCard
            icon={<Coins size={12} className="text-brand-600" />}
            label="합산 거래대금"
            value={<span className="text-brand-600">{formatWon(data.total_trading_value)}</span>}
          />
        </div>
      )}

      {err && <div className="text-up text-sm">{err}</div>}

      <MacWindow title="LIMIT UP · SURGE" bodyClassName="p-0">
        {/* 탭 */}
        <div className="flex gap-1 border-b border-surface-border px-4">
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
                'px-3 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors',
                tab === t.k ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink',
              )}
            >
              {t.l}
            </button>
          ))}
        </div>

        <ul className="divide-y divide-surface-border">
          {loading && !data && (
            <li className="text-center py-10 text-sm text-ink-muted">수집·분석 중 (최대 30초)…</li>
          )}
          {!loading && filtered.length === 0 && (
            <li className="text-center py-10 text-sm text-ink-subtle">해당 조건의 종목 없음</li>
          )}
          {filtered.map((it) => {
            const open = expanded.has(it.symbol)
            return (
              <li key={it.symbol}>
                <button
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-inner/70 transition-colors"
                  onClick={() => toggle(it.symbol)}
                >
                  {open ? <ChevronDown size={15} className="text-ink-subtle" /> : <ChevronRight size={15} className="text-ink-subtle" />}
                  <Badge category={it.category} />
                  <Link
                    to={`/hanriver/stock/${it.symbol}`}
                    className="text-[14px] font-semibold text-ink hover:text-brand-600"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {it.name}
                  </Link>
                  <span className="text-[11px] text-ink-subtle font-mono">{it.symbol}</span>
                  {it.market && <span className="text-[10px] text-ink-subtle uppercase tracking-wider">{it.market}</span>}
                  <span className="flex-1" />
                  <span className="text-[13px] tabular-nums text-ink">{it.close.toLocaleString()}</span>
                  <span className="text-[13px] tabular-nums font-semibold text-up w-16 text-right">
                    +{it.change_pct.toFixed(2)}%
                  </span>
                  <span className="text-[12px] tabular-nums text-ink-muted w-20 text-right">
                    {formatWon(it.trading_value)}
                  </span>
                </button>

                {open && (
                  <div className="border-t border-surface-border px-5 py-4 space-y-4 bg-surface-inner/50">
                    {it.reason && (
                      <div>
                        <div className="eyebrow mb-1.5">AI 상승 이유</div>
                        <p className="text-[13px] text-ink leading-relaxed">{it.reason}</p>
                      </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <div className="eyebrow mb-1.5">관련 뉴스</div>
                        <ul className="text-[12px] space-y-1.5">
                          {it.news.length > 0 ? it.news.map((n, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-ink-subtle w-14 shrink-0">{n.office}</span>
                              <a href={n.url} target="_blank" rel="noreferrer" className="text-ink hover:text-brand-600 truncate">
                                {n.title}
                              </a>
                            </li>
                          )) : <li className="text-ink-subtle">(수집된 뉴스 없음)</li>}
                        </ul>
                      </div>
                      <div>
                        <div className="eyebrow mb-1.5">최근 7일 공시</div>
                        <ul className="text-[12px] space-y-1.5">
                          {it.disclosures.length > 0 ? it.disclosures.map((d, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-ink-subtle w-16 shrink-0">{d.rcept_dt}</span>
                              <a href={d.url} target="_blank" rel="noreferrer" className="text-ink hover:text-brand-600 truncate">
                                {d.report_name}
                              </a>
                            </li>
                          )) : <li className="text-ink-subtle">(공시 없음)</li>}
                        </ul>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-[12px] text-ink-muted pt-2 border-t border-surface-border">
                      <div>거래량: <span className="text-ink tabular-nums">{it.volume.toLocaleString()}</span></div>
                      <div>거래대금: <span className="text-ink tabular-nums">{it.trading_value.toLocaleString()}원</span></div>
                      <div>종가: <span className="text-ink tabular-nums">{it.close.toLocaleString()}원</span></div>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      </MacWindow>
    </div>
  )
}

function Badge({ category }: { category: 'limit_up' | 'surge' }) {
  if (category === 'limit_up') {
    return (
      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded border border-up/40 bg-up/10 text-up shrink-0 tracking-wider">
        상한
      </span>
    )
  }
  return (
    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded border border-amber-400/40 bg-amber-50 text-amber-700 shrink-0 tracking-wider">
      급등
    </span>
  )
}
