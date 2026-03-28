import { useState } from 'react'
import { FlaskConical, Search, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'
import { useResearch } from '../../presenters/useResearch'
import type { ResearchResult } from '../../models/researchStore'
import { formatKRW } from '../../presenters/format'

// ── 스코어 배지 ──────────────────────────────────────
function ScoreBadge({ score }: { score: number }) {
  const cls =
    score >= 70
      ? 'bg-green-500/20 text-green-400'
      : score >= 40
      ? 'bg-yellow-500/20 text-yellow-400'
      : 'bg-slate-700 text-slate-400'
  return (
    <span className={clsx('inline-block px-2 py-0.5 rounded text-xs font-bold tabular-nums', cls)}>
      {score.toFixed(0)}
    </span>
  )
}

// ── 시그널 칩 ────────────────────────────────────────
const SIGNAL_LABELS: Record<string, { label: string; cls: string }> = {
  oversold:     { label: 'RSI 과매도', cls: 'bg-up/20 text-up' },
  overbought:   { label: 'RSI 과매수', cls: 'bg-down/20 text-down' },
  golden_cross: { label: '골든크로스', cls: 'bg-green-500/20 text-green-400' },
  dead_cross:   { label: '데드크로스', cls: 'bg-red-800/20 text-red-400' },
  bullish:      { label: 'MACD 강세', cls: 'bg-brand-500/20 text-brand-500' },
  bearish:      { label: 'MACD 약세', cls: 'bg-slate-600/40 text-slate-400' },
  new_high:     { label: '신고가', cls: 'bg-up/20 text-up' },
  near_high:    { label: '고가근접', cls: 'bg-yellow-500/20 text-yellow-400' },
  spike:        { label: '거래량↑', cls: 'bg-purple-500/20 text-purple-400' },
}

function SignalChips({ signals }: { signals: ResearchResult['signals'] }) {
  const chips: string[] = []
  if (signals.rsi && signals.rsi !== 'neutral') chips.push(signals.rsi)
  if (signals.ma === 'golden_cross' || signals.ma === 'dead_cross') chips.push(signals.ma)
  if (signals.macd) chips.push(signals.macd)
  if (signals.high_status && signals.high_status !== 'normal') chips.push(signals.high_status)
  if (signals.volume === 'spike') chips.push('spike')

  return (
    <div className="flex flex-wrap gap-1">
      {chips.map((c) => {
        const meta = SIGNAL_LABELS[c]
        return meta ? (
          <span key={c} className={clsx('px-1.5 py-0.5 rounded text-xs font-medium', meta.cls)}>
            {meta.label}
          </span>
        ) : null
      })}
    </div>
  )
}

// ── 행 확장 상세 ─────────────────────────────────────
function DetailRow({ r }: { r: ResearchResult }) {
  return (
    <tr className="bg-surface-card/30">
      <td colSpan={6} className="px-6 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          {r.rsi != null && (
            <div>
              <span className="text-slate-500">RSI(14)</span>
              <span className="ml-2 text-white font-mono">{r.rsi.toFixed(1)}</span>
            </div>
          )}
          {r.ma5 != null && (
            <div>
              <span className="text-slate-500">MA5</span>
              <span className="ml-2 text-white font-mono">{formatKRW(r.ma5)}</span>
            </div>
          )}
          {r.ma20 != null && (
            <div>
              <span className="text-slate-500">MA20</span>
              <span className="ml-2 text-white font-mono">{formatKRW(r.ma20)}</span>
            </div>
          )}
          {r.ma60 != null && (
            <div>
              <span className="text-slate-500">MA60</span>
              <span className="ml-2 text-white font-mono">{formatKRW(r.ma60)}</span>
            </div>
          )}
          {r.high_pct != null && (
            <div>
              <span className="text-slate-500">기간고가대비</span>
              <span className="ml-2 text-white font-mono">{r.high_pct.toFixed(1)}%</span>
            </div>
          )}
          {r.volume_ratio != null && (
            <div>
              <span className="text-slate-500">거래량비율</span>
              <span className="ml-2 text-white font-mono">{r.volume_ratio.toFixed(2)}x</span>
            </div>
          )}
          {r.macd_val != null && (
            <div>
              <span className="text-slate-500">MACD</span>
              <span className="ml-2 text-white font-mono">{r.macd_val.toFixed(2)}</span>
            </div>
          )}
        </div>
        <p className="mt-2 text-xs text-slate-400">{r.summary}</p>
      </td>
    </tr>
  )
}

