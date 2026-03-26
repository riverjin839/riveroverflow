import { create } from 'zustand'

export interface NewHighResult {
  symbol: string
  name: string
  current_price: number
  high_52w: number
  high_pct: number
  volume: number
  is_new_high: boolean
}

interface ScreenerState {
  results: NewHighResult[]
  loading: boolean
  lastScanned: string | null
  setResults: (results: NewHighResult[]) => void
  setLoading: (v: boolean) => void
  setLastScanned: (t: string) => void
}

export const useScreenerStore = create<ScreenerState>((set) => ({
  results: [],
  loading: false,
  lastScanned: null,
  setResults: (results) => set({ results }),
  setLoading: (loading) => set({ loading }),
  setLastScanned: (lastScanned) => set({ lastScanned }),
}))
