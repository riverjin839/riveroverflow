import { useState } from 'react'
import { Network, ChevronRight, ToggleLeft, ToggleRight, RefreshCw } from 'lucide-react'
import clsx from 'clsx'
import { useOntology } from '../../presenters/useOntology'
import type { OntologyRule } from '../../models/ontologyStore'

// ── 타입 색상 ────────────────────────────────────────
const TYPE_COLORS: Record<string, string> = {
  stock:    'bg-brand-500/20 text-brand-500',
  strategy: 'bg-yellow-500/20 text-yellow-400',
  trade:    'bg-green-500/20 text-green-400',
  research: 'bg-purple-500/20 text-purple-400',
  signal:   'bg-orange-500/20 text-orange-400',
}

function TypeBadge({ type }: { type: string }) {
  return (
    <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', TYPE_COLORS[type] ?? 'bg-slate-700 text-slate-300')}>
      {type}
    </span>
  )
}

// ── 규칙 토글 행 ─────────────────────────────────────
function RuleRow({ rule, onToggle }: { rule: OntologyRule; onToggle: (id: string, v: boolean) => void }) {
  const triggerColor: Record<string, string> = {
    signal: 'text-yellow-400',
    schedule: 'text-blue-400',
    manual: 'text-slate-400',
  }

  return (
    <tr className={clsx(!rule.enabled && 'opacity-50')}>
      <td className="px-4 py-3">
        <div className="text-sm font-medium text-white">{rule.name}</div>
        <div className="text-xs text-slate-500 mt-0.5">{rule.description}</div>
      </td>
      <td className="px-4 py-3 hidden sm:table-cell">
        <span className={clsx('text-xs font-mono', triggerColor[rule.trigger_type] ?? 'text-slate-400')}>
          {rule.trigger_type}
        </span>
      </td>
      <td className="px-4 py-3 hidden md:table-cell">
        <span className="text-xs font-mono text-slate-400">{rule.action_type}</span>
      </td>
      <td className="px-4 py-3 text-right w-20">
        <span className="text-xs text-slate-500 mr-2">P{rule.priority}</span>
      </td>
      <td className="px-4 py-3 text-right">
        <button
          onClick={() => onToggle(rule.id, !rule.enabled)}
          className="text-slate-400 hover:text-white transition-colors"
          title={rule.enabled ? '비활성화' : '활성화'}
        >
          {rule.enabled ? (
            <ToggleRight size={22} className="text-green-400" />
          ) : (
            <ToggleLeft size={22} />
          )}
        </button>
      </td>
    </tr>
  )
}

// ── 탭 ──────────────────────────────────────────────
type Tab = 'summary' | 'objects' | 'links' | 'rules'

