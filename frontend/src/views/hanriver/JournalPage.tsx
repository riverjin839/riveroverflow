import { useEffect, useState } from 'react'
import clsx from 'clsx'
import { hanriverApi, type JournalItem } from '../../presenters/useHanriverPhase2'
import MacWindow from '../../components/MacWindow'

export default function JournalPage() {
  const [items, setItems] = useState<JournalItem[]>([])
  const [selected, setSelected] = useState<JournalItem | null>(null)
  const [critique, setCritique] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() { const r = await hanriverApi.listJournal(); setItems(r.data) }
  useEffect(() => { load() }, [])
  async function sync() {
    setBusy(true)
    try { await hanriverApi.journalSync(); await load() } finally { setBusy(false) }
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
    <div className="space-y-5">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink tracking-tight">매매 일지</h1>
        <button className="btn-primary" onClick={sync} disabled={busy}>
          {busy ? '동기화 중…' : '체결 내역 동기화'}
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <MacWindow title="JOURNAL" className="lg:col-span-2" bodyClassName="p-0">
          <table className="w-full text-[13px]">
            <thead className="bg-surface-inner text-ink-muted text-[11px] uppercase tracking-wider">
              <tr>
                <th className="text-left p-3">일자</th>
                <th className="text-left p-3">종목</th>
                <th className="text-left p-3">사이드</th>
                <th className="text-right p-3">수량</th>
                <th className="text-right p-3">체결가</th>
                <th className="text-left p-3">셋업</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr
                  key={it.id}
                  className={clsx(
                    'border-t border-surface-border cursor-pointer',
                    selected?.id === it.id ? 'bg-surface-inner' : 'hover:bg-surface-inner/50',
                  )}
                  onClick={() => { setSelected(it); setCritique(null) }}
                >
                  <td className="p-3 text-ink-muted">{new Date(it.trade_date).toLocaleDateString('ko-KR')}</td>
                  <td className="p-3 text-ink font-medium">{it.name}</td>
                  <td className={clsx('p-3', it.side === 'buy' ? 'text-up' : 'text-down')}>{it.side}</td>
                  <td className="p-3 text-right tabular-nums">{it.quantity}</td>
                  <td className="p-3 text-right tabular-nums">{it.price.toLocaleString()}</td>
                  <td className="p-3 text-ink-subtle">{it.setup ?? '-'}</td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><td colSpan={6} className="text-center py-10 text-ink-subtle">일지 없음 — 동기화 버튼을 눌러주세요.</td></tr>
              )}
            </tbody>
          </table>
        </MacWindow>

        <MacWindow title="DETAIL & COACH">
          {selected ? (
            <div className="space-y-3">
              <div>
                <div className="text-sm font-semibold text-ink">{selected.name}</div>
                <div className="text-[11px] text-ink-subtle">{new Date(selected.trade_date).toLocaleString('ko-KR')}</div>
              </div>
              <div className="eyebrow">자동 초안</div>
              <div className="text-[13px] text-ink whitespace-pre-wrap">{selected.draft ?? '-'}</div>

              <label className="block eyebrow mt-2">셋업 태그</label>
              <input
                className="input"
                defaultValue={selected.setup ?? ''}
                onBlur={(e) => save(selected.id, { setup: e.target.value })}
                placeholder="VSA_SOS, pullback..."
              />
              <label className="block eyebrow mt-2">코멘트</label>
              <textarea
                className="input min-h-[80px]"
                defaultValue={selected.user_note ?? ''}
                onBlur={(e) => save(selected.id, { user_note: e.target.value })}
              />

              <button className="btn-primary w-full" onClick={() => coach(selected.id)}>AI 복기 코칭</button>
              {critique && (
                <pre className="whitespace-pre-wrap font-sans text-[12px] text-ink card-inner p-3 mt-2">
                  {critique}
                </pre>
              )}
            </div>
          ) : (
            <div className="text-sm text-ink-subtle">왼쪽에서 일지를 선택하세요.</div>
          )}
        </MacWindow>
      </div>
    </div>
  )
}
