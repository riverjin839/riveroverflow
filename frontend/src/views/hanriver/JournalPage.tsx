import { useEffect, useState } from 'react'
import { hanriverApi, type JournalItem } from '../../presenters/useHanriverPhase2'

export default function JournalPage() {
  const [items, setItems] = useState<JournalItem[]>([])
  const [selected, setSelected] = useState<JournalItem | null>(null)
  const [critique, setCritique] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    const r = await hanriverApi.listJournal()
    setItems(r.data)
  }

  useEffect(() => { load() }, [])

  async function sync() {
    setBusy(true)
    try {
      await hanriverApi.journalSync()
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function coach(id: number) {
    setCritique('로딩 중...')
    const r = await hanriverApi.coach(id)
    setCritique(r.data.critique_md)
  }

  async function save(id: number, patch: { setup?: string; user_note?: string }) {
    await hanriverApi.patchJournal(id, patch)
    await load()
  }

  return (
    <div className="space-y-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">매매 일지 (RIVERFLOW 연동)</h1>
        <button className="btn-primary" onClick={sync} disabled={busy}>
          {busy ? '동기화 중…' : '체결 내역 동기화'}
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 bg-surface-card border border-surface-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface text-slate-500 text-xs">
              <tr>
                <th className="text-left p-2">일자</th>
                <th className="text-left p-2">종목</th>
                <th className="text-left p-2">사이드</th>
                <th className="text-right p-2">수량</th>
                <th className="text-right p-2">체결가</th>
                <th className="text-left p-2">셋업</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr
                  key={it.id}
                  className={`border-t border-surface-border cursor-pointer hover:bg-surface/60 ${selected?.id === it.id ? 'bg-surface' : ''}`}
                  onClick={() => { setSelected(it); setCritique(null) }}
                >
                  <td className="p-2 text-slate-400">{new Date(it.trade_date).toLocaleDateString('ko-KR')}</td>
                  <td className="p-2 text-slate-200">{it.name}</td>
                  <td className={`p-2 ${it.side === 'buy' ? 'text-red-400' : 'text-blue-400'}`}>{it.side}</td>
                  <td className="p-2 text-right tabular-nums">{it.quantity}</td>
                  <td className="p-2 text-right tabular-nums">{it.price.toLocaleString()}</td>
                  <td className="p-2 text-slate-500">{it.setup ?? '-'}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={6} className="text-center py-8 text-slate-500">일지 없음 — 동기화 버튼으로 체결 내역을 가져오세요.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <aside className="bg-surface-card border border-surface-border rounded-lg p-4">
          {selected ? (
            <div className="space-y-3">
              <h2 className="text-sm font-semibold text-slate-200">
                {selected.name} · {new Date(selected.trade_date).toLocaleString('ko-KR')}
              </h2>
              <div className="text-xs text-slate-400">자동 초안</div>
              <div className="text-sm text-slate-300 whitespace-pre-wrap">{selected.draft ?? '-'}</div>

              <label className="block text-xs text-slate-500 mt-2">셋업 태그</label>
              <input
                className="input"
                defaultValue={selected.setup ?? ''}
                onBlur={(e) => save(selected.id, { setup: e.target.value })}
                placeholder="VSA_SOS, pullback ..."
              />
              <label className="block text-xs text-slate-500 mt-2">코멘트</label>
              <textarea
                className="input min-h-[80px]"
                defaultValue={selected.user_note ?? ''}
                onBlur={(e) => save(selected.id, { user_note: e.target.value })}
              />

              <button className="btn-primary w-full" onClick={() => coach(selected.id)}>AI 복기 코칭</button>
              {critique && (
                <pre className="whitespace-pre-wrap font-sans text-xs text-slate-200 bg-surface/70 border border-surface-border rounded p-3 mt-2">
                  {critique}
                </pre>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-500">왼쪽에서 일지를 선택하세요.</div>
          )}
        </aside>
      </div>
    </div>
  )
}
