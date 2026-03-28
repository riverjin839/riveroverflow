import { create } from 'zustand'

export interface ConditionSpec {
  type: 'consecutive_bullish' | 'consecutive_bearish_no_wick' | 'trading_value_consecutive'
  n: number
  threshold?: number   // 억 KRW (trading_value 전용)
  wick_pct?: number    // % (bearish_no_wick 전용)
}

export interface ConditionResult {
  symbol: string
  name: string
  current_price: number
  volume: number
  matched_conditions: string[]
}

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
  conditionResults: ConditionResult[]
  conditionLoading: boolean
  setConditionResults: (results: ConditionResult[]) => void
  setConditionLoading: (v: boolean) => void
}

export const useResearchStore = create<ResearchState>((set) => ({
  results: [],
  loading: false,
  lastScanned: null,
  setResults: (results) => set({ results }),
  setLoading: (loading) => set({ loading }),
  setLastScanned: (lastScanned) => set({ lastScanned }),
  conditionResults: [],
  conditionLoading: false,
  setConditionResults: (conditionResults) => set({ conditionResults }),
  setConditionLoading: (conditionLoading) => set({ conditionLoading }),
}))
