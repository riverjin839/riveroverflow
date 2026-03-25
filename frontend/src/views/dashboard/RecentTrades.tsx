import { formatKRW } from '../../presenters/format'
import type { TradeEvent } from '../../models/realtimeStore'
import clsx from 'clsx'

export default function RecentTrades({ trades }: { trades: TradeEvent[] }) {
  return (
    <div className="card h-full">
      <h2 className="text-sm font-semibold text-slate-300 mb-3">최근 체결</h2>
      {trades.length === 0 ? (
        <div className="text-center text-slate-500 text-sm py-8">
          체결 내역이 없습니다
        </div>
      ) : (
        <div className="space-y-2">
          {trades.map((t) => (
            <div key={t.order_id} className="flex items-center justify-between text-xs">
              <div>
                <span
                  className={clsx(
                    'font-bold mr-1',
                    t.side === 'buy' ? 'text-up' : 'text-down'
                  )}
                >
                  {t.side === 'buy' ? '매수' : '매도'}
                </span>
                <span className="text-slate-300">{t.symbol}</span>
              </div>
              <div className="text-right">
                <div className="font-mono text-slate-200">{formatKRW(t.price)}</div>
                <div className="text-slate-500">{t.quantity.toLocaleString()}주</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
