import { Settings } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">설정</h1>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">브로커 연결</h2>
        <div className="space-y-3">
          <BrokerStatus name="한국투자증권" status="연결됨" ok />
          <BrokerStatus name="Kiwoom" status="브릿지 미연결" ok={false} />
        </div>
      </div>

      <div className="card space-y-4">
        <h2 className="text-sm font-semibold text-slate-300">리스크 설정</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-slate-400 mb-1">종목당 최대 포지션 비율</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                defaultValue={10}
                className="w-24 bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
              <span className="text-sm text-slate-400">%</span>
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">손절 기준</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                defaultValue={3}
                className="w-24 bg-surface border border-surface-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
              <span className="text-sm text-slate-400">%</span>
            </div>
          </div>
        </div>
        <button className="btn-primary text-sm">저장</button>
      </div>
    </div>
  )
}

function BrokerStatus({ name, status, ok }: { name: string; status: string; ok: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-surface-border/50">
      <span className="text-sm">{name}</span>
      <span className={`text-xs ${ok ? 'text-green-400' : 'text-slate-500'}`}>{status}</span>
    </div>
  )
}
