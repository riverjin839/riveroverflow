import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, Plus } from 'lucide-react'
import { hanriverApi, type WatchlistItem, type AlertItem } from '../../presenters/useHanriverPhase2'
import StockSearchInput from '../../components/StockSearchInput'

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [form, setForm] = useState({ symbol: '', name: '', tags: '', memo: '' })
  const [alertForm, setAlertForm] = useState({ symbol: '', rule_type: 'price_above', threshold: '' })

  async function load() {
    const [w, a] = await Promise.all([hanriverApi.watchlist(), hanriverApi.alerts()])
    setItems(w.data)
    setAlerts(a.data)
  }

  useEffect(() => {
    load()
  }, [])

  async function add() {
    if (!form.symbol || !form.name) return
    await hanriverApi.watchlistAdd(form)
    setForm({ symbol: '', name: '', tags: '', memo: '' })
    await load()
  }

  async function remove(sym: string) {
    await hanriverApi.watchlistRemove(sym)
    await load()
  }

  async function addAlert() {
    if (!alertForm.symbol) return
    await hanriverApi.alertsAdd({
      symbol: alertForm.symbol,
      rule_type: alertForm.rule_type,
      threshold: alertForm.threshold ? Number(alertForm.threshold) : null,
    })
    setAlertForm({ symbol: '', rule_type: 'price_above', threshold: '' })
    await load()
  }

  async function removeAlert(id: number) {
    await hanriverApi.alertsRemove(id)
    await load()
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">관심 종목 & 알림</h1>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">관심 종목</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2 mb-3">
          <StockSearchInput
            value={form.symbol}
            onChange={(v) => setForm((f) => ({ ...f, symbol: v }))}
            onSelect={(it) => setForm((f) => ({ ...f, symbol: it.symbol, name: it.name }))}
            placeholder="종목명/코드 검색"
          />
          <input className="input" placeholder="삼성전자" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="input" placeholder="tags (csv)" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
          <input className="input md:col-span-1" placeholder="memo" value={form.memo} onChange={(e) => setForm({ ...form, memo: e.target.value })} />
          <button onClick={add} className="btn-primary"><Plus size={14} /> 추가</button>
        </div>
        <ul className="divide-y divide-surface-border">
          {items.map((it) => (
            <li key={it.id} className="py-2 flex items-center gap-3 text-sm">
              <Link to={`/hanriver/stock/${it.symbol}`} className="text-brand-500 w-24">{it.symbol}</Link>
              <span className="text-slate-200 flex-1">{it.name}</span>
              <span className="text-xs text-slate-500">{it.tags}</span>
              <button onClick={() => remove(it.symbol)} className="text-slate-500 hover:text-red-400">
                <Trash2 size={14} />
              </button>
            </li>
          ))}
          {items.length === 0 && <li className="text-xs text-slate-500 py-3">관심 종목 없음</li>}
        </ul>
      </section>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">알림 규칙</h2>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2 mb-3">
          <StockSearchInput
            value={alertForm.symbol}
            onChange={(v) => setAlertForm((f) => ({ ...f, symbol: v }))}
            placeholder="종목명/코드 검색"
          />
          <select className="input" value={alertForm.rule_type} onChange={(e) => setAlertForm({ ...alertForm, rule_type: e.target.value })}>
            <option value="price_above">가격 이상</option>
            <option value="price_below">가격 이하</option>
            <option value="volume_spike">거래량 급증</option>
            <option value="flow_reversal">수급 전환</option>
          </select>
          <input className="input" placeholder="기준값" type="number" value={alertForm.threshold} onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })} />
          <div className="md:col-span-1" />
          <button onClick={addAlert} className="btn-primary"><Plus size={14} /> 추가</button>
        </div>
        <ul className="divide-y divide-surface-border">
          {alerts.map((a) => (
            <li key={a.id} className="py-2 flex items-center gap-3 text-sm">
              <span className="text-slate-300 w-24">{a.symbol}</span>
              <span className="text-slate-400 w-32">{a.rule_type}</span>
              <span className="text-slate-200 tabular-nums">{a.threshold ?? '-'}</span>
              <span className="flex-1" />
              <button onClick={() => removeAlert(a.id)} className="text-slate-500 hover:text-red-400">
                <Trash2 size={14} />
              </button>
            </li>
          ))}
          {alerts.length === 0 && <li className="text-xs text-slate-500 py-3">알림 규칙 없음</li>}
        </ul>
        <p className="text-xs text-slate-500 mt-3">
          ※ 알림 트리거 엔진은 향후 Phase 5 에서 실시간 루프에 붙여 조건 도달 시 텔레그램으로 발송.
        </p>
      </section>
    </div>
  )
}
