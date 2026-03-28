import { create } from 'zustand'

export interface ResearchResult {
  symbol: string
  name: string
  research_date: string
  period_days: number
  rsi: number | null
  ma5: number | null
  ma20: number | null
  ma60: number | null
  macd_val: number | null
  macd_signal_val: number | null
  high_period: number | null
  high_pct: number | null
  volume_ratio: number | null
  signals: {
    rsi?: string
    rsi_value?: number
    ma?: string
    ma60?: string
    macd?: string
    high_pct?: number
    high_status?: string
    volume?: string
    volume_ratio?: number
    [key: string]: unknown
  }
  composite_score: number
  summary: string
}

interface ResearchState {
  results: ResearchResult[]
  loading: boolean
  lastScanned: string | null
  setResults: (results: ResearchResult[]) => void
  setLoading: (v: boolean) => void
  setLastScanned: (t: string) => void
}

export const useResearchStore = create<ResearchState>((set) => ({
  results: [],
  loading: false,
  lastScanned: null,
  setResults: (results) => set({ results }),
  setLoading: (loading) => set({ loading }),
  setLastScanned: (lastScanned) => set({ lastScanned }),
}))
