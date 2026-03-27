import { useEffect } from 'react'
import api from './api'
import { useResearchStore } from '../models/researchStore'

export function useResearch() {
  const { results, loading, lastScanned, setResults, setLoading, setLastScanned } =
    useResearchStore()

  useEffect(() => {
    fetchLatest()
  }, [])

  async function fetchLatest(minScore = 0) {
    setLoading(true)
    try {
      const res = await api.get('/api/v1/research/results/latest', {
        params: { min_score: minScore },
      })
      setResults(res.data)
      if (res.data.length > 0) {
        setLastScanned(res.data[0].research_date)
      }
    } catch (e) {
      console.error('리서치 결과 로드 실패:', e)
    } finally {
      setLoading(false)
    }
  }

  async function runScan(symbols?: string[], periodDays = 60) {
    setLoading(true)
    try {
      const res = await api.post('/api/v1/research/scan', {
        symbols: symbols && symbols.length > 0 ? symbols : null,
        period_days: periodDays,
      })
      setResults(res.data)
      setLastScanned(new Date().toLocaleDateString('ko-KR'))
    } catch (e) {
      console.error('리서치 스캔 실패:', e)
    } finally {
      setLoading(false)
    }
  }

  return { results, loading, lastScanned, runScan, fetchLatest }
}
