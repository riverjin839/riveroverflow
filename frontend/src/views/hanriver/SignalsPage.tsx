import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { hanriverApi, type AiSignal } from '../../presenters/useHanriverPhase2'
import StockSearchInput from '../../components/StockSearchInput'

export default function SignalsPage() {
  const [signals, setSignals] = useState<AiSignal[]>([])
  const [form, setForm] = useState({ symbol: '005930', mode: 'day' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function refresh() {
    const r = await hanriverApi.listSignals()
    setSignals(r.data)
  }

  useEffect(() => { refresh() }, [])

  async function generate() {
    setBusy(true)
    setErr(null)
    try {
      await hanriverApi.generateSignal(form.symbol, form.mode)
      await refresh()
    } catch (e) {
      setErr((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">AI 매매 시그널</h1>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">시그널 생성</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <StockSearchInput
            value={form.symbol}
            onChange={(v) => setForm((f) => ({ ...f, symbol: v }))}
            placeholder="종목명/코드 검색"
          />
          <select className="input" value={form.mode} onChange={(e) => setForm({ ...form, mode: e.target.value })}>
            <option value="day">당일 매매 (데이)</option>
            <option value="swing">주간 매매 (눌림 스윙)</option>
          </select>
          <div />
          <button className="btn-primary" onClick={generate} disabled={busy}>
            {busy ? '생성 중…' : '제안 생성'}
          </button>
        </div>
        {err && <div className="text-red-400 text-xs mt-2">{err}</div>}
      </section>

      <section className="space-y-3">
        {signals.map((s) => (
          <article key={s.id} className="bg-surface-card rounded-lg border border-surface-border p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link to={`/hanriver/stock/${s.symbol}`} className="text-base font-semibold text-brand-500">
                  {s.name} ({s.symbol})
                </Link>
                <div className="text-xs text-slate-400 mt-0.5">
                  {s.mode === 'day' ? '데이' : '스윙'} · 확신도 {(s.confidence * 100).toFixed(0)}%
                  <span className="ml-2 text-slate-500">{new Date(s.created_at).toLocaleString('ko-KR')}</span>
                </div>
              </div>
              <SignalBadge signal={s.signal} />
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
              <Stat label="진입" value={s.entry_price} />
              <Stat label="손절" value={s.stop_loss} color="text-blue-300" />
              <Stat label="익절" value={s.take_profit} color="text-red-300" />
            </div>
            <details className="mt-3 text-sm text-slate-200">
              <summary className="cursor-pointer text-slate-400">근거 리포트</summary>
              <pre className="whitespace-pre-wrap font-sans mt-2 text-slate-200 leading-relaxed">
                {s.rationale}
              </pre>
            </details>
          </article>
        ))}
        {signals.length === 0 && (
          <div className="text-center text-slate-500 py-8 text-sm">시그널 없음 — 위에서 제안을 생성하세요.</div>
        )}
      </section>
    </div>
  )
}

function SignalBadge({ signal }: { signal: string }) {
  const map: Record<string, string> = {
    buy: 'bg-red-500/20 text-red-300 border-red-500/40',
    sell: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    hold: 'bg-slate-600/30 text-slate-300 border-slate-500/40',
  }
  const label: Record<string, string> = { buy: '매수 제안', sell: '매도 제안', hold: '관망' }
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded border ${map[signal] ?? map.hold}`}>
      {label[signal] ?? signal}
    </span>
  )
}

function Stat({ label, value, color }: { label: string; value: number | null; color?: string }) {
  return (
    <div className="bg-surface rounded border border-surface-border p-2">
      <div className="text-slate-500">{label}</div>
      <div className={`mt-1 font-semibold ${color ?? 'text-slate-200'} tabular-nums`}>
        {value != null ? value.toLocaleString() : '-'}
      </div>
    </div>
  )
}