// ── 메인 테이블 행 ────────────────────────────────────
function ResultRow({ r }: { r: ResearchResult }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <>
      <tr
        className={clsx(
          'cursor-pointer hover:bg-surface-border/30 transition-colors',
          r.composite_score >= 70 && 'border-l-2 border-green-500'
        )}
        onClick={() => setExpanded((v) => !v)}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <ScoreBadge score={r.composite_score} />
          </div>
        </td>
        <td className="px-4 py-3">
          <div className="font-medium text-white text-sm">{r.name}</div>
          <div className="text-xs text-slate-500 font-mono">{r.symbol}</div>
        </td>
        <td className="px-4 py-3 hidden sm:table-cell">
          <SignalChips signals={r.signals} />
        </td>
        <td className="px-4 py-3 text-xs text-slate-400 hidden md:table-cell">
          {r.research_date}
        </td>
        <td className="px-4 py-3 text-right text-slate-400">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </td>
      </tr>
      {expanded && <DetailRow r={r} />}
    </>
  )
}

// ── 시그널 필터 버튼 ──────────────────────────────────
const FILTER_OPTIONS = [
  { key: 'oversold', label: 'RSI 과매도' },
  { key: 'golden_cross', label: '골든크로스' },
  { key: 'bullish', label: 'MACD 강세' },
  { key: 'near_high', label: '고가근접' },
  { key: 'spike', label: '거래량급증' },
]

// ── 페이지 ───────────────────────────────────────────
export default function ResearchPage() {
  const { results, loading, lastScanned, runScan } = useResearch()
  const [customSymbols, setCustomSymbols] = useState('')
  const [periodDays, setPeriodDays] = useState(60)
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set())

  function toggleFilter(key: string) {
    setActiveFilters((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const filteredResults =
    activeFilters.size === 0
      ? results
      : results.filter((r) => {
          const sigVals = Object.values(r.signals).map((v) => String(v))
          return [...activeFilters].some((f) => sigVals.some((v) => v.includes(f)))
        })

  function handleScan() {
    const syms = customSymbols.trim()
      ? customSymbols.split(',').map((s) => s.trim()).filter(Boolean)
      : undefined
    runScan(syms, periodDays)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FlaskConical size={22} className="text-brand-500" />
            오토리서치
          </h1>
          {lastScanned && (
            <p className="text-xs text-slate-500 mt-0.5">마지막 리서치: {lastScanned}</p>
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="card space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <label className="block text-xs text-slate-400 mb-1">커스텀 종목 (쉼표 구분)</label>
            <input
              type="text"
              value={customSymbols}
              onChange={(e) => setCustomSymbols(e.target.value)}
              placeholder="005930,000660 (비우면 KOSPI 기본 20종목)"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">분석 기간</label>
            <select
              value={periodDays}
              onChange={(e) => setPeriodDays(Number(e.target.value))}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            >
              <option value={20}>20일 (1개월)</option>
              <option value={60}>60일 (3개월)</option>
              <option value={120}>120일 (6개월)</option>
              <option value={252}>252일 (52주)</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleScan}
          disabled={loading}
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          {loading ? '분석 중...' : '리서치 실행'}
        </button>
      </div>

      {/* 시그널 필터 */}
      {results.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {FILTER_OPTIONS.map((f) => (
            <button
              key={f.key}
              onClick={() => toggleFilter(f.key)}
              className={clsx(
                'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                activeFilters.has(f.key)
                  ? 'bg-brand-500 text-white'
                  : 'bg-surface-card text-slate-400 border border-surface-border hover:text-white'
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}

      {/* 결과 테이블 */}
      {filteredResults.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
            <span className="text-sm font-semibold text-white">리서치 결과</span>
            <span className="text-xs text-slate-400">{filteredResults.length}종목 · 클릭해서 상세 확인</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium w-16">스코어</th>
                  <th className="px-4 py-2.5 font-medium">종목</th>
                  <th className="px-4 py-2.5 font-medium hidden sm:table-cell">시그널</th>
                  <th className="px-4 py-2.5 font-medium hidden md:table-cell">날짜</th>
                  <th className="px-4 py-2.5 w-8" />
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredResults.map((r) => (
                  <ResultRow key={`${r.symbol}-${r.research_date}`} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && results.length === 0 && (
        <div className="card text-center py-12 text-slate-500">
          <FlaskConical size={40} className="mx-auto mb-3 opacity-30" />
          <p>리서치 실행 버튼을 눌러 종목 분석을 시작하세요.</p>
          <p className="text-xs mt-1">장 종료 후 (15:45 KST) 매일 자동으로도 실행됩니다.</p>
        </div>
      )}
    </div>
  )
}
