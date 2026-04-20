import { useEffect, useState } from 'react'
import { hanriverApi, type AiReport } from '../../presenters/useHanriverPhase2'
import MacWindow from '../../components/MacWindow'
import clsx from 'clsx'

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
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-ink tracking-tight">AI 리포트</h1>

      <MacWindow title="GENERATE">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
            <option value="daily">Daily · 당일 시장 요약</option>
            <option value="weekly">Weekly · 주간 리뷰</option>
            <option value="stock">Stock · 종목 심층</option>
          </select>
          <input
            className="input md:col-span-2"
            placeholder={type === 'stock' ? '종목 코드 (예: 005930)' : '날짜 (비우면 오늘)'}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <button className="btn-primary" onClick={generate} disabled={busy}>
            {busy ? '생성 중 …' : '리포트 생성'}
          </button>
        </div>
      </MacWindow>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="space-y-2">
          {reports.map((r) => (
            <button
              key={r.id}
              className={clsx(
                'w-full text-left card p-3 text-sm transition-all',
                selected?.id === r.id ? 'ring-2 ring-brand-500' : 'hover:border-ink-subtle',
              )}
              onClick={() => setSelected(r)}
            >
              <div className="text-[11px] text-ink-subtle">
                {r.report_type} · {new Date(r.created_at).toLocaleString('ko-KR')}
              </div>
              <div className="text-ink font-medium mt-1 truncate">{r.subject}</div>
            </button>
          ))}
          {reports.length === 0 && <div className="text-xs text-ink-subtle">생성된 리포트 없음</div>}
        </div>
        <MacWindow title="REPORT" className="lg:col-span-2" bodyClassName="p-5 min-h-[360px]">
          {selected ? (
            <pre className="whitespace-pre-wrap font-sans text-[13px] text-ink leading-relaxed">
              {selected.content_md}
            </pre>
          ) : (
            <div className="text-sm text-ink-subtle">왼쪽에서 리포트를 선택하세요.</div>
          )}
        </MacWindow>
      </div>
    </div>
  )
}
