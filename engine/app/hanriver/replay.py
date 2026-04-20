"""타임머신 모드 — 특정 일자의 시황·차트·뉴스·매매를 동시 재현.

Phase 4 MVP: 다음을 하나의 응답으로 묶어 반환
- 그날까지의 OHLCV (200봉)
- 그날 기준 기술적 지표 스냅샷
- 그날 전후 뉴스
- 그날 사용자 매매 기록 (있으면)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import indicators
from ..models.hanriver import NewsItem
from ..models.trade import Trade


async def snapshot(
    broker,
    session: AsyncSession,
    symbol: str,
    target_date: str,
) -> dict[str, Any]:
    target_dt = datetime.fromisoformat(target_date)

    ohlcv = await broker.get_ohlcv(symbol, "D", 400)
    df = pd.DataFrame(ohlcv)
    if not df.empty:
        df["time_dt"] = pd.to_datetime(df["time"])
        df_sliced = df[df["time_dt"] <= target_dt].tail(200).drop(columns=["time_dt"])
    else:
        df_sliced = df

    ind = indicators.latest_snapshot(df_sliced) if not df_sliced.empty else {}

    news_rows = (await session.execute(
        select(NewsItem)
        .where(
            NewsItem.published_at >= target_dt - timedelta(days=1),
            NewsItem.published_at <= target_dt + timedelta(days=1),
        )
        .order_by(NewsItem.published_at.desc())
        .limit(30)
    )).scalars().all()

    trades = (await session.execute(
        select(Trade)
        .where(
            Trade.symbol == symbol,
            Trade.created_at >= target_dt - timedelta(hours=6),
            Trade.created_at <= target_dt + timedelta(hours=18),
        )
    )).scalars().all()

    return {
        "symbol": symbol,
        "target_date": target_date,
        "ohlcv": df_sliced.to_dict(orient="records"),
        "indicators": ind,
        "news": [
            {"id": n.id, "source": n.source, "title": n.title, "url": n.url,
             "published_at": n.published_at.isoformat()}
            for n in news_rows
        ],
        "trades": [
            {"id": t.id, "side": t.side, "quantity": t.quantity,
             "price": float(t.price), "created_at": t.created_at.isoformat()}
            for t in trades
        ],
    }
