import { useEffect, useState } from 'react'
import { hanriverApi, type BacktestSummary } from '../../presenters/useHanriverPhase2'

export default function BacktestPage() {
  const [list, setList] = useState<BacktestSummary[]>([])
  const [form, setForm] = useState({
    name: '', symbol: '005930', strategy: 'ma_cross',
    short: 5, long: 20, period: 14, oversold: 30, overbought: 70,
    start_date: '2024-01-01', end_date: new Date().toISOString().slice(0, 10),
  })
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    const r = await hanriverApi.listBacktest()
    setList(r.data)
  }
  useEffect(() => { load() }, [])

  async function run() {
    setBusy(true)
    try {
      const params: Record<string, unknown> =
        form.strategy === 'ma_cross' ? { short: form.short, long: form.long }
          : form.strategy === 'rsi' ? { period: form.period, oversold: form.oversold, overbought: form.overbought }
            : {}
      const r = await hanriverApi.runBacktest({
        name: form.name || `${form.strategy}_${form.symbol}`,
        symbol: form.symbol,
        strategy: form.strategy,
        params,
        start_date: form.start_date,
        end_date: form.end_date,
      })
      setResult(r.data)
      await load()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">백테스트</h1>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          <input className="input" placeholder="이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" placeholder="종목 코드" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} />
          <select className="input" value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })}>
            <option value="ma_cross">MA Cross</option>
            <option value="rsi">RSI</option>
            <option value="vsa">VSA</option>
          </select>
          <input className="input" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
          <input className="input" type="date" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
          <button className="btn-primary" onClick={run} disabled={busy}>{busy ? '실행 중…' : '실행'}</button>
        </div>
        {form.strategy === 'ma_cross' && (
          <div className="grid grid-cols-4 gap-2 mt-2">
            <label className="text-xs text-slate-500">단기 MA
              <input className="input" type="number" value={form.short} onChange={(e) => setForm({ ...form, short: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-slate-500">장기 MA
              <input className="input" type="number" value={form.long} onChange={(e) => setForm({ ...form, long: Number(e.target.value) })} />
            </label>
          </div>
        )}
        {form.strategy === 'rsi' && (
          <div className="grid grid-cols-4 gap-2 mt-2">
            <label className="text-xs text-slate-500">period
              <input className="input" type="number" value={form.period} onChange={(e) => setForm({ ...form, period: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-slate-500">oversold
              <input className="input" type="number" value={form.oversold} onChange={(e) => setForm({ ...form, oversold: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-slate-500">overbought
              <input className="input" type="number" value={form.overbought} onChange={(e) => setForm({ ...form, overbought: Number(e.target.value) })} />
            </label>
          </div>
        )}
      </section>

      {result && (
        <section className="bg-surface-card rounded-lg border border-surface-border p-4">
          <h2 className="text-sm font-semibold text-slate-200 mb-3">결과</h2>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-sm">
            {Object.entries(result.metrics).map(([k, v]) => (
              <div key={k} className="bg-surface rounded border border-surface-border p-2">
                <div className="text-xs text-slate-500">{k}</div>
                <div className="text-slate-200 tabular-nums mt-1">{typeof v === 'number' ? v : String(v)}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">이전 결과</h2>
        <ul className="divide-y divide-surface-border text-sm">
          {list.map((b) => (
            <li key={b.id} className="py-2 grid grid-cols-6 gap-2">
              <span className="text-slate-200 col-span-2 truncate">{b.name}</span>
              <span className="text-slate-500 text-xs">WR {(Number(b.metrics.win_rate) * 100).toFixed(1)}%</span>
              <span className="text-slate-500 text-xs">PF {b.metrics.profit_factor}</span>
              <span className="text-slate-500 text-xs">MDD {(Number(b.metrics.mdd) * 100).toFixed(1)}%</span>
              <span className="text-slate-500 text-xs text-right">{new Date(b.created_at).toLocaleDateString('ko-KR')}</span>
            </li>
          ))}
          {list.length === 0 && <li className="text-xs text-slate-500 py-3">이전 결과 없음</li>}
        </ul>
      </section>
    </div>
  )
}
