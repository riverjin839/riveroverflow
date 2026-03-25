export function formatKRW(value: string | number | undefined | null): string {
  if (value === null || value === undefined) return '-'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (isNaN(n)) return '-'
  return n.toLocaleString('ko-KR') + '원'
}

export function formatPct(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function getPctColor(value: number): string {
  if (value > 0) return 'text-up'
  if (value < 0) return 'text-down'
  return 'text-slate-400'
}
