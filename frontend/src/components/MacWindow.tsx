import clsx from 'clsx'
import type { ReactNode } from 'react'

type Props = {
  title?: ReactNode
  className?: string
  padding?: 'none' | 'md' | 'lg'
  children: ReactNode
  trailing?: ReactNode  // 헤더 오른쪽 액션 영역
  bodyClassName?: string
  headerless?: boolean  // traffic light 헤더 숨김 (hero 전용)
}

// macOS Sonoma 윈도우 카드: 상단 traffic light + 중앙 타이틀 + 본문
export default function MacWindow({
  title,
  className,
  padding = 'md',
  children,
  trailing,
  bodyClassName,
  headerless,
}: Props) {
  return (
    <section className={clsx('card overflow-hidden', className)}>
      {!headerless && (
        <header className="relative flex items-center h-9 px-3 border-b border-surface-border bg-surface-card">
          <div className="traffic-lights">
            <span className="traffic-light red" />
            <span className="traffic-light yellow" />
            <span className="traffic-light green" />
          </div>
          {title && (
            <div className="absolute left-1/2 -translate-x-1/2 eyebrow pointer-events-none">
              {title}
            </div>
          )}
          {trailing && <div className="ml-auto">{trailing}</div>}
        </header>
      )}
      <div
        className={clsx(
          {
            'p-0': padding === 'none',
            'p-4': padding === 'md',
            'p-6': padding === 'lg',
          },
          bodyClassName,
        )}
      >
        {children}
      </div>
    </section>
  )
}

// 중첩 미니 카드 (Humidity/Wind/... 스타일)
export function MacMiniCard({
  icon, label, value, hint, className,
}: {
  icon?: ReactNode
  label: string
  value: ReactNode
  hint?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('card-inner p-3.5 shadow-mac', className)}>
      <div className="flex items-center gap-1.5 text-ink-muted text-xs mb-1.5">
        {icon}
        <span>{label}</span>
      </div>
      <div className="text-lg font-semibold text-ink tabular-nums leading-tight">{value}</div>
      {hint && <div className="text-[11px] text-ink-subtle mt-1">{hint}</div>}
    </div>
  )
}

// 선형 프로그레스 바 (7-day forecast 온도 바 스타일)
export function MacProgressBar({
  value, max = 100, className,
}: {
  value: number  // 0~100 퍼센트
  max?: number
  className?: string
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className={clsx('h-2 rounded-full bg-surface-border overflow-hidden', className)}>
      <div
        className="h-full bg-brand-600 rounded-full transition-[width] duration-500"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
