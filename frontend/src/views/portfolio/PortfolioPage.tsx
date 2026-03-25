import { usePortfolio } from '../../presenters/usePortfolio'
import { formatKRW, formatPct, getPctColor } from '../../presenters/format'

export default function PortfolioPage() {
  const { balance, positions, loading, refetch } = usePortfolio()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">포트폴리오</h1>
        <button onClick={refetch} className="btn-ghost text-sm">
          새로고침
        </button>
      </div>

      {/* Balance overview */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {[
          { label: '총 평가금액', value: formatKRW(balance?.total_value) },
          { label: '주식 평가금액', value: formatKRW(balance?.stock_value) },
          { label: '예수금', value: formatKRW(balance?.cash) },
          {
            label: '평가손익',
            value: formatKRW(balance?.profit_loss),
            className: getPctColor(balance?.profit_loss_pct ?? 0),
          },
          {
            label: '수익률',
            value: formatPct(balance?.profit_loss_pct ?? 0),
            className: getPctColor(balance?.profit_loss_pct ?? 0),
          },
        ].map(({ label, value, className }) => (
          <div key={label} className="card">
            <p className="text-xs text-slate-400">{label}</p>
            <p className={`text-lg font-bold font-mono mt-1 ${className ?? 'text-white'}`}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* Positions table */}
      <div className="card">
        <h2 className="text-sm font-semibold mb-4">보유 종목 ({positions.length})</h2>
        {loading ? (
          <div className="text-center text-slate-500 py-8">로딩 중...</div>
        ) : positions.length === 0 ? (
          <div className="text-center text-slate-500 py-8">보유 종목이 없습니다</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-surface-border text-left">
                  <th className="pb-3 pr-4">종목명</th>
                  <th className="pb-3 pr-4 text-right">수량</th>
                  <th className="pb-3 pr-4 text-right hidden md:table-cell">평균단가</th>
                  <th className="pb-3 pr-4 text-right">현재가</th>
                  <th className="pb-3 pr-4 text-right">평가손익</th>
                  <th className="pb-3 text-right">수익률</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((p) => (
                  <tr
                    key={p.symbol}
                    className="border-b border-surface-border/40 hover:bg-surface-border/20"
                  >
                    <td className="py-3 pr-4">
                      <div className="font-medium">{p.name}</div>
                      <div className="text-xs text-slate-500">{p.symbol}</div>
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      {p.quantity.toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono hidden md:table-cell">
                      {formatKRW(p.avg_price)}
                    </td>
                    <td className="py-3 pr-4 text-right font-mono">
                      {formatKRW(p.current_price)}
                    </td>
                    <td className={`py-3 pr-4 text-right font-mono ${getPctColor(p.profit_loss_pct)}`}>
                      {formatKRW(p.profit_loss)}
                    </td>
                    <td className={`py-3 text-right font-mono ${getPctColor(p.profit_loss_pct)}`}>
                      {formatPct(p.profit_loss_pct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
