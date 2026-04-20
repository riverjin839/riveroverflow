import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { hanriverApi, type StockDetail, type FlowRow, type Disclosure } from '../../presenters/useHanriverPhase2'

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
    return () => {
      alive = false
    }
  }, [symbol])

  if (loading) return <div className="text-slate-400">로딩 중…</div>
  if (err) return <div className="text-red-400">{err}</div>
  if (!detail) return null

  const ind = detail.indicators as Record<string, any>
  const vsa = (ind.vsa ?? {}) as Record<string, any>

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">
            {detail.name} <span className="text-slate-500">({detail.symbol})</span>
          </h1>
          <div className="text-sm text-slate-300 mt-1">
            {detail.price.toLocaleString()}{' '}
            <span className={detail.change_pct > 0 ? 'text-red-400' : detail.change_pct < 0 ? 'text-blue-400' : 'text-slate-400'}>
              {detail.change_pct > 0 ? '+' : ''}{detail.change_pct.toFixed(2)}%
            </span>
            <span className="text-slate-500 ml-3 text-xs">거래량 {detail.volume.toLocaleString()}</span>
          </div>
        </div>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-surface-card rounded-lg border border-surface-border p-4">
          <h2 className="text-sm font-semibold text-slate-200 mb-3">기술적 지표</h2>
          <dl className="text-sm divide-y divide-surface-border">
            <Row label="MA20" value={ind.ma20} />
            <Row label="MA60" value={ind.ma60} />
            <Row label="MA120" value={ind.ma120} />
            <Row label="RSI(14)" value={ind.rsi14} />
            <Row label="MACD" value={ind.macd} />
            <Row label="MACD hist" value={ind.macd_hist} />
            <Row label="볼린저 상단" value={ind.bb_upper} />
            <Row label="볼린저 하단" value={ind.bb_lower} />
          </dl>
        </div>

        <div className="bg-surface-card rounded-lg border border-surface-border p-4">
          <h2 className="text-sm font-semibold text-slate-200 mb-3">VSA 시그널 (최근 봉)</h2>
          <ul className="text-sm space-y-2">
            <VsaItem label="Sign of Strength (매집)" active={!!vsa.sos} color="text-red-300" />
            <VsaItem label="Sign of Weakness (분배)" active={!!vsa.sow} color="text-blue-300" />
            <VsaItem label="Upthrust (고점 반락)" active={!!vsa.upthrust} color="text-amber-300" />
            <VsaItem label="Test (눌림 확인)" active={!!vsa.test} color="text-emerald-300" />
          </ul>
          <div className="text-xs text-slate-500 mt-3">
            거래량 배수: {vsa.vol_ratio?.toFixed?.(2) ?? '-'} · 종가 위치: {vsa.close_pos?.toFixed?.(2) ?? '-'}
          </div>
        </div>

        <div className="bg-surface-card rounded-lg border border-surface-border p-4">
          <h2 className="text-sm font-semibold text-slate-200 mb-3">공매도 잔고</h2>
          {short && Object.keys(short).length ? (
            <dl className="text-sm divide-y divide-surface-border">
              <Row label="잔고 수량" value={short.balance_qty} />
              <Row label="잔고 금액" value={short.balance_value} />
              <Row label="비중(%)" value={short.ratio} />
            </dl>
          ) : (
            <div className="text-xs text-slate-500">데이터 없음</div>
          )}
        </div>
      </section>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">수급 (최근 {flows.length}일)</h2>
        <div className="overflow-x-auto">
          <table className="text-xs w-full">
            <thead className="text-slate-500">
              <tr>
                <th className="text-left py-1">날짜</th>
                <th className="text-right py-1">외국인 순매수</th>
                <th className="text-right py-1">기관 순매수</th>
                <th className="text-right py-1">개인 순매수</th>
              </tr>
            </thead>
            <tbody>
              {flows.slice().reverse().map((f) => (
                <tr key={f.trade_date} className="border-t border-surface-border">
                  <td className="py-1 text-slate-400">{f.trade_date}</td>
                  <td className={`py-1 text-right tabular-nums ${f.foreign_net >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                    {f.foreign_net.toLocaleString()}
                  </td>
                  <td className={`py-1 text-right tabular-nums ${f.institution_net >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                    {f.institution_net.toLocaleString()}
                  </td>
                  <td className={`py-1 text-right tabular-nums ${f.individual_net >= 0 ? 'text-red-400' : 'text-blue-400'}`}>
                    {f.individual_net.toLocaleString()}
                  </td>
                </tr>
              ))}
              {flows.length === 0 && (
                <tr><td colSpan={4} className="text-center py-4 text-slate-500">수급 데이터 없음</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">공시 (최근 30일)</h2>
        <ul className="text-sm divide-y divide-surface-border">
          {disclosures.map((d) => (
            <li key={d.rcept_no} className="py-2 flex items-center gap-3">
              <span className="text-xs text-slate-500 w-20 shrink-0">{d.rcept_dt}</span>
              <a href={d.url} target="_blank" rel="noreferrer" className="text-slate-200 hover:text-brand-500 flex-1 truncate">
                {d.report_name}
              </a>
            </li>
          ))}
          {disclosures.length === 0 && <li className="text-xs text-slate-500 py-2">공시 없음</li>}
        </ul>
      </section>
    </div>
  )
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex justify-between py-1.5">
      <span className="text-slate-500">{label}</span>
      <span className="text-slate-200 tabular-nums">
        {typeof value === 'number' ? value.toFixed(2) : String(value ?? '-')}
      </span>
    </div>
  )
}

function VsaItem({ label, active, color }: { label: string; active: boolean; color: string }) {
  return (
    <li className="flex items-center justify-between">
      <span className="text-slate-300">{label}</span>
      <span className={active ? color + ' font-semibold' : 'text-slate-600'}>
        {active ? '● 포착' : '○'}
      </span>
    </li>
  )
}
