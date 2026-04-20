import { useEffect, useState } from 'react'
import { hanriverApi, type AiReport } from '../../presenters/useHanriverPhase2'

export default function HanriverReportsPage() {
  const [reports, setReports] = useState<AiReport[]>([])
  const [subject, setSubject] = useState('')
  const [type, setType] = useState('daily')
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<AiReport | null>(null)

  async function refresh() {
    const r = await hanriverApi.listReports()
    setReports(r.data)
  }
  useEffect(() => { refresh() }, [])

  async function generate() {
    setBusy(true)
    try {
      await hanriverApi.generateReport(type, subject || new Date().toISOString().slice(0, 10))
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">HANRIVER AI 리포트</h1>

      <section className="bg-surface-card rounded-lg border border-surface-border p-4">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">리포트 생성</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="daily">Daily (당일 시장 요약)</option>
            <option value="weekly">Weekly (주간 리뷰)</option>
            <option value="stock">Stock (종목 심층)</option>
          </select>
          <input
            className="input md:col-span-2"
            placeholder={type === 'stock' ? '종목 코드 (예: 005930)' : '날짜 (비우면 오늘)'}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <button className="btn-primary" onClick={generate} disabled={busy}>
            {busy ? '생성 중 (최대 30초)…' : '리포트 생성'}
          </button>
        </div>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1 space-y-2">
          {reports.map((r) => (
            <button
              key={r.id}
              className={`w-full text-left bg-surface-card border rounded p-3 text-sm hover:border-brand-500/60 ${selected?.id === r.id ? 'border-brand-500' : 'border-surface-border'}`}
              onClick={() => setSelected(r)}
            >
              <div className="text-xs text-slate-500">
                {r.report_type} · {new Date(r.created_at).toLocaleString('ko-KR')}
              </div>
              <div className="text-slate-200 mt-1 truncate">{r.subject}</div>
            </button>
          ))}
          {reports.length === 0 && (
            <div className="text-xs text-slate-500">생성된 리포트 없음</div>
          )}
        </div>
        <article className="lg:col-span-2 bg-surface-card border border-surface-border rounded-lg p-4 min-h-[320px]">
          {selected ? (
            <pre className="whitespace-pre-wrap font-sans text-sm text-slate-200 leading-relaxed">
              {selected.content_md}
            </pre>
          ) : (
            <div className="text-sm text-slate-500">왼쪽에서 리포트를 선택하세요.</div>
          )}
        </article>
      </div>
    </div>
  )
}
