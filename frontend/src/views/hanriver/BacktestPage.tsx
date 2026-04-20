import { useEffect, useState } from 'react'
import { hanriverApi, type BacktestSummary } from '../../presenters/useHanriverPhase2'
import StockSearchInput from '../../components/StockSearchInput'
import MacWindow, { MacMiniCard } from '../../components/MacWindow'

export default function BacktestPage() {
  const [list, setList] = useState<BacktestSummary[]>([])
  const [form, setForm] = useState({
    name: '', symbol: '005930', strategy: 'ma_cross',
    short: 5, long: 20, period: 14, oversold: 30, overbought: 70,
    start_date: '2024-01-01', end_date: new Date().toISOString().slice(0, 10),
  })
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function load() { const r = await hanriverApi.listBacktest(); setList(r.data) }
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
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-ink tracking-tight">백테스트</h1>

      <MacWindow title="STRATEGY CONFIG">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
          <input className="input" placeholder="이름" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <StockSearchInput
            value={form.symbol}
            onChange={(v) => setForm((f) => ({ ...f, symbol: v }))}
            placeholder="종목명/코드"
          />
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
          <div className="grid grid-cols-4 gap-2 mt-3">
            <label className="text-xs text-ink-muted space-y-1">단기 MA
              <input className="input w-full" type="number" value={form.short} onChange={(e) => setForm({ ...form, short: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-ink-muted space-y-1">장기 MA
              <input className="input w-full" type="number" value={form.long} onChange={(e) => setForm({ ...form, long: Number(e.target.value) })} />
            </label>
          </div>
        )}
        {form.strategy === 'rsi' && (
          <div className="grid grid-cols-4 gap-2 mt-3">
            <label className="text-xs text-ink-muted space-y-1">period
              <input className="input w-full" type="number" value={form.period} onChange={(e) => setForm({ ...form, period: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-ink-muted space-y-1">oversold
              <input className="input w-full" type="number" value={form.oversold} onChange={(e) => setForm({ ...form, oversold: Number(e.target.value) })} />
            </label>
            <label className="text-xs text-ink-muted space-y-1">overbought
              <input className="input w-full" type="number" value={form.overbought} onChange={(e) => setForm({ ...form, overbought: Number(e.target.value) })} />
            </label>
          </div>
        )}
      </MacWindow>

      {result && (
        <MacWindow title="RESULT">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            {Object.entries(result.metrics).map(([k, v]) => (
              <MacMiniCard key={k} label={k} value={typeof v === 'number' ? v : String(v)} />
            ))}
          </div>
        </MacWindow>
      )}

      <MacWindow title="PREVIOUS RUNS" bodyClassName="p-0">
        <ul className="divide-y divide-surface-border text-sm">
          {list.map((b) => (
            <li key={b.id} className="px-4 py-3 grid grid-cols-6 gap-2 items-center">
              <span className="text-ink col-span-2 font-medium truncate">{b.name}</span>
              <span className="text-xs text-ink-muted">WR {(Number(b.metrics.win_rate) * 100).toFixed(1)}%</span>
              <span className="text-xs text-ink-muted">PF {b.metrics.profit_factor}</span>
              <span className="text-xs text-ink-muted">MDD {(Number(b.metrics.mdd) * 100).toFixed(1)}%</span>
              <span className="text-xs text-ink-subtle text-right">{new Date(b.created_at).toLocaleDateString('ko-KR')}</span>
            </li>
          ))}
          {list.length === 0 && <li className="px-4 py-4 text-xs text-ink-subtle">이전 결과 없음</li>}
        </ul>
      </MacWindow>
    </div>
  )
}
