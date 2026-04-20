import {
  useKrIndices,
  useGlobalIndices,
  useFxCommodities,
  useSentiment,
  useSectorHeatmap,
  useHanriverNews,
} from '../../presenters/useHanriver'
import IndexCardGrid from './IndexCardGrid'
import QuoteListPanel from './QuoteListPanel'
import SectorHeatmap from './SectorHeatmap'
import NewsFeed from './NewsFeed'

export default function HanriverDashboardPage() {
  const kr = useKrIndices()
  const global_ = useGlobalIndices()
  const fx = useFxCommodities()
  const sent = useSentiment()
  const sectors = useSectorHeatmap()
  const news = useHanriverNews(20)

  return (
    <div className="space-y-4">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">HANRIVER</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            한강 흐름을 읽다 · 통합 시황 대시보드
          </p>
        </div>
        <div className="text-xs text-slate-500">
          KR 지수: pykrx(일봉 종가) · 해외/환율/원자재/VIX: yfinance · F&G: alternative.me
        </div>
      </header>

      <IndexCardGrid title="국내 지수" quotes={kr.data} loading={kr.loading} columns={4} />
      <IndexCardGrid
        title="해외 지수"
        quotes={global_.data}
        loading={global_.loading}
        columns={8}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <QuoteListPanel title="환율 & 원자재" quotes={fx.data} loading={fx.loading} />
        <QuoteListPanel title="시장 심리" quotes={sent.data} loading={sent.loading} />
      </div>

      <SectorHeatmap quotes={sectors.data} loading={sectors.loading} />

      <NewsFeed items={news.data} loading={news.loading} />
    </div>
  )
}
