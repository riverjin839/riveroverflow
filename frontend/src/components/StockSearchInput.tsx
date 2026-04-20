import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import api from '../presenters/api'

type SearchItem = { symbol: string; name: string; market: string }

type Props = {
  value: string
  onChange: (value: string) => void
  onSelect?: (item: SearchItem) => void
  placeholder?: string
  className?: string
  autoFocus?: boolean
}

// 간단한 디바운스 훅
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

export default function StockSearchInput({
  value, onChange, onSelect, placeholder = '종목명 또는 코드', className, autoFocus,
}: Props) {
  const [items, setItems] = useState<SearchItem[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const [loading, setLoading] = useState(false)
  const debounced = useDebounce(value, 180)
  const wrapRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!debounced || debounced.length < 1) {
      setItems([])
      return
    }
    let alive = true
    setLoading(true)
    api
      .get<SearchItem[]>('/api/v1/hanriver/stocks/search', {
        params: { q: debounced, limit: 8 },
      })
      .then((r) => {
        if (!alive) return
        setItems(r.data)
        setOpen(true)
        setActive(0)
      })
      .catch(() => alive && setItems([]))
      .finally(() => alive && setLoading(false))
    return () => {
      alive = false
    }
  }, [debounced])

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  function choose(it: SearchItem) {
    onChange(it.symbol)
    onSelect?.(it)
    setOpen(false)
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((i) => Math.min(i + 1, items.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((i) => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      if (items[active]) {
        e.preventDefault()
        choose(items[active])
      }
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div ref={wrapRef} className={clsx('relative', className)}>
      <input
        className="input w-full"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => items.length && setOpen(true)}
        onKeyDown={onKey}
        placeholder={placeholder}
        autoFocus={autoFocus}
      />
      {open && items.length > 0 && (
        <ul className="absolute z-20 left-0 right-0 mt-1 bg-surface-card border border-surface-border rounded shadow-lg max-h-72 overflow-auto">
          {items.map((it, idx) => (
            <li
              key={it.symbol}
              className={clsx(
                'px-3 py-2 text-sm cursor-pointer flex items-center gap-2',
                idx === active ? 'bg-brand-500/20 text-white' : 'text-slate-200 hover:bg-surface-border',
              )}
              onMouseDown={(e) => {
                e.preventDefault()
                choose(it)
              }}
              onMouseEnter={() => setActive(idx)}
            >
              <span className="text-brand-500 font-mono text-xs w-16">{it.symbol}</span>
              <span className="flex-1 truncate">{it.name}</span>
              <span className="text-xs text-slate-500">{it.market}</span>
            </li>
          ))}
        </ul>
      )}
      {loading && value && items.length === 0 && (
        <div className="absolute z-20 left-0 right-0 mt-1 bg-surface-card border border-surface-border rounded px-3 py-2 text-xs text-slate-500">
          검색 중...
        </div>
      )}
    </div>
  )
}
