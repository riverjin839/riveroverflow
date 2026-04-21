import {
  useKrIndices,
  useGlobalIndices,
  useFxCommodities,
  useSentiment,
  useSectorHeatmap,
  useHanriverNews,
  type Quote,
} from '../../presenters/useHanriver'
import MacWindow, { MacMiniCard } from '../../components/MacWindow'
import { Droplets, Wind, Gauge, Thermometer, Activity, Eye } from 'lucide-react'
import clsx from 'clsx'

function changeClass(ch: number | null | undefined): string {
  if (ch == null) return 'text-ink-subtle'
  if (ch > 0) return 'text-up'
  if (ch < 0) return 'text-down'
  return 'text-ink-muted'
}

function formatPrice(p: number): string {
  if (Math.abs(p) >= 1000) return p.toLocaleString('ko-KR', { maximumFractionDigits: 2 })
  return p.toLocaleString('ko-KR', { maximumFractionDigits: 3 })
}

function formatChange(ch: number | null | undefined): string {
  if (ch == null) return '-'
  const sign = ch > 0 ? '+' : ''
  return `${sign}${ch.toFixed(2)}%`
}

function todayKR(): string {
  return new Date().toLocaleDateString('ko-KR', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })
}

// HanriverDashboardPage — weather-theme 구조 매핑:
//   Hero(주요 지수) + Weather Details(환율/심리) + Hourly(해외 지수)
//   + 7-day(업종 히트맵) + Sunrise/Sunset(뉴스 핵심)
export default function HanriverDashboardPage() {
  const kr = useKrIndices()
  const global_ = useGlobalIndices()
  const fx = useFxCommodities()
  const sent = useSentiment()
  const sectors = useSectorHeatmap()
  const news = useHanriverNews(20)

  const kospi = kr.data.find((q) => q.code === 'KOSPI')

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <header>
        <h1 className="text-3xl font-bold text-ink tracking-tight">HANRIVER</h1>
        <p className="text-sm text-ink-muted mt-0.5">{todayKR()}</p>
      </header>

      {/* 상단 2컬럼: Hero(국내 지수) + Weather Details(환율/심리) */}
      <section className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <HeroKospi kospi={kospi} kr={kr.data} loading={kr.loading} />
        <MacWindow title="MARKET DETAILS" className="lg:col-span-3" bodyClassName="p-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {fx.data.slice(0, 6).map((q) => (
              <MacMiniCard
                key={q.code}
                icon={iconFor(q.code)}
                label={q.name}
                value={formatPrice(q.price)}
                hint={
                  <span className={changeClass(q.change_pct)}>
                    {formatChange(q.change_pct)}
                  </span>
                }
              />
            ))}
            {sent.data.slice(0, 3).map((q) => (
              <MacMiniCard
                key={q.code}
                icon={<Activity size={12} />}
                label={q.name}
                value={formatPrice(q.price)}
                hint={<span className="text-ink-subtle">{q.code}</span>}
              />
            ))}
          </div>
        </MacWindow>
      </section>

      {/* 해외 지수 — Hourly Forecast 레이아웃 재현 */}
      <MacWindow title="GLOBAL INDICES" bodyClassName="px-4 py-5">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {global_.data.map((q, i) => (
            <GlobalIndexCell key={q.code} quote={q} featured={i === 0} />
          ))}
          {global_.loading && global_.data.length === 0 &&
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-[92px] w-20 bg-surface-inner rounded-xl animate-pulse shrink-0" />
            ))}
        </div>
      </MacWindow>

      {/* 하단 2컬럼: 업종 히트맵(7-day 바) + 뉴스(Sunrise/Sunset) */}
      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <MacWindow title="SECTOR 7-DAY" className="lg:col-span-2">
          <SectorBarList quotes={sectors.data} loading={sectors.loading} />
        </MacWindow>

        <MacWindow title="NEWS & DISCLOSURES" bodyClassName="p-0">
          <ul className="divide-y divide-surface-border">
            {news.loading && news.data.length === 0
              ? Array.from({ length: 5 }).map((_, i) => (
                  <li key={i} className="h-12 bg-surface-inner/50 animate-pulse m-2" />
                ))
              : news.data.slice(0, 8).map((n) => (
                  <li key={n.id} className="px-4 py-2.5 hover:bg-surface-inner/60 transition-colors">
                    <a href={n.url} target="_blank" rel="noreferrer" className="block">
                      <div className="flex items-center gap-2 text-[11px] text-ink-subtle">
                        <span>{n.source}</span>
                        <span>·</span>
                        <span>{new Date(n.published_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</span>
                        {n.importance !== 'unknown' && (
                          <span className={clsx(
                            'ml-auto text-[10px] px-1.5 py-0.5 rounded border',
                            n.importance === 'high' && 'text-up border-up/30 bg-up/5',
                            n.importance === 'medium' && 'text-amber-600 border-amber-400/40 bg-amber-50',
                            n.importance === 'low' && 'text-ink-subtle border-surface-border',
                          )}>
                            {n.importance === 'high' ? '상' : n.importance === 'medium' ? '중' : '하'}
                          </span>
                        )}
                      </div>
                      <div className="text-[13px] text-ink mt-0.5 leading-snug line-clamp-2">
                        {n.title}
                      </div>
                    </a>
                  </li>
                ))}
          </ul>
        </MacWindow>
      </section>
    </div>
  )
}

