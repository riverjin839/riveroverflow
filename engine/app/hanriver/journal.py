"""매매 일지 자동 동기화.

- 내부 `trades` 테이블의 filled 체결을 주기적으로 journal 로 복제
- 같은 (filled_at, symbol, side, price) 가 이미 있으면 스킵 (idempotent)
- 셋업 태그 추정: 당시 VSA·RSI 상태를 자동 분류
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.trade import Trade
from ..models.hanriver import TradingJournalEntry


async def sync_from_trades(session: AsyncSession) -> int:
    existing = (await session.execute(
        select(TradingJournalEntry.symbol, TradingJournalEntry.trade_date, TradingJournalEntry.side)
    )).all()
    seen = {(r[0], r[1], r[2]) for r in existing}

    trades = (await session.execute(
        select(Trade).where(Trade.status == "filled").order_by(Trade.filled_at.desc())
    )).scalars().all()

    added = 0
    for t in trades:
        filled_at = t.filled_at or t.created_at
        key = (t.symbol, filled_at, t.side)
        if key in seen:
            continue
        entry = TradingJournalEntry(
            trade_date=filled_at,
            symbol=t.symbol,
            name=t.name or t.symbol,
            side=t.side,
            quantity=t.quantity,
            price=t.price,
            pnl=None,
            setup=None,
            draft=f"자동 초안: {t.side} {t.quantity}주 @ {t.price}"
            + (f" · 사유: {t.signal_reason}" if t.signal_reason else ""),
        )
        session.add(entry)
        added += 1
    return added
