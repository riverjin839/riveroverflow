import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { hanriverApi, type AiSignal } from '../../presenters/useHanriverPhase2'
import StockSearchInput from '../../components/StockSearchInput'
import MacWindow from '../../components/MacWindow'

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
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? (e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-2xl font-bold text-ink tracking-tight">AI 매매 시그널</h1>
        <p className="text-xs text-ink-muted mt-1">룰(VSA/RSI/MA 정배열) + Claude 자연어 근거</p>
      </header>

      <MacWindow title="GENERATE SIGNAL">
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
        {err && <div className="text-up text-xs mt-2">{err}</div>}
      </MacWindow>

      <section className="space-y-3">
        {signals.length === 0 && (
          <div className="text-center text-ink-subtle py-10 text-sm card">
            시그널 없음 — 위에서 제안을 생성하세요.
          </div>
        )}
        {signals.map((s) => (
          <MacWindow key={s.id} title={`${s.mode === 'day' ? 'DAY' : 'SWING'} · ${s.symbol}`}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <Link to={`/hanriver/stock/${s.symbol}`} className="text-lg font-semibold text-ink hover:text-brand-600">
                  {s.name}
                </Link>
                <div className="text-[11px] text-ink-muted mt-0.5">
                  확신도 {(s.confidence * 100).toFixed(0)}%
                  <span className="ml-2 text-ink-subtle">{new Date(s.created_at).toLocaleString('ko-KR')}</span>
                </div>
              </div>
              <SignalBadge signal={s.signal} />
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3">
              <Stat label="진입" value={s.entry_price} />
              <Stat label="손절" value={s.stop_loss} color="text-down" />
              <Stat label="익절" value={s.take_profit} color="text-up" />
            </div>
            <details className="mt-3">
              <summary className="cursor-pointer text-xs text-ink-muted hover:text-ink">근거 리포트</summary>
              <pre className="whitespace-pre-wrap font-sans mt-2 text-[13px] text-ink leading-relaxed">
                {s.rationale}
              </pre>
            </details>
          </MacWindow>
        ))}
      </section>
    </div>
  )
}

function SignalBadge({ signal }: { signal: string }) {
  const map: Record<string, string> = {
    buy: 'bg-up/10 text-up border-up/30',
    sell: 'bg-down/10 text-down border-down/30',
    hold: 'bg-surface-inner text-ink-muted border-surface-border',
  }
  const label: Record<string, string> = { buy: '매수 제안', sell: '매도 제안', hold: '관망' }
  return (
    <span className={clsx('text-[11px] font-semibold px-2.5 py-1 rounded-full border', map[signal] ?? map.hold)}>
      {label[signal] ?? signal}
    </span>
  )
}

function Stat({ label, value, color }: { label: string; value: number | null; color?: string }) {
  return (
    <div className="card-inner p-2.5">
      <div className="text-[11px] text-ink-muted">{label}</div>
      <div className={clsx('mt-1 font-semibold tabular-nums', color ?? 'text-ink')}>
        {value != null ? value.toLocaleString() : '-'}
      </div>
    </div>
  )
}
