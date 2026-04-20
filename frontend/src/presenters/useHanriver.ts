import { useEffect, useState } from 'react'
import api from './api'

export type Quote = {
  code: string
  name: string
  price: number
  change_pct: number | null
  ts: string
  stale: boolean
}

export type NewsItem = {
  id: number
  source: string
  title: string
  url: string
  importance: string
  published_at: string
}

function usePolled<T>(path: string, intervalMs: number, initial: T) {
  const [data, setData] = useState<T>(initial)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    let timer: ReturnType<typeof setTimeout> | undefined

    async function tick() {
      try {
        const res = await api.get<T>(path)
        if (!alive) return
        setData(res.data)
        setError(null)
      } catch (e) {
        if (!alive) return
        setError((e as Error).message)
      } finally {
        if (alive) {
          setLoading(false)
          timer = setTimeout(tick, intervalMs)
        }
      }
    }
    tick()

    return () => {
      alive = false
      if (timer) clearTimeout(timer)
    }
  }, [path, intervalMs])

  return { data, loading, error }
}

export const useKrIndices = () =>
  usePolled<Quote[]>('/api/v1/hanriver/indices/kr', 5_000, [])

export const useGlobalIndices = () =>
  usePolled<Quote[]>('/api/v1/hanriver/indices/global', 30_000, [])

export const useFxCommodities = () =>
  usePolled<Quote[]>('/api/v1/hanriver/fx', 30_000, [])

export const useSentiment = () =>
  usePolled<Quote[]>('/api/v1/hanriver/sentiment', 60_000, [])

export const useSectorHeatmap = () =>
  usePolled<Quote[]>('/api/v1/hanriver/heatmap/sectors', 30_000, [])

export const useHanriverNews = (limit = 20) =>
  usePolled<NewsItem[]>(`/api/v1/hanriver/news?limit=${limit}`, 60_000, [])
