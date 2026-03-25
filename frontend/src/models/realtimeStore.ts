import { create } from 'zustand'
import { usePortfolioStore } from './portfolioStore'
import { useAuthStore } from './authStore'

export interface MarketTick {
  symbol: string
  name: string
  price: string
  change_pct: number
  volume: number
  time: string
}

export interface TradeEvent {
  order_id: string
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  price: string
  strategy_id: string
  signal_reason: string
  time: string
}

interface RealtimeState {
  connected: boolean
  ticks: Record<string, MarketTick>     // symbol → latest tick
  recentTrades: TradeEvent[]
  ws: WebSocket | null

  connect: () => void
  disconnect: () => void
}

export const useRealtimeStore = create<RealtimeState>((set, get) => ({
  connected: false,
  ticks: {},
  recentTrades: [],
  ws: null,

  connect: () => {
    const { ws } = get()
    if (ws) return

    const token = useAuthStore.getState().token
    const wsUrl = `${import.meta.env.VITE_WS_URL || 'ws://localhost:8080'}/ws?token=${token}`

    const socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      set({ connected: true })
    }

    socket.onclose = () => {
      set({ connected: false, ws: null })
      // Reconnect after 3s
      setTimeout(() => {
        if (useAuthStore.getState().token) {
          get().connect()
        }
      }, 3000)
    }

    socket.onerror = () => {
      set({ connected: false })
    }

    socket.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data)
        const data = typeof envelope.data === 'string'
          ? JSON.parse(envelope.data)
          : envelope.data

        switch (data?.type) {
          case 'price':
            set((state) => ({
              ticks: { ...state.ticks, [data.symbol]: data as MarketTick },
            }))
            break

          case 'trade':
            set((state) => ({
              recentTrades: [data as TradeEvent, ...state.recentTrades].slice(0, 100),
            }))
            break

          case 'portfolio':
            usePortfolioStore.getState().updateFromRealtimeEvent(data)
            break
        }
      } catch {
        // ignore malformed messages
      }
    }

    set({ ws: socket })
  },

  disconnect: () => {
    const { ws } = get()
    if (ws) {
      ws.close()
      set({ ws: null, connected: false })
    }
  },
}))
