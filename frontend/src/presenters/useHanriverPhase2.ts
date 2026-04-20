import api from './api'

export type OhlcvPoint = {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type StockDetail = {
  symbol: string
  name: string
  price: number
  change_pct: number
  volume: number
  indicators: Record<string, unknown>
}

export type FlowRow = {
  trade_date: string
  foreign_net: number
  institution_net: number
  individual_net: number
}

export type Disclosure = {
  corp_name: string
  symbol: string | null
  report_name: string
  rcept_no: string
  rcept_dt: string
  url: string
}

export type WatchlistItem = {
  id: number
  symbol: string
  name: string
  tags: string | null
  memo: string | null
}

export type AlertItem = {
  id: number
  symbol: string
  rule_type: string
  threshold: number | null
  enabled: boolean
  last_triggered: string | null
  memo: string | null
}

export type AiSignal = {
  id: number
  symbol: string
  name: string
  mode: string
  signal: string
  entry_price: number | null
  stop_loss: number | null
  take_profit: number | null
  confidence: number
  rationale: string
  created_at: string
}

export type AiReport = {
  id: number
  report_type: string
  subject: string
  content_md: string
  created_at: string
}

export type JournalItem = {
  id: number
  trade_date: string
  symbol: string
  name: string
  side: string
  quantity: number
  price: number
  pnl: number | null
  setup: string | null
  draft: string | null
  user_note: string | null
}

export type BacktestSummary = {
  id: number
  name: string
  strategy_config: Record<string, unknown>
  metrics: Record<string, number>
  created_at: string
}

export const hanriverApi = {
  stockDetail: (symbol: string) =>
    api.get<StockDetail>(`/api/v1/hanriver/stock/${symbol}`),
  ohlcv: (symbol: string, count = 120) =>
    api.get<OhlcvPoint[]>(`/api/v1/hanriver/stock/${symbol}/ohlcv`, { params: { count } }),
  flow: (symbol: string, days = 30) =>
    api.get<FlowRow[]>(`/api/v1/hanriver/stock/${symbol}/flow`, { params: { days } }),
  short: (symbol: string) =>
    api.get(`/api/v1/hanriver/stock/${symbol}/short`),
  stockDisclosures: (symbol: string, days = 30) =>
    api.get<Disclosure[]>(`/api/v1/hanriver/stock/${symbol}/disclosures`, { params: { days } }),
  disclosures: (days = 1, limit = 50) =>
    api.get<Disclosure[]>(`/api/v1/hanriver/disclosures`, { params: { days, limit } }),

  watchlist: () => api.get<WatchlistItem[]>('/api/v1/hanriver/watchlist'),
  watchlistAdd: (body: Partial<WatchlistItem>) =>
    api.post<WatchlistItem>('/api/v1/hanriver/watchlist', body),
  watchlistRemove: (symbol: string) =>
    api.delete(`/api/v1/hanriver/watchlist/${symbol}`),

  alerts: () => api.get<AlertItem[]>('/api/v1/hanriver/alerts'),
  alertsAdd: (body: Partial<AlertItem>) =>
    api.post<AlertItem>('/api/v1/hanriver/alerts', body),
  alertsRemove: (id: number) => api.delete(`/api/v1/hanriver/alerts/${id}`),

  generateSignal: (symbol: string, mode: string) =>
    api.post<AiSignal>('/api/v1/hanriver/signals/generate', { symbol, mode }),
  listSignals: (limit = 30) =>
    api.get<AiSignal[]>('/api/v1/hanriver/signals', { params: { limit } }),

  generateReport: (report_type: string, subject: string) =>
    api.post<AiReport>('/api/v1/hanriver/reports/generate', { report_type, subject }),
  listReports: () => api.get<AiReport[]>('/api/v1/hanriver/reports'),

  scoreNews: () => api.post('/api/v1/hanriver/news/score-recent'),

  journalSync: () => api.post('/api/v1/hanriver/journal/sync'),
  listJournal: () => api.get<JournalItem[]>('/api/v1/hanriver/journal'),
  patchJournal: (id: number, body: { setup?: string; user_note?: string }) =>
    api.patch(`/api/v1/hanriver/journal/${id}`, body),
  coach: (id: number) => api.post(`/api/v1/hanriver/journal/${id}/coach`),

  replay: (symbol: string, target_date: string) =>
    api.post('/api/v1/hanriver/replay', { symbol, target_date }),

  runBacktest: (body: {
    name: string; symbol: string; strategy: string; params: Record<string, unknown>;
    start_date: string; end_date: string;
  }) => api.post('/api/v1/hanriver/backtest/run', body),
  listBacktest: () => api.get<BacktestSummary[]>('/api/v1/hanriver/backtest'),
}