// ── 페이지 ──────────────────────────────────────────
export default function OntologyPage() {
  const { objects, links, rules, summary, loading, refetch, toggleRule } = useOntology()
  const [tab, setTab] = useState<Tab>('summary')
  const [typeFilter, setTypeFilter] = useState<string>('all')

  const tabs: { key: Tab; label: string }[] = [
    { key: 'summary', label: '요약' },
    { key: 'objects', label: `객체 (${objects.length})` },
    { key: 'links', label: `관계 (${links.length})` },
    { key: 'rules', label: `규칙 (${rules.length})` },
  ]

  const objectTypes = ['all', ...Array.from(new Set(objects.map((o) => o.type))).sort()]
  const filteredObjects = typeFilter === 'all' ? objects : objects.filter((o) => o.type === typeFilter)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Network size={22} className="text-brand-500" />
          온톨로지 탐색기
        </h1>
        <button
          onClick={refetch}
          disabled={loading}
          className="btn-ghost flex items-center gap-1.5 text-sm"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          새로고침
        </button>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 border-b border-surface-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px',
              tab === t.key
                ? 'border-brand-500 text-brand-500'
                : 'border-transparent text-slate-400 hover:text-white'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── 요약 탭 ── */}
      {tab === 'summary' && summary && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(summary.objects).map(([type, count]) => (
              <div key={type} className="card">
                <TypeBadge type={type} />
                <div className="text-2xl font-bold text-white mt-2">{count}</div>
                <div className="text-xs text-slate-500 mt-0.5">객체</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="card">
              <div className="text-xs text-slate-400">관계 (Links)</div>
              <div className="text-2xl font-bold text-white mt-1">{summary.total_links}</div>
            </div>
            <div className="card">
              <div className="text-xs text-slate-400">활성 규칙</div>
              <div className="text-2xl font-bold text-white mt-1">
                {summary.enabled_rules}
                <span className="text-sm text-slate-500 font-normal ml-1">/ {summary.total_rules}</span>
              </div>
            </div>
          </div>
          <div className="card">
            <p className="text-xs text-slate-400 leading-relaxed">
              온톨로지는 도메인의 <span className="text-white">논리 구조</span>를 DB에 표현한 것입니다.
              객체(Object)·관계(Link)·규칙(Rule)이 하나의 덩어리로 비즈니스 로직을 정의하고,
              엔진이 이를 실행합니다. 프론트엔드는 이벤트를 생성하는 클라이언트입니다.
            </p>
          </div>
        </div>
      )}

      {/* ── 객체 탭 ── */}
      {tab === 'objects' && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap">
            {objectTypes.map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={clsx(
                  'px-3 py-1 rounded-full text-xs font-medium transition-colors',
                  typeFilter === t
                    ? 'bg-brand-500 text-white'
                    : 'bg-surface-card text-slate-400 border border-surface-border hover:text-white'
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium">타입</th>
                  <th className="px-4 py-2.5 font-medium">키</th>
                  <th className="px-4 py-2.5 font-medium hidden md:table-cell">속성</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filteredObjects.slice(0, 100).map((obj) => (
                  <tr key={obj.id} className="hover:bg-surface-border/20">
                    <td className="px-4 py-2.5">
                      <TypeBadge type={obj.type} />
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-slate-300">{obj.key}</td>
                    <td className="px-4 py-2.5 text-xs text-slate-500 hidden md:table-cell max-w-xs truncate">
                      {JSON.stringify(obj.properties)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredObjects.length > 100 && (
              <p className="px-4 py-2 text-xs text-slate-500 border-t border-surface-border">
                상위 100개 표시 (전체 {filteredObjects.length}개)
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── 관계 탭 ── */}
      {tab === 'links' && (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                <th className="px-4 py-2.5 font-medium">주체(Subject)</th>
                <th className="px-4 py-2.5 font-medium text-center">관계</th>
                <th className="px-4 py-2.5 font-medium">대상(Object)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {links.slice(0, 100).map((link) => (
                <tr key={link.id} className="hover:bg-surface-border/20">
                  <td className="px-4 py-2.5">
                    <TypeBadge type={link.subject_type} />
                    <span className="ml-2 text-xs text-slate-300 font-mono">{link.subject_key.replace(/^(stock|strategy|research):/, '')}</span>
                  </td>
                  <td className="px-4 py-2.5 text-center">
                    <div className="flex items-center justify-center gap-1 text-xs text-slate-400">
                      <ChevronRight size={12} />
                      <span className="font-mono">{link.predicate}</span>
                      <ChevronRight size={12} />
                    </div>
                  </td>
                  <td className="px-4 py-2.5">
                    <TypeBadge type={link.object_type} />
                    <span className="ml-2 text-xs text-slate-300 font-mono">{link.object_key.replace(/^(stock|strategy|research):/, '')}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {links.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-sm">
              아직 관계가 없습니다. 리서치를 실행하면 관계가 생성됩니다.
            </div>
          )}
        </div>
      )}

      {/* ── 규칙 탭 ── */}
      {tab === 'rules' && (
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border text-xs text-slate-400">
            토글로 규칙을 활성화/비활성화할 수 있습니다. 우선순위가 높은 규칙이 먼저 적용됩니다.
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border text-left text-xs text-slate-500">
                <th className="px-4 py-2.5 font-medium">규칙명</th>
                <th className="px-4 py-2.5 font-medium hidden sm:table-cell">트리거</th>
                <th className="px-4 py-2.5 font-medium hidden md:table-cell">액션</th>
                <th className="px-4 py-2.5 font-medium text-right">우선순위</th>
                <th className="px-4 py-2.5 font-medium text-right">활성</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {rules.map((rule) => (
                <RuleRow key={rule.id} rule={rule} onToggle={toggleRule} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
