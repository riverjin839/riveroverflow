import { useEffect } from 'react'
import { usePortfolioStore } from '../models/portfolioStore'
import { useRealtimeStore } from '../models/realtimeStore'
import api from './api'

export function usePortfolio() {
  const { balance, positions, loading, setBalance, setPositions, setLoading } =
    usePortfolioStore()
  const connect = useRealtimeStore((s) => s.connect)

  useEffect(() => {
    connect()
    fetchPortfolio()
  }, [])

  async function fetchPortfolio() {
    setLoading(true)
    try {
      const [balRes, posRes] = await Promise.all([
        api.get('/api/v1/portfolio/balance'),
        api.get('/api/v1/portfolio/positions'),
      ])
      setBalance(balRes.data)
      setPositions(posRes.data)
    } catch (e) {
      console.error('Portfolio fetch error:', e)
    } finally {
      setLoading(false)
    }
  }

  return { balance, positions, loading, refetch: fetchPortfolio }
}
