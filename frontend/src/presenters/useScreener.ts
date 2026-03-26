import api from './api'
import { useScreenerStore } from '../models/screenerStore'

export function useScreener() {
  const { results, loading, lastScanned, setResults, setLoading, setLastScanned } =
    useScreenerStore()

  async function scan(customSymbols?: string, periodDays = 252, thresholdPct = 97) {
    setLoading(true)
    try {
      const params: Record<string, string | number> = {
        period_days: periodDays,
        threshold_pct: thresholdPct,
      }
      if (customSymbols?.trim()) {
        params.symbols = customSymbols.trim()
      }
      const res = await api.get('/api/v1/screener/new-highs', { params })
      setResults(res.data)
      setLastScanned(new Date().toLocaleTimeString('ko-KR'))
    } catch (e) {
      console.error('신고가 스캔 실패:', e)
    } finally {
      setLoading(false)
    }
  }

  return { results, loading, lastScanned, scan }
}
