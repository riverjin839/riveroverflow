import { useState } from 'react'
import { FlaskConical, Search, Loader2, ChevronDown, ChevronUp, Plus, X, Filter } from 'lucide-react'
import clsx from 'clsx'
import { useResearch } from '../../presenters/useResearch'
import type { ResearchResult, ConditionSpec, ConditionResult } from '../../models/researchStore'
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
  above_ma60:   { label: 'MA60 상회', cls: 'bg-blue-500/20 text-blue-400' },
  below_ma60:   { label: 'MA60 하회', cls: 'bg-red-800/20 text-red-400' },
  above_ma120:  { label: 'MA120 상회', cls: 'bg-blue-400/20 text-blue-300' },
  below_ma120:  { label: 'MA120 하회', cls: 'bg-red-900/20 text-red-500' },
}

function SignalChips({ signals }: { signals: ResearchResult['signals'] }) {
  const chips: string[] = []
  if (signals.rsi && signals.rsi !== 'neutral') chips.push(signals.rsi)
  if (signals.ma === 'golden_cross' || signals.ma === 'dead_cross') chips.push(signals.ma)
  if (signals.macd) chips.push(signals.macd)
  if (signals.high_status && signals.high_status !== 'normal') chips.push(signals.high_status)
  if (signals.volume === 'spike') chips.push('spike')
  if (signals.ma60_status === 'above_ma60') chips.push('above_ma60')
  if (signals.ma120_status === 'above_ma120') chips.push('above_ma120')

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
          {r.signals.monthly_tv != null && (
            <div>
              <span className="text-slate-500">월누적거래대금</span>
              <span className="ml-2 text-white font-mono">
                {(r.signals.monthly_tv as number).toLocaleString()}억
              </span>
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
  { key: 'oversold',    label: 'RSI 과매도' },
  { key: 'golden_cross', label: '골든크로스' },
  { key: 'bullish',     label: 'MACD 강세' },
  { key: 'near_high',   label: '고가근접' },
  { key: 'spike',       label: '거래량급증' },
  { key: 'above_ma60',  label: 'MA60 상회' },
  { key: 'above_ma120', label: 'MA120 상회' },
]

// ══════════════════════════════════════════════════════
// ── 조건 스크리닝 탭 ──────────────────────────────────
// ══════════════════════════════════════════════════════

const CONDITION_TYPE_OPTIONS = [
  { value: 'consecutive_bullish',              label: 'N일 연속 양봉',        hasThreshold: false, hasWick: false, hasMonths: false, hasMaPeriod: false, hasSymbols: false },
  { value: 'consecutive_bearish_no_wick',      label: 'N일 연속 꼬리없는 음봉', hasThreshold: false, hasWick: true,  hasMonths: false, hasMaPeriod: false, hasSymbols: false },
  { value: 'trading_value_consecutive',        label: 'N일 연속 거래대금',     hasThreshold: true,  hasWick: false, hasMonths: false, hasMaPeriod: false, hasSymbols: false },
  { value: 'monthly_cumulative_trading_value', label: '월단위 누적 거래대금',   hasThreshold: true,  hasWick: false, hasMonths: true,  hasMaPeriod: false, hasSymbols: false },
  { value: 'price_above_ma',                   label: '이동평균 상회',          hasThreshold: false, hasWick: false, hasMonths: false, hasMaPeriod: true,  hasSymbols: false },
  { value: 'symbol_in_list',                   label: '종목 리스트 포함',       hasThreshold: false, hasWick: false, hasMonths: false, hasMaPeriod: false, hasSymbols: true  },
] as const

function conditionLabel(c: ConditionSpec): string {
  if (c.type === 'consecutive_bullish') return `${c.n}일 연속 양봉`
  if (c.type === 'consecutive_bearish_no_wick') return `${c.n}일 연속 꼬리없는 음봉 (꼬리 ${c.wick_pct ?? 1}% 이내)`
  if (c.type === 'trading_value_consecutive') return `거래대금 ${c.n}일 연속 ${(c.threshold ?? 0).toLocaleString()}억 이상`
  if (c.type === 'monthly_cumulative_trading_value') return `${c.months ?? 1}개월 누적 거래대금 ${(c.threshold ?? 0).toLocaleString()}억 이상`
  if (c.type === 'price_above_ma') return `현재가 MA${c.ma_period ?? 20} 상회`
  if (c.type === 'symbol_in_list') return `종목 리스트 포함 (${(c.symbols ?? []).length}개)`
  return c.type
}

function ConditionScreenerTab() {
  const { conditionResults, conditionLoading, runConditionScan } = useResearch()
  const [conditions, setConditions] = useState<ConditionSpec[]>([])
  const [customSymbols, setCustomSymbols] = useState('')

  // 빌더 상태
  const [buildType, setBuildType] = useState<ConditionSpec['type']>('consecutive_bullish')
  const [buildN, setBuildN] = useState(3)
  const [buildThreshold, setBuildThreshold] = useState(3000)
  const [buildWickPct, setBuildWickPct] = useState(1.0)
  const [buildMonths, setBuildMonths] = useState(1)
  const [buildMaPeriod, setBuildMaPeriod] = useState(20)
  const [buildSymbolList, setBuildSymbolList] = useState('')  // 쉼표 구분 입력

  const selectedMeta = CONDITION_TYPE_OPTIONS.find((o) => o.value === buildType)!

  function addCondition() {
    const symbolArr = buildSymbolList
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length === 6 && /^\d+$/.test(s))

    const spec: ConditionSpec = {
      type: buildType,
      n: buildN,
      ...(selectedMeta.hasThreshold && { threshold: buildThreshold }),
      ...(selectedMeta.hasWick && { wick_pct: buildWickPct }),
      ...(selectedMeta.hasMonths && { months: buildMonths }),
      ...(selectedMeta.hasMaPeriod && { ma_period: buildMaPeriod }),
      ...(selectedMeta.hasSymbols && { symbols: symbolArr }),
    }
    setConditions((prev) => [...prev, spec])
  }

  function removeCondition(idx: number) {
    setConditions((prev) => prev.filter((_, i) => i !== idx))
  }

  function handleScan() {
    if (conditions.length === 0) return
    const syms = customSymbols.trim()
      ? customSymbols.split(',').map((s) => s.trim()).filter(Boolean)
      : undefined
    runConditionScan(syms, conditions)
  }

  return (
    <div className="space-y-4">
      {/* 조건 빌더 */}
      <div className="card space-y-4">
        <div className="text-sm font-semibold text-white flex items-center gap-2">
          <Filter size={15} className="text-brand-500" />
          조건 추가
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* 조건 타입 */}
          <div className="sm:col-span-2">
            <label className="block text-xs text-slate-400 mb-1">조건 타입</label>
            <select
              value={buildType}
              onChange={(e) => setBuildType(e.target.value as ConditionSpec['type'])}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            >
              {CONDITION_TYPE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* 연속 일수 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">연속 일수</label>
            <input
              type="number"
              min={1}
              max={20}
              value={buildN}
              onChange={(e) => setBuildN(Math.max(1, Math.min(20, Number(e.target.value))))}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* 거래대금 기준 (조건별 노출) */}
          {selectedMeta.hasThreshold && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">거래대금 기준 (억)</label>
              <input
                type="number"
                min={0}
                value={buildThreshold}
                onChange={(e) => setBuildThreshold(Number(e.target.value))}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          )}

          {/* 꼬리 허용 % */}
          {selectedMeta.hasWick && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">꼬리 허용 (%)</label>
              <input
                type="number"
                min={0}
                max={10}
                step={0.5}
                value={buildWickPct}
                onChange={(e) => setBuildWickPct(Number(e.target.value))}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          )}

          {/* 개월수 (월 누적 거래대금) */}
          {selectedMeta.hasMonths && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">기준 개월수</label>
              <input
                type="number"
                min={1}
                max={12}
                value={buildMonths}
                onChange={(e) => setBuildMonths(Math.max(1, Math.min(12, Number(e.target.value))))}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          )}

          {/* 이동평균 기간 */}
          {selectedMeta.hasMaPeriod && (
            <div>
              <label className="block text-xs text-slate-400 mb-1">이동평균 기간</label>
              <select
                value={buildMaPeriod}
                onChange={(e) => setBuildMaPeriod(Number(e.target.value))}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              >
                <option value={5}>MA5 (1주)</option>
                <option value={20}>MA20 (1개월)</option>
                <option value={60}>MA60 (3개월)</option>
                <option value={120}>MA120 (6개월)</option>
                <option value={200}>MA200 (10개월)</option>
              </select>
            </div>
          )}
        </div>

        {/* 종목 리스트 입력 */}
        {selectedMeta.hasSymbols && (
          <div>
            <label className="block text-xs text-slate-400 mb-1">
              종목코드 목록 (쉼표 구분, 6자리 숫자만 인식)
            </label>
            <input
              type="text"
              value={buildSymbolList}
              onChange={(e) => setBuildSymbolList(e.target.value)}
              placeholder="005930,000660,035420"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>
        )}

        <button
          onClick={addCondition}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-card border border-surface-border text-sm text-slate-300 hover:text-white hover:border-brand-500 transition-colors"
        >
          <Plus size={14} />
          조건 추가
        </button>

        {/* 추가된 조건 목록 */}
        {conditions.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-xs text-slate-500">추가된 조건 (AND 논리로 모두 만족하는 종목만 반환)</div>
            <div className="flex flex-wrap gap-2">
              {conditions.map((c, i) => (
                <span
                  key={i}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-brand-500/20 text-brand-400 border border-brand-500/30"
                >
                  {conditionLabel(c)}
                  <button onClick={() => removeCondition(i)} className="hover:text-white">
                    <X size={11} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 종목 입력 + 실행 */}
      <div className="card space-y-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">커스텀 종목 (쉼표 구분)</label>
          <input
            type="text"
            value={customSymbols}
            onChange={(e) => setCustomSymbols(e.target.value)}
            placeholder="005930,000660 (비우면 KOSPI 기본 20종목)"
            className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
          />
        </div>
        <button
          onClick={handleScan}
          disabled={conditionLoading || conditions.length === 0}
          className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {conditionLoading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          {conditionLoading ? '스크리닝 중...' : '스크리닝 실행'}
        </button>
        {conditions.length === 0 && (
          <p className="text-xs text-slate-500">조건을 1개 이상 추가한 후 실행하세요.</p>
        )}
      </div>

      {/* 결과 테이블 */}
      {conditionResults.length > 0 && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
            <span className="text-sm font-semibold text-white">매칭 종목</span>
            <span className="text-xs text-slate-400">{conditionResults.length}종목 매칭</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium">종목</th>
                  <th className="px-4 py-2.5 font-medium text-right">현재가</th>
                  <th className="px-4 py-2.5 font-medium text-right hidden sm:table-cell">거래량</th>
                  <th className="px-4 py-2.5 font-medium">매칭 조건</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {conditionResults.map((r) => (
                  <ConditionResultRow key={r.symbol} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!conditionLoading && conditionResults.length === 0 && conditions.length > 0 && (
        <div className="card text-center py-8 text-slate-500 text-sm">
          조건을 만족하는 종목이 없습니다.
        </div>
      )}
    </div>
  )
}

function ConditionResultRow({ r }: { r: ConditionResult }) {
  return (
    <tr className="hover:bg-surface-border/30 transition-colors">
      <td className="px-4 py-3">
        <div className="font-medium text-white text-sm">{r.name}</div>
        <div className="text-xs text-slate-500 font-mono">{r.symbol}</div>
      </td>
      <td className="px-4 py-3 text-right font-mono text-white text-sm">
        {formatKRW(r.current_price)}
      </td>
      <td className="px-4 py-3 text-right text-slate-400 text-xs hidden sm:table-cell font-mono">
        {r.volume.toLocaleString()}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {r.matched_conditions.map((c, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400"
            >
              {c}
            </span>
          ))}
        </div>
      </td>
    </tr>
  )
}

// ══════════════════════════════════════════════════════
// ── 페이지 ───────────────────────────────────────────
// ══════════════════════════════════════════════════════

type Tab = 'analysis' | 'conditions'

export default function ResearchPage() {
  const { results, loading, lastScanned, runScan } = useResearch()
  const [activeTab, setActiveTab] = useState<Tab>('analysis')
  const [customSymbols, setCustomSymbols] = useState('')
  const [periodDays, setPeriodDays] = useState(60)
  const [activeFilters, setActiveFilters] = useState<Set<string>>(new Set())
  const [minMonthlyTV, setMinMonthlyTV] = useState('')

  function toggleFilter(key: string) {
    setActiveFilters((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  const filteredResults = results.filter((r) => {
    if (activeFilters.size > 0) {
      const sigVals = Object.values(r.signals).map((v) => String(v))
      if (![...activeFilters].some((f) => sigVals.some((v) => v.includes(f)))) return false
    }
    if (minMonthlyTV !== '') {
      const tv = r.signals.monthly_tv as number | undefined
      if (tv == null || tv < Number(minMonthlyTV)) return false
    }
    return true
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

      {/* 탭 */}
      <div className="flex gap-1 border-b border-surface-border">
        {[
          { key: 'analysis' as Tab, label: '기본 분석' },
          { key: 'conditions' as Tab, label: '조건 스크리닝' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={clsx(
              'px-4 py-2 text-sm font-medium -mb-px border-b-2 transition-colors',
              activeTab === t.key
                ? 'border-brand-500 text-white'
                : 'border-transparent text-slate-400 hover:text-white'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── 기본 분석 탭 ── */}
      {activeTab === 'analysis' && (
        <>
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
            <div className="space-y-2">
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
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">월누적거래대금</span>
                <input
                  type="number"
                  min={0}
                  placeholder="최소 억 (예: 3000)"
                  value={minMonthlyTV}
                  onChange={(e) => setMinMonthlyTV(e.target.value)}
                  className="w-44 bg-surface border border-surface-border rounded-lg px-2 py-1 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
                />
                <span className="text-xs text-slate-500">억 이상</span>
                {minMonthlyTV !== '' && (
                  <button
                    onClick={() => setMinMonthlyTV('')}
                    className="text-xs text-slate-500 hover:text-white"
                  >
                    ✕ 초기화
                  </button>
                )}
              </div>
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
        </>
      )}

      {/* ── 조건 스크리닝 탭 ── */}
      {activeTab === 'conditions' && <ConditionScreenerTab />}
    </div>
  )
}
