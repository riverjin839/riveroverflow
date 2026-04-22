import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Sparkles, ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import api from '../../presenters/api'
import MacWindow, { MacMiniCard, MacProgressBar } from '../../components/MacWindow'

type Candidate = {
  symbol: string
  name: string
  market: string
  close: number
  change_pct: number
  score: number
  features: Record<string, number | null>
  reasons: string[]
  commentary: string | null
}

type Payload = {
  universe_kind: string
  universe_size: number
  candidate_count: number
  items: Candidate[]
}

export default function PatternScannerPage() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [opts, setOpts] = useState({ kind: 'kospi', min_score: 60, max_results: 20, enable_llm: true })
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  async function run() {
    setLoading(true)
    setErr(null)
    try {
      const r = await api.post<Payload>('/api/v1/hanriver/pattern-scan', opts)
      setData(r.data)
    } catch (e: any) {
      setErr(e?.response?.data?.detail ?? (e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  function toggle(s: string) {
    setExpanded((p) => {
      const n = new Set(p)
      n.has(s) ? n.delete(s) : n.add(s)
      return n
    })
  }

  return (
    <div className="space-y-5">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-ink tracking-tight flex items-center gap-2">
            <Sparkles size={22} className="text-brand-600" />
            선취매 패턴 스캐너
          </h1>
          <p className="text-xs text-ink-muted mt-1">
            타이트 베이스 + 조용한 매집 + VSA SOS + 돌파 임박 — 다요인 스코어링
          </p>
        </div>
      </header>

      <MacWindow title="SCAN CONFIG">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
          <select className="input" value={opts.kind} onChange={(e) => setOpts({ ...opts, kind: e.target.value })}>
            <option value="kospi">KOSPI 시총 상위</option>
            <option value="kosdaq">KOSDAQ 시총 상위</option>
            <option value="all">전체 (상위 500)</option>
          </select>
          <label className="text-xs text-ink-muted">
            최소 점수
            <input
              type="number" min={40} max={95}
              className="input w-full mt-1"
              value={opts.min_score}
              onChange={(e) => setOpts({ ...opts, min_score: Number(e.target.value) })}
            />
          </label>
          <label className="text-xs text-ink-muted">
            최대 결과 수
            <input
              type="number" min={5} max={50}
              className="input w-full mt-1"
              value={opts.max_results}
              onChange={(e) => setOpts({ ...opts, max_results: Number(e.target.value) })}
            />
          </label>
          <label className="text-xs text-ink-muted flex items-center gap-2 mt-5">
            <input
              type="checkbox" checked={opts.enable_llm}
              onChange={(e) => setOpts({ ...opts, enable_llm: e.target.checked })}
            />
            AI 해설 (상위 5)
          </label>
          <button className="btn-primary" onClick={run} disabled={loading}>
            {loading ? '스캔 중… (최대 60초)' : '스캔 실행'}
          </button>
        </div>
        <p className="text-[11px] text-ink-subtle mt-3">
          ※ 스캔은 종목당 60일 OHLCV 를 조회하므로 유니버스 크기에 따라 30~90초가 걸릴 수 있습니다.
        </p>
      </MacWindow>

      {err && <div className="text-up text-sm">{err}</div>}

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MacMiniCard label="유니버스" value={`${data.universe_size} 종목`} hint={data.universe_kind} />
          <MacMiniCard
            label={`합격 (≥${opts.min_score})`}
            value={<span className="text-brand-600">{data.candidate_count}</span>}
          />
          <MacMiniCard label="노출" value={`${data.items.length}건`} />
          <MacMiniCard
            label="AI 해설"
            value={opts.enable_llm ? '상위 5' : '비활성'}
            hint="Claude 비용 절감"
          />
        </div>
      )}

      <MacWindow title="CANDIDATES" bodyClassName="p-0">
        {!data && !loading && (
          <div className="py-10 text-center text-ink-subtle text-sm">
            위의 '스캔 실행' 버튼을 눌러 선취매 후보를 탐색하세요.
          </div>
        )}
        {loading && !data && (
          <div className="py-10 text-center text-ink-muted text-sm">
            종목별 OHLCV 수집 + 특성 계산 중… (진행 중 병렬 처리)
          </div>
        )}
        <ul className="divide-y divide-surface-border">
          {data?.items.map((c, i) => {
            const open = expanded.has(c.symbol)
            return (
              <li key={c.symbol}>
                <button
                  onClick={() => toggle(c.symbol)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-surface-inner/70 transition-colors"
                >
                  {open ? <ChevronDown size={15} className="text-ink-subtle" /> : <ChevronRight size={15} className="text-ink-subtle" />}
                  <span className="text-ink-subtle text-xs w-6 text-right tabular-nums">{i + 1}</span>
                  <Link
                    to={`/hanriver/stock/${c.symbol}`}
                    className="text-[14px] font-semibold text-ink hover:text-brand-600"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {c.name}
                  </Link>
                  <span className="text-[11px] text-ink-subtle font-mono">{c.symbol}</span>
                  <span className="text-[10px] text-ink-subtle uppercase tracking-wider">{c.market}</span>
                  <span className="flex-1" />
                  <span className="text-[13px] tabular-nums text-ink">{c.close.toLocaleString()}</span>
                  <span
                    className={clsx(
                      'text-[12px] tabular-nums font-semibold w-16 text-right',
                      c.change_pct > 0 ? 'text-up' : c.change_pct < 0 ? 'text-down' : 'text-ink-muted',
                    )}
                  >
                    {c.change_pct > 0 ? '+' : ''}
                    {c.change_pct.toFixed(2)}%
                  </span>
                  <div className="w-40 flex items-center gap-2">
                    <MacProgressBar value={c.score} className="flex-1" />
                    <span className="text-[12px] font-semibold text-brand-600 w-7 text-right tabular-nums">{c.score}</span>
                  </div>
                </button>

                {open && (
                  <div className="border-t border-surface-border px-5 py-4 space-y-3 bg-surface-inner/50">
                    {c.reasons.length > 0 && (
                      <div>
                        <div className="eyebrow mb-1.5">매칭된 특성</div>
                        <div className="flex flex-wrap gap-1.5">
                          {c.reasons.map((r, j) => (
                            <span key={j} className="text-[11px] px-2 py-0.5 rounded-full border border-brand-500/30 bg-brand-50 text-brand-600">
                              {r}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {c.commentary && (
                      <div>
                        <div className="eyebrow mb-1.5">AI 해설</div>
                        <p className="text-[13px] text-ink leading-relaxed">{c.commentary}</p>
                      </div>
                    )}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
                      <Metric label="20일 σ/μ" v={c.features.std_ratio} fmt={(x) => x.toFixed(4)} />
                      <Metric label="거래량 3/20" v={c.features.vol_ratio} fmt={(x) => x.toFixed(2)} />
                      <Metric label="VSA SOS 20일" v={c.features.vsa_sos_20d} fmt={(x) => String(x)} />
                      <Metric label="20일 고가 비율" v={c.features.high20_ratio} fmt={(x) => x.toFixed(3)} />
                      <Metric label="MA20" v={c.features.ma20} fmt={(x) => x.toLocaleString()} />
                      <Metric label="MA60" v={c.features.ma60} fmt={(x) => x.toLocaleString()} />
                      <Metric label="최근 10일 급등봉" v={c.features.surged_count_10d} fmt={(x) => `${x}개`} />
                    </div>
                  </div>
                )}
              </li>
            )
          })}
          {data && data.items.length === 0 && (
            <li className="py-10 text-center text-ink-subtle text-sm">
              조건 충족 종목 없음 — 최소 점수를 낮추거나 유니버스를 바꿔 보세요.
            </li>
          )}
        </ul>
      </MacWindow>
    </div>
  )
}

function Metric<T>({ label, v, fmt }: { label: string; v: T | null | undefined; fmt: (x: T) => string }) {
  return (
    <div className="card-inner p-2">
      <div className="text-ink-muted">{label}</div>
      <div className="text-ink tabular-nums mt-0.5">
        {v != null ? fmt(v) : '-'}
      </div>
    </div>
  )
}
