import { useEffect } from 'react'
import api from './api'
import { useResearchStore } from '../models/researchStore'
import type { ConditionSpec } from '../models/researchStore'

export function useResearch() {
  const {
    results, loading, lastScanned, setResults, setLoading, setLastScanned,
    conditionResults, conditionLoading, setConditionResults, setConditionLoading,
  } = useResearchStore()

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

  async function runConditionScan(symbols: string[] | undefined, conditions: ConditionSpec[]) {
    setConditionLoading(true)
    try {
      const res = await api.post('/api/v1/screener/conditions', {
        symbols: symbols && symbols.length > 0 ? symbols : null,
        conditions,
        period_days: 30,
      })
      setConditionResults(res.data)
    } catch (e) {
      console.error('조건 스크리닝 실패:', e)
    } finally {
      setConditionLoading(false)
    }
  }

  return { results, loading, lastScanned, runScan, fetchLatest, conditionResults, conditionLoading, runConditionScan }
}