// ── Hero: 대표 지수(KOSPI) 크게, 보조 3종 작게 ──────────────
function HeroKospi({
  kospi, kr, loading,
}: { kospi?: Quote; kr: Quote[]; loading: boolean }) {
  return (
    <section className="card lg:col-span-2 p-6 flex flex-col justify-between min-h-[280px]">
      <div>
        <div className="flex items-center gap-1.5 text-xs text-ink-muted">
          <span>●</span>
          <span className="tracking-wider">KOREA · KOSPI</span>
        </div>
        <div className="mt-4 flex items-start gap-2">
          <span className="text-6xl font-bold text-ink tabular-nums leading-none">
            {kospi ? kospi.price.toLocaleString('ko-KR', { maximumFractionDigits: 2 }) : '—'}
          </span>
          <span className="text-2xl text-ink-muted mt-1">pt</span>
        </div>
        <div className={clsx('mt-2 text-base font-semibold', changeClass(kospi?.change_pct))}>
          {kospi ? formatChange(kospi.change_pct) : '—'}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-6">
        {kr.filter((q) => q.code !== 'KOSPI').slice(0, 3).map((q) => (
          <div key={q.code} className="card-inner p-2.5">
            <div className="text-[11px] text-ink-muted truncate">{q.name}</div>
            <div className="text-sm font-semibold text-ink mt-0.5 tabular-nums">
              {formatPrice(q.price)}
            </div>
            <div className={clsx('text-[11px] tabular-nums mt-0.5', changeClass(q.change_pct))}>
              {formatChange(q.change_pct)}
            </div>
          </div>
        ))}
      </div>

      {kospi?.stale && (
        <div className="mt-3 text-[11px] text-amber-600">
          ⚠ stub 데이터 — 실데이터 연결 대기
        </div>
      )}
      {loading && kr.length === 0 && (
        <div className="mt-3 text-xs text-ink-subtle">로딩 중...</div>
      )}
    </section>
  )
}

// ── Hourly forecast 스타일 셀 (해외 지수) ───────────────────
function GlobalIndexCell({ quote, featured }: { quote: Quote; featured?: boolean }) {
  return (
    <div
      className={clsx(
        'shrink-0 w-[96px] rounded-xl px-2 py-2.5 flex flex-col items-center',
        featured
          ? 'bg-ink text-white shadow-mac'
          : 'bg-surface-inner border border-surface-border text-ink',
      )}
    >
      <div className={clsx('text-[11px] font-medium mb-1.5 truncate w-full text-center', featured ? 'text-white' : 'text-ink-muted')}>
        {quote.name}
      </div>
      <div className="text-[15px] font-semibold tabular-nums">
        {formatPrice(quote.price)}
      </div>
      <div
        className={clsx(
          'text-[11px] tabular-nums mt-0.5',
          featured
            ? quote.change_pct != null && quote.change_pct >= 0 ? 'text-red-300' : 'text-blue-300'
            : changeClass(quote.change_pct),
        )}
      >
        {formatChange(quote.change_pct)}
      </div>
    </div>
  )
}

// ── 섹터 7-day 바 스타일 리스트 ─────────────────────────────
function SectorBarList({ quotes, loading }: { quotes: Quote[]; loading: boolean }) {
  if (loading && quotes.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-8 bg-surface-inner rounded animate-pulse" />
        ))}
      </div>
    )
  }
  const maxAbs = Math.max(3, ...quotes.map((q) => Math.abs(q.change_pct ?? 0)))

  return (
    <ul className="space-y-2.5">
      {quotes.map((q) => {
        const chg = q.change_pct ?? 0
        const pctFill = Math.min(100, (Math.abs(chg) / maxAbs) * 100)
        const isUp = chg >= 0
        return (
          <li key={q.code} className="grid grid-cols-[80px_1fr_60px] items-center gap-3 text-sm">
            <span className="text-ink-muted truncate">{q.name}</span>
            <div className="relative h-2 bg-surface-border rounded-full overflow-hidden">
              <div
                className={clsx(
                  'absolute top-0 h-full rounded-full transition-[width] duration-500',
                  isUp ? 'bg-up' : 'bg-down',
                )}
                style={{
                  width: `${pctFill}%`,
                  left: isUp ? '50%' : `${50 - pctFill}%`,
                }}
              />
              <div className="absolute left-1/2 top-0 h-full w-px bg-surface-card" />
            </div>
            <span className={clsx('text-right tabular-nums text-xs', changeClass(chg))}>
              {formatChange(chg)}
            </span>
          </li>
        )
      })}
    </ul>
  )
}

function iconFor(code: string) {
  const m: Record<string, JSX.Element> = {
    USD_KRW: <Droplets size={12} />,
    DXY: <Gauge size={12} />,
    WTI: <Thermometer size={12} />,
    GOLD: <Activity size={12} />,
    BTC: <Wind size={12} />,
    US10Y: <Eye size={12} />,
  }
  return m[code] ?? <Activity size={12} />
}
