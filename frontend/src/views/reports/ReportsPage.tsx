import { useState, useEffect, useCallback } from 'react'
import { Newspaper, RefreshCw, ExternalLink, Search, Loader2, ChevronDown } from 'lucide-react'
import clsx from 'clsx'
import api from '../../presenters/api'
import { formatKRW } from '../../presenters/format'

// ── 타입 ─────────────────────────────────────────────────
interface Report {
  id: number
  symbol: string | null
  company_name: string
  securities_firm: string
  title: string
  target_price: number | null
  report_date: string
  url: string
  source: string
}

// ── 목표주가 배지 ─────────────────────────────────────────
function TargetBadge({ price }: { price: number | null }) {
  if (price == null) return <span className="text-slate-600 text-xs">-</span>
  return (
    <span className="text-xs font-mono text-yellow-400">
      {formatKRW(price)}
    </span>
  )
}

// ── 증권사 배지 ───────────────────────────────────────────
function FirmBadge({ firm }: { firm: string }) {
  return (
    <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-brand-500/15 text-brand-500 whitespace-nowrap">
      {firm}
    </span>
  )
}

// ── 리포트 행 ─────────────────────────────────────────────
function ReportRow({ r }: { r: Report }) {
  return (
    <tr className="hover:bg-surface-border/30 transition-colors group">
      {/* 날짜 */}
      <td className="px-4 py-3 text-xs text-slate-400 tabular-nums whitespace-nowrap">
        {r.report_date}
      </td>
      {/* 종목 */}
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-white leading-tight">{r.company_name}</div>
        {r.symbol && (
          <div className="text-xs text-slate-500 font-mono mt-0.5">{r.symbol}</div>
        )}
      </td>
      {/* 제목 + 링크 */}
      <td className="px-4 py-3 max-w-xs lg:max-w-sm">
        {r.url ? (
          <a
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group/link flex items-start gap-1 text-sm text-slate-200 hover:text-brand-500 transition-colors"
          >
            <span className="line-clamp-2 leading-snug">{r.title}</span>
            <ExternalLink
              size={12}
              className="mt-0.5 shrink-0 opacity-0 group-hover/link:opacity-100 transition-opacity"
            />
          </a>
        ) : (
          <span className="text-sm text-slate-400 line-clamp-2">{r.title}</span>
        )}
      </td>
      {/* 증권사 */}
      <td className="px-4 py-3 hidden sm:table-cell">
        <FirmBadge firm={r.securities_firm} />
      </td>
      {/* 목표주가 */}
      <td className="px-4 py-3 text-right hidden md:table-cell">
        <TargetBadge price={r.target_price} />
      </td>
    </tr>
  )
}

// ── 메인 페이지 ───────────────────────────────────────────
export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([])
  const [firms, setFirms] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [fetchResult, setFetchResult] = useState<{ fetched: number; saved: number } | null>(null)

  // 필터 상태
  const [symbolInput, setSymbolInput] = useState('')
  const [firmFilter, setFirmFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [limit, setLimit] = useState(100)

  const loadFirms = useCallback(async () => {
    try {
      const res = await api.get('/api/v1/reports/firms')
      setFirms(res.data)
    } catch {
      // 무시 — DB 비어있을 수 있음
    }
  }, [])

  const loadReports = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { limit }
      if (symbolInput.trim()) params.symbol = symbolInput.trim()
      if (firmFilter) params.firm = firmFilter
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo

      const res = await api.get('/api/v1/reports', { params })
      setReports(res.data)
    } catch (e) {
      console.error('리포트 로드 실패:', e)
    } finally {
      setLoading(false)
    }
  }, [symbolInput, firmFilter, dateFrom, dateTo, limit])

  // 초기 로드
  useEffect(() => {
    loadReports()
    loadFirms()
  }, [])

  async function handleFetch() {
    setFetching(true)
    setFetchResult(null)
    try {
      const res = await api.post('/api/v1/reports/fetch', null, { params: { pages: 3 } })
      setFetchResult(res.data)
      await loadReports()
      await loadFirms()
    } catch (e) {
      console.error('리포트 수집 실패:', e)
    } finally {
      setFetching(false)
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    loadReports()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Newspaper size={22} className="text-brand-500" />
            증권사 리포트
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            NAVER Finance 증권사 리서치 리포트 모음
          </p>
        </div>

        <div className="flex items-center gap-3">
          {fetchResult && (
            <span className="text-xs text-green-400">
              수집 {fetchResult.fetched}건 / 신규 저장 {fetchResult.saved}건
            </span>
          )}
          <button
            onClick={handleFetch}
            disabled={fetching}
            className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {fetching
              ? <Loader2 size={15} className="animate-spin" />
              : <RefreshCw size={15} />
            }
            {fetching ? '수집 중...' : '최신 리포트 불러오기'}
          </button>
        </div>
      </div>

      {/* 검색 필터 */}
      <div className="card">
        <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* 종목코드 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">종목코드</label>
            <input
              type="text"
              maxLength={6}
              value={symbolInput}
              onChange={(e) => setSymbolInput(e.target.value)}
              placeholder="005930"
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* 증권사 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">증권사</label>
            {firms.length > 0 ? (
              <select
                value={firmFilter}
                onChange={(e) => setFirmFilter(e.target.value)}
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              >
                <option value="">전체</option>
                {firms.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            ) : (
              <input
                type="text"
                value={firmFilter}
                onChange={(e) => setFirmFilter(e.target.value)}
                placeholder="한국투자증권"
                className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-brand-500"
              />
            )}
          </div>

          {/* 시작일 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">시작일</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* 종료일 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1">종료일</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="w-full bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>

          {/* 조회 버튼 */}
          <div className="sm:col-span-2 lg:col-span-4 flex items-center gap-3">
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Search size={15} />}
              {loading ? '조회 중...' : '조회'}
            </button>
            <button
              type="button"
              onClick={() => {
                setSymbolInput('')
                setFirmFilter('')
                setDateFrom('')
                setDateTo('')
              }}
              className="text-xs text-slate-500 hover:text-white transition-colors"
            >
              초기화
            </button>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-slate-500">최대</span>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="bg-surface border border-surface-border rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value={50}>50건</option>
                <option value={100}>100건</option>
                <option value={200}>200건</option>
              </select>
            </div>
          </div>
        </form>
      </div>

      {/* 결과 테이블 */}
      {reports.length > 0 ? (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
            <span className="text-sm font-semibold text-white">리포트 목록</span>
            <span className="text-xs text-slate-400">{reports.length}건</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium whitespace-nowrap">날짜</th>
                  <th className="px-4 py-2.5 font-medium">종목</th>
                  <th className="px-4 py-2.5 font-medium">제목</th>
                  <th className="px-4 py-2.5 font-medium hidden sm:table-cell">증권사</th>
                  <th className="px-4 py-2.5 font-medium text-right hidden md:table-cell">목표주가</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {reports.map((r) => (
                  <ReportRow key={r.id} r={r} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : !loading && (
        <div className="card text-center py-16 text-slate-500">
          <Newspaper size={44} className="mx-auto mb-3 opacity-20" />
          <p className="text-sm">리포트가 없습니다.</p>
          <p className="text-xs mt-1">
            상단의 <span className="text-brand-500">"최신 리포트 불러오기"</span>를 눌러 NAVER Finance에서 수집하세요.
          </p>
        </div>
      )}
    </div>
  )
}
