import { useState } from 'react'
import { hanriverApi } from '../../presenters/useHanriverPhase2'
import StockSearchInput from '../../components/StockSearchInput'
import MacWindow from '../../components/MacWindow'

export default function ReplayPage() {
  const [symbol, setSymbol] = useState('005930')
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [data, setData] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    try {
      const r = await hanriverApi.replay(symbol, date)
      setData(r.data)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-ink tracking-tight">복기 · 타임머신</h1>

      <MacWindow title="REPLAY SETTINGS">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <StockSearchInput value={symbol} onChange={setSymbol} placeholder="종목명/코드 검색" />
          <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <div />
          <button className="btn-primary" onClick={run} disabled={busy}>
            {busy ? '재현 중…' : '재현'}
          </button>
        </div>
      </MacWindow>

      {data && (
        <>
          <MacWindow title={`INDICATORS · ${data.symbol} · ${data.target_date}`}>
            <pre className="text-[12px] text-ink whitespace-pre-wrap font-mono">
              {JSON.stringify(data.indicators, null, 2)}
            </pre>
          </MacWindow>

          <MacWindow title="NEWS AT THE TIME" bodyClassName="p-0">
            <ul className="divide-y divide-surface-border">
              {(data.news ?? []).map((n: any) => (
                <li key={n.id} className="px-4 py-2 flex items-center gap-3 text-sm">
                  <span className="text-[11px] text-ink-subtle w-32">{new Date(n.published_at).toLocaleString('ko-KR')}</span>
                  <span className="text-[11px] text-ink-muted w-12">{n.source}</span>
                  <a href={n.url} target="_blank" rel="noreferrer" className="text-ink hover:text-brand-600 flex-1 truncate">{n.title}</a>
                </li>
              ))}
              {(data.news ?? []).length === 0 && <li className="px-4 py-4 text-xs text-ink-subtle">기록된 뉴스 없음</li>}
            </ul>
          </MacWindow>

          <MacWindow title="MY TRADES" bodyClassName="p-0">
            <ul className="divide-y divide-surface-border">
              {(data.trades ?? []).map((t: any) => (
                <li key={t.id} className="px-4 py-2 flex gap-3 text-sm">
                  <span className="text-[11px] text-ink-subtle w-32">{new Date(t.created_at).toLocaleString('ko-KR')}</span>
                  <span className={t.side === 'buy' ? 'text-up font-medium' : 'text-down font-medium'}>{t.side}</span>
                  <span className="text-ink tabular-nums">{t.quantity}주 @ {t.price.toLocaleString()}</span>
                </li>
              ))}
              {(data.trades ?? []).length === 0 && <li className="px-4 py-4 text-xs text-ink-subtle">당일 매매 없음</li>}
            </ul>
          </MacWindow>
        </>
      )}
    </div>
  )
}
