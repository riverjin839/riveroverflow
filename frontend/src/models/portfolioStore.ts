import { create } from 'zustand'

export interface Position {
  symbol: string
  name: string
  quantity: number
  avg_price: string
  current_price: string
  profit_loss: string
  profit_loss_pct: number
}

export interface Balance {
  total_value: string
  cash: string
  stock_value: string
  profit_loss: string
  profit_loss_pct: number
  currency: string
}

interface PortfolioState {
  balance: Balance | null
  positions: Position[]
  loading: boolean
  setBalance: (balance: Balance) => void
  setPositions: (positions: Position[]) => void
  setLoading: (v: boolean) => void
  updateFromRealtimeEvent: (event: any) => void
}

export const usePortfolioStore = create<PortfolioState>((set) => ({
  balance: null,
  positions: [],
  loading: false,

  setBalance: (balance) => set({ balance }),
  setPositions: (positions) => set({ positions }),
  setLoading: (loading) => set({ loading }),

  updateFromRealtimeEvent: (event) => {
    if (event.type !== 'portfolio') return
    set({
      balance: {
        total_value: event.total_value,
        cash: event.cash,
        stock_value: event.stock_value,
        profit_loss: event.profit_loss,
        profit_loss_pct: event.profit_loss_pct,
        currency: 'KRW',
      },
      positions: event.positions ?? [],
    })
  },
}))
