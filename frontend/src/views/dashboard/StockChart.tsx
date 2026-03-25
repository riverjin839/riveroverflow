import { useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts'
import api from '../../presenters/api'

interface Props {
  symbol: string
  name: string
}

export default function StockChart({ symbol, name }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<ReturnType<typeof createChart> | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1e293b' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#334155' },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
      },
      width: containerRef.current.clientWidth,
      height: 280,
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444',
      downColor: '#3b82f6',
      borderUpColor: '#ef4444',
      borderDownColor: '#3b82f6',
      wickUpColor: '#ef4444',
      wickDownColor: '#3b82f6',
    })

    // Load OHLCV data
    api.get(`/api/v1/portfolio/ohlcv/${symbol}?period=D&count=100`)
      .then((res) => {
        const data = res.data.map((d: any) => ({
          time: d.time.substring(0, 10),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }))
        candleSeries.setData(data)
        chart.timeScale().fitContent()
      })
      .catch(() => {/* ignore if not connected */})

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol])

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-300">
          {name} ({symbol})
        </h2>
        <span className="text-xs text-slate-500">일봉</span>
      </div>
      <div ref={containerRef} />
    </div>
  )
}
