import { useState } from 'react'
import { hanriverApi } from '../../presenters/useHanriverPhase2'

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
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">복기 (타임머신 모드)</h1>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="005930" />
          <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <div />
          <button className="btn-primary" onClick={run} disabled={busy}>
            {busy ? '재현 중…' : '재현'}
          </button>
        </div>
      </section>

      {data && (
        <>
          <section className="bg-surface-card rounded-lg border border-surface-border p-4">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">
              {data.symbol} · {data.target_date} 당시 지표
            </h2>
            <pre className="text-xs text-slate-300 whitespace-pre-wrap">
              {JSON.stringify(data.indicators, null, 2)}
            </pre>
          </section>

          <section className="bg-surface-card rounded-lg border border-surface-border p-4">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">당시 주변 뉴스</h2>
            <ul className="divide-y divide-surface-border text-sm">
              {(data.news ?? []).map((n: any) => (
                <li key={n.id} className="py-2 flex items-center gap-3">
                  <span className="text-xs text-slate-500 w-32">{new Date(n.published_at).toLocaleString('ko-KR')}</span>
                  <span className="text-xs text-slate-400 w-12">{n.source}</span>
                  <a href={n.url} target="_blank" rel="noreferrer" className="text-slate-200 hover:text-brand-500 flex-1 truncate">{n.title}</a>
                </li>
              ))}
              {(data.news ?? []).length === 0 && <li className="text-xs text-slate-500 py-2">기록된 뉴스 없음</li>}
            </ul>
          </section>

          <section className="bg-surface-card rounded-lg border border-surface-border p-4">
            <h2 className="text-sm font-semibold text-slate-200 mb-3">당시 내 매매</h2>
            <ul className="divide-y divide-surface-border text-sm">
              {(data.trades ?? []).map((t: any) => (
                <li key={t.id} className="py-2 flex gap-3">
                  <span className="text-xs text-slate-500 w-32">{new Date(t.created_at).toLocaleString('ko-KR')}</span>
                  <span className={t.side === 'buy' ? 'text-red-400' : 'text-blue-400'}>{t.side}</span>
                  <span className="text-slate-200 tabular-nums">{t.quantity}주 @ {t.price.toLocaleString()}</span>
                </li>
              ))}
              {(data.trades ?? []).length === 0 && <li className="text-xs text-slate-500 py-2">당일 매매 없음</li>}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
