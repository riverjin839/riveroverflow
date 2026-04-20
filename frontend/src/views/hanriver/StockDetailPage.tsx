import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { hanriverApi, type StockDetail, type FlowRow, type Disclosure } from '../../presenters/useHanriverPhase2'
import MacWindow, { MacMiniCard } from '../../components/MacWindow'

export default function StockDetailPage() {
  const { symbol: pathSym } = useParams()
  const [sp] = useSearchParams()
  const symbol = pathSym ?? sp.get('symbol') ?? '005930'

  const [detail, setDetail] = useState<StockDetail | null>(null)
  const [flows, setFlows] = useState<FlowRow[]>([])
  const [disclosures, setDisclosures] = useState<Disclosure[]>([])
  const [short, setShort] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setErr(null)
    Promise.all([
      hanriverApi.stockDetail(symbol),
      hanriverApi.flow(symbol, 30),
      hanriverApi.stockDisclosures(symbol, 30),
      hanriverApi.short(symbol),
    ])
      .then(([d, f, disc, s]) => {
        if (!alive) return
        setDetail(d.data)
        setFlows(f.data)
        setDisclosures(disc.data)
        setShort(s.data)
      })
      .catch((e) => alive && setErr((e as Error).message))
      .finally(() => alive && setLoading(false))
    return () => { alive = false }
  }, [symbol])

  if (loading) return <div className="text-ink-muted text-sm">로딩 중…</div>
  if (err) return <div className="text-up text-sm">{err}</div>
  if (!detail) return null

  const ind = (detail.indicators ?? {}) as Record<string, any>
  const vsa = (ind.vsa ?? {}) as Record<string, any>

  return (
    <div className="space-y-5">
      {/* Hero */}
      <section className="card p-6">
        <div className="eyebrow">STOCK · {detail.symbol}</div>
        <div className="mt-3 flex items-baseline gap-3">
          <h1 className="text-3xl font-bold text-ink tracking-tight">{detail.name}</h1>
        </div>
        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-5xl font-bold text-ink tabular-nums">{detail.price.toLocaleString()}</span>
          <span className={clsx(
            'text-lg font-semibold',
            detail.change_pct > 0 ? 'text-up' : detail.change_pct < 0 ? 'text-down' : 'text-ink-muted',
          )}>
            {detail.change_pct > 0 ? '+' : ''}{detail.change_pct.toFixed(2)}%
          </span>
          <span className="text-sm text-ink-subtle ml-3">거래량 {detail.volume.toLocaleString()}</span>
        </div>
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <MacWindow title="INDICATORS">
          <div className="grid grid-cols-2 gap-3">
            <MacMiniCard label="MA20" value={formatNum(ind.ma20)} />
            <MacMiniCard label="MA60" value={formatNum(ind.ma60)} />
            <MacMiniCard label="MA120" value={formatNum(ind.ma120)} />
            <MacMiniCard label="RSI(14)" value={formatNum(ind.rsi14)} />
            <MacMiniCard label="MACD" value={formatNum(ind.macd)} />
            <MacMiniCard label="MACD hist" value={formatNum(ind.macd_hist)} />
            <MacMiniCard label="BB 상단" value={formatNum(ind.bb_upper)} />
            <MacMiniCard label="BB 하단" value={formatNum(ind.bb_lower)} />
          </div>
        </MacWindow>

        <MacWindow title="VSA SIGNALS">
          <ul className="space-y-2.5 text-sm">
            <VsaItem label="Sign of Strength (매집)" active={!!vsa.sos} color="text-up" />
            <VsaItem label="Sign of Weakness (분배)" active={!!vsa.sow} color="text-down" />
            <VsaItem label="Upthrust (고점 반락)" active={!!vsa.upthrust} color="text-amber-600" />
            <VsaItem label="Test (눌림 확인)" active={!!vsa.test} color="text-emerald-600" />
          </ul>
          <div className="mt-4 pt-3 border-t border-surface-border text-[11px] text-ink-subtle">
            거래량 배수: <span className="text-ink">{vsa.vol_ratio?.toFixed?.(2) ?? '-'}</span>
            {' · '}
            종가 위치: <span className="text-ink">{vsa.close_pos?.toFixed?.(2) ?? '-'}</span>
          </div>
        </MacWindow>

        <MacWindow title="SHORT BALANCE">
          {short && Object.keys(short).length ? (
            <div className="space-y-2.5 text-sm">
              <Row label="잔고 수량" value={short.balance_qty} />
              <Row label="잔고 금액" value={short.balance_value} />
              <Row label="비중(%)" value={short.ratio} />
            </div>
          ) : (
            <div className="text-xs text-ink-subtle">데이터 없음</div>
          )}
        </MacWindow>
      </section>

      <MacWindow title={`FLOW · ${flows.length}일`} bodyClassName="p-0">
        <div className="overflow-x-auto">
          <table className="text-[12px] w-full">
            <thead className="bg-surface-inner text-ink-muted">
              <tr>
                <th className="text-left p-3 font-medium">날짜</th>
                <th className="text-right p-3 font-medium">외국인</th>
                <th className="text-right p-3 font-medium">기관</th>
                <th className="text-right p-3 font-medium">개인</th>
              </tr>
            </thead>
            <tbody>
              {flows.slice().reverse().map((f) => (
                <tr key={f.trade_date} className="border-t border-surface-border">
                  <td className="p-3 text-ink-muted">{f.trade_date}</td>
                  <td className={clsx('p-3 text-right tabular-nums', f.foreign_net >= 0 ? 'text-up' : 'text-down')}>
                    {f.foreign_net.toLocaleString()}
                  </td>
                  <td className={clsx('p-3 text-right tabular-nums', f.institution_net >= 0 ? 'text-up' : 'text-down')}>
                    {f.institution_net.toLocaleString()}
                  </td>
                  <td className={clsx('p-3 text-right tabular-nums', f.individual_net >= 0 ? 'text-up' : 'text-down')}>
                    {f.individual_net.toLocaleString()}
                  </td>
                </tr>
              ))}
              {flows.length === 0 && (
                <tr><td colSpan={4} className="text-center py-6 text-ink-subtle">수급 데이터 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </MacWindow>

      <MacWindow title="DISCLOSURES · 최근 30일">
        <ul className="divide-y divide-surface-border text-sm">
          {disclosures.map((d) => (
            <li key={d.rcept_no} className="py-2 flex items-center gap-3">
              <span className="text-xs text-ink-subtle w-20 shrink-0">{d.rcept_dt}</span>
              <a href={d.url} target="_blank" rel="noreferrer" className="text-ink hover:text-brand-600 flex-1 truncate">
                {d.report_name}
              </a>
            </li>
          ))}
          {disclosures.length === 0 && <li className="text-xs text-ink-subtle py-2">공시 없음</li>}
        </ul>
      </MacWindow>
    </div>
  )
}

function formatNum(v: unknown): string {
  if (typeof v === 'number') return v.toFixed(2)
  return String(v ?? '-')
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex justify-between">
      <span className="text-ink-muted">{label}</span>
      <span className="text-ink tabular-nums">
        {typeof value === 'number' ? value.toLocaleString() : String(value ?? '-')}
      </span>
    </div>
  )
}

function VsaItem({ label, active, color }: { label: string; active: boolean; color: string }) {
  return (
    <li className="flex items-center justify-between">
      <span className="text-ink-muted">{label}</span>
      <span className={active ? color + ' font-semibold' : 'text-ink-subtle'}>
        {active ? '● 포착' : '○'}
      </span>
    </li>
  )
}
