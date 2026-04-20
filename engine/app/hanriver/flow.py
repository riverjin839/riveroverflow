"""수급 데이터 수집 (외국인/기관/개인 일별 순매수).

pykrx 사용. 당일 데이터는 장 마감 후 집계되므로 T-1 기준.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import TypedDict

logger = logging.getLogger(__name__)


class FlowRow(TypedDict):
    trade_date: str
    foreign_net: float
    institution_net: float
    individual_net: float


def _flow_sync(symbol: str, days: int) -> list[FlowRow]:
    from pykrx import stock as krx

    end = date.today()
    start = end - timedelta(days=days * 2)

    try:
        df = krx.get_market_trading_value_by_date(
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            symbol,
            etf=False,
            etn=False,
            elw=False,
        )
    except Exception as e:
        logger.warning("pykrx flow fetch failed symbol=%s: %s", symbol, e)
        return []

    if df is None or df.empty:
        return []

    df = df.tail(days)
    out: list[FlowRow] = []
    for idx, row in df.iterrows():
        try:
            out.append(FlowRow(
                trade_date=str(idx.date()),
                foreign_net=float(row.get("외국인합계", row.get("외국인", 0))),
                institution_net=float(row.get("기관합계", 0)),
                individual_net=float(row.get("개인", 0)),
            ))
        except (KeyError, ValueError):
            continue
    return out


async def fetch_flow(symbol: str, days: int = 30) -> list[FlowRow]:
    return await asyncio.get_event_loop().run_in_executor(None, _flow_sync, symbol, days)


def _short_balance_sync(symbol: str) -> dict | None:
    from pykrx import stock as krx

    end = date.today()
    start = end - timedelta(days=14)
    try:
        df = krx.get_shorting_balance_by_date(
            start.strftime("%Y%m%d"),
            end.strftime("%Y%m%d"),
            symbol,
        )
    except Exception as e:
        logger.warning("pykrx short balance failed symbol=%s: %s", symbol, e)
        return None
    if df is None or df.empty:
        return None
    last = df.iloc[-1]
    return {
        "balance_qty": float(last.get("공매도잔고", 0)),
        "balance_value": float(last.get("공매도잔고금액", 0)),
        "ratio": float(last.get("비중", 0)),
    }


async def fetch_short_balance(symbol: str) -> dict | None:
    return await asyncio.get_event_loop().run_in_executor(None, _short_balance_sync, symbol)
