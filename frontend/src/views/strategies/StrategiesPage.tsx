import { useState, useEffect } from 'react'
import { Plus, Play, Pause, Trash2, Zap } from 'lucide-react'
import api from '../../presenters/api'
import clsx from 'clsx'

interface StrategyConfig {
  id: string
  name: string
  strategy_type: string
  symbols: string[]
  params: Record<string, any>
  enabled: boolean
  broker: string
  created_at: string
}

const STRATEGY_LABELS: Record<string, string> = {
  ma_cross: '이동평균 교차',
  rsi: 'RSI',
  macd: 'MACD',
  ml_base: 'ML 기반',
}

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<StrategyConfig[]>([])
  const [engineRunning, setEngineRunning] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchAll()
  }, [])

  async function fetchAll() {
    const [stRes, engRes] = await Promise.all([
      api.get('/api/v1/strategies').catch(() => ({ data: [] })),
      api.get('/api/v1/engine/status').catch(() => ({ data: { running: false } })),
    ])
    setStrategies(stRes.data)
    setEngineRunning(engRes.data.running)
  }

  async function toggleEngine() {
    setLoading(true)
    try {
      if (engineRunning) {
        await api.post('/api/v1/engine/stop')
        setEngineRunning(false)
      } else {
        await api.post('/api/v1/engine/start')
        setEngineRunning(true)
      }
    } finally {
      setLoading(false)
    }
  }

  async function toggleStrategy(id: string) {
    await api.put(`/api/v1/strategies/${id}/toggle`)
    await fetchAll()
  }

  async function deleteStrategy(id: string) {
    if (!confirm('전략을 삭제하시겠습니까?')) return
    await api.delete(`/api/v1/strategies/${id}`)
    setStrategies((prev) => prev.filter((s) => s.id !== id))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <h1 className="text-xl font-bold">전략 관리</h1>
        <div className="flex gap-2">
          <button
            onClick={toggleEngine}
            disabled={loading}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              engineRunning
                ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
            )}
          >
            {engineRunning ? <Pause size={16} /> : <Play size={16} />}
            {engineRunning ? '엔진 중지' : '엔진 시작'}
          </button>
          <button className="btn-primary flex items-center gap-2">
            <Plus size={16} />
            새 전략
          </button>
        </div>
      </div>

      {/* Engine status */}
      <div className={clsx(
        'card flex items-center gap-3 py-3',
        engineRunning ? 'border-green-500/30' : 'border-surface-border'
      )}>
        <Zap size={18} className={engineRunning ? 'text-green-400' : 'text-slate-500'} />
        <div>
          <div className="text-sm font-medium">
            {engineRunning ? '자동매매 실행 중' : '자동매매 중지됨'}
          </div>
          <div className="text-xs text-slate-500">
            {engineRunning ? 'KRX 09:00~15:30 자동 실행' : '엔진 시작 버튼을 눌러 활성화'}
          </div>
        </div>
        <div className="ml-auto">
          <div className={clsx(
            'w-2.5 h-2.5 rounded-full',
            engineRunning ? 'bg-green-400 animate-pulse' : 'bg-slate-600'
          )} />
        </div>
      </div>

      {/* Strategies list */}
      <div className="space-y-3">
        {strategies.length === 0 ? (
          <div className="card text-center py-12 text-slate-500">
            <Zap size={32} className="mx-auto mb-3 opacity-30" />
            <p>등록된 전략이 없습니다</p>
            <p className="text-sm mt-1">새 전략 버튼을 눌러 전략을 추가하세요</p>
          </div>
        ) : (
          strategies.map((s) => (
            <div key={s.id} className="card">
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-xs bg-surface-border px-2 py-0.5 rounded text-slate-400">
                      {STRATEGY_LABELS[s.strategy_type] ?? s.strategy_type}
                    </span>
                    <span className="text-xs bg-surface-border px-2 py-0.5 rounded text-slate-400">
                      {s.broker}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    종목: {s.symbols.join(', ')}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleStrategy(s.id)}
                    className={clsx(
                      'text-xs px-3 py-1.5 rounded-lg transition-colors',
                      s.enabled
                        ? 'bg-green-500/10 text-green-400'
                        : 'bg-surface-border text-slate-400'
                    )}
                  >
                    {s.enabled ? '활성' : '비활성'}
                  </button>
                  <button
                    onClick={() => deleteStrategy(s.id)}
                    className="text-slate-500 hover:text-red-400 transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
