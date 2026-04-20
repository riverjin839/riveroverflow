"""백테스트 엔진 MVP.

간단한 벡터화 백테스트:
- strategy: ma_cross | rsi | vsa
- 각 봉의 신호를 생성 → 다음 봉 시가에 진입/청산
- 수수료·슬리피지 0.15% 가정
- 결과: 총 수익률, 승률, profit factor, MDD, sharpe(일간)

Phase 4 수준. Phase 5에서 walk-forward / multi-symbol 확장.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from . import indicators

FEE_RATE = 0.0015


async def run(
    broker,
    symbol: str,
    strategy: str,
    params: dict[str, Any],
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    ohlcv = await broker.get_ohlcv(symbol, "D", 800)
    if not ohlcv:
        return {"metrics": _empty_metrics(), "trades": []}

    df = pd.DataFrame(ohlcv)
    df["time"] = pd.to_datetime(df["time"])
    df = df[(df["time"] >= pd.to_datetime(start_date)) & (df["time"] <= pd.to_datetime(end_date))]
    df = df.reset_index(drop=True)
    if len(df) < 30:
        return {"metrics": _empty_metrics(), "trades": []}

    signals = _signals(df, strategy, params)

    trades = _simulate(df, signals)
    metrics = _metrics(trades, df)
    return {"metrics": metrics, "trades": trades[-50:]}


def _signals(df: pd.DataFrame, strategy: str, params: dict) -> pd.Series:
    s = pd.Series(0, index=df.index, dtype=int)  # 1=buy, -1=sell
    close = df["close"]
    if strategy == "ma_cross":
        short = params.get("short", 5)
        long_ = params.get("long", 20)
        ma_s = indicators.sma(close, short)
        ma_l = indicators.sma(close, long_)
        prev_above = (ma_s.shift(1) > ma_l.shift(1))
        now_above = (ma_s > ma_l)
        s[(~prev_above) & now_above] = 1
        s[prev_above & (~now_above)] = -1
    elif strategy == "rsi":
        period = params.get("period", 14)
        low = params.get("oversold", 30)
        high = params.get("overbought", 70)
        rsi_v = indicators.rsi(close, period)
        s[(rsi_v.shift(1) >= low) & (rsi_v < low)] = 1
        s[(rsi_v.shift(1) <= high) & (rsi_v > high)] = -1
    elif strategy == "vsa":
        v = indicators.vsa(df)
        s[v["sos"]] = 1
        s[v["sow"]] = -1
    return s


def _simulate(df: pd.DataFrame, signals: pd.Series) -> list[dict]:
    position = 0
    entry_price = 0.0
    trades: list[dict] = []
    for i in range(len(df) - 1):
        sig = signals.iloc[i]
        next_open = float(df.iloc[i + 1]["open"])
        when = df.iloc[i + 1]["time"].isoformat()
        if sig == 1 and position == 0:
            position = 1
            entry_price = next_open * (1 + FEE_RATE)
            trades.append({"type": "enter", "time": when, "price": entry_price})
        elif sig == -1 and position == 1:
            exit_price = next_open * (1 - FEE_RATE)
            pnl_pct = (exit_price - entry_price) / entry_price
            trades.append({
                "type": "exit", "time": when, "price": exit_price,
                "pnl_pct": round(pnl_pct, 4),
            })
            position = 0

    # 마감 처리
    if position == 1:
        last_close = float(df.iloc[-1]["close"]) * (1 - FEE_RATE)
        pnl_pct = (last_close - entry_price) / entry_price
        trades.append({
            "type": "exit", "time": df.iloc[-1]["time"].isoformat(),
            "price": last_close, "pnl_pct": round(pnl_pct, 4),
        })
    return trades


def _metrics(trades: list[dict], df: pd.DataFrame) -> dict[str, float]:
    closed = [t for t in trades if t["type"] == "exit"]
    if not closed:
        return _empty_metrics()

    pnls = [t["pnl_pct"] for t in closed]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    cum = 1.0
    equity = []
    for p in pnls:
        cum *= (1 + p)
        equity.append(cum)
    equity_s = pd.Series(equity) if equity else pd.Series([1.0])
    peak = equity_s.cummax()
    dd = (equity_s - peak) / peak
    mdd = float(dd.min()) if not dd.empty else 0.0

    profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf") if wins else 0.0
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    total_return = cum - 1

    daily_returns = pd.Series(pnls)
    sharpe = 0.0
    if len(daily_returns) >= 2 and daily_returns.std():
        sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))

    return {
        "trade_count": len(pnls),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else 999.0,
        "total_return": round(total_return, 4),
        "mdd": round(mdd, 4),
        "sharpe": round(sharpe, 3),
    }


def _empty_metrics() -> dict[str, float]:
    return {
        "trade_count": 0, "win_rate": 0.0, "profit_factor": 0.0,
        "total_return": 0.0, "mdd": 0.0, "sharpe": 0.0,
    }
