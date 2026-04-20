"""기술적 지표 엔진 (순수 pandas/numpy).

- MA / RSI / MACD / Bollinger
- VSA (Volume Spread Analysis): Sign of Strength / Weakness / Test

VSA 룰 (Tom Williams):
  - Sign of Strength (SOS): 거래량 급증 + 큰 하락봉 but 종가가 중간 이상
    → 세력 매집
  - Sign of Weakness (SOW): 거래량 급증 + 큰 상승봉 but 종가가 중간 이하
    → 세력 분배
  - Upthrust: 전고점 돌파 후 같은 봉에서 반락
  - Test: 좁은 스프레드 + 거래량 축소 (매도 압력 소진 확인)

출력은 시그널별 boolean Series + 부가 feature dict.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    diff = close.diff()
    gain = diff.clip(lower=0.0)
    loss = -diff.clip(upper=0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, window: int = 20, std: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    dev = close.rolling(window).std()
    return pd.DataFrame({"mid": mid, "upper": mid + std * dev, "lower": mid - std * dev})


def vwap(df: pd.DataFrame) -> pd.Series:
    """Intraday VWAP. df는 high, low, close, volume 필요."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    pv = typical * df["volume"]
    return pv.cumsum() / df["volume"].cumsum().replace(0, np.nan)


# ──────────────────────────────────────────────────────
# VSA
# ──────────────────────────────────────────────────────

def vsa(df: pd.DataFrame, lookback: int = 30) -> pd.DataFrame:
    """VSA 시그널 컬럼을 담은 DataFrame 반환.

    입력 df: open, high, low, close, volume (index는 날짜)
    반환 컬럼: spread, close_pos, vol_ratio, sos, sow, upthrust, test
    """
    out = pd.DataFrame(index=df.index)
    out["spread"] = df["high"] - df["low"]
    # 종가가 스프레드 내에서 어디에 위치하는가 (0=저점, 1=고점)
    out["close_pos"] = np.where(
        out["spread"] > 0,
        (df["close"] - df["low"]) / out["spread"],
        0.5,
    )
    vol_mean = df["volume"].rolling(lookback).mean()
    out["vol_ratio"] = df["volume"] / vol_mean.replace(0, np.nan)
    spread_mean = out["spread"].rolling(lookback).mean()
    spread_ratio = out["spread"] / spread_mean.replace(0, np.nan)

    prev_close = df["close"].shift(1)
    down_bar = df["close"] < prev_close
    up_bar = df["close"] > prev_close

    # Sign of Strength: 큰 하락봉 + 거래량 급증 + 종가가 중간 이상 (세력 매집)
    out["sos"] = (
        down_bar
        & (spread_ratio > 1.5)
        & (out["vol_ratio"] > 1.8)
        & (out["close_pos"] >= 0.5)
    )

    # Sign of Weakness: 큰 상승봉 + 거래량 급증 + 종가가 중간 이하 (세력 분배)
    out["sow"] = (
        up_bar
        & (spread_ratio > 1.5)
        & (out["vol_ratio"] > 1.8)
        & (out["close_pos"] <= 0.5)
    )

    # Upthrust: 전고점 돌파 후 반락
    prior_high = df["high"].shift(1).rolling(lookback).max()
    out["upthrust"] = (
        (df["high"] > prior_high)
        & (df["close"] < prior_high)
        & (out["vol_ratio"] > 1.3)
    )

    # Test: 좁은 스프레드 + 거래량 축소 + 하락 지역에서 (매도압력 소진)
    out["test"] = (
        (spread_ratio < 0.7)
        & (out["vol_ratio"] < 0.7)
        & down_bar.rolling(3).sum().fillna(0).gt(0)
    )

    return out


def latest_snapshot(df: pd.DataFrame) -> dict:
    """최근 봉의 지표 묶음을 dict로 반환 (API 응답용)."""
    if df is None or df.empty:
        return {}
    close = df["close"]
    out = {
        "close": float(close.iloc[-1]),
        "ma20": _safe_last(sma(close, 20)),
        "ma60": _safe_last(sma(close, 60)),
        "ma120": _safe_last(sma(close, 120)),
        "rsi14": _safe_last(rsi(close, 14)),
    }
    mcd = macd(close)
    out["macd"] = _safe_last(mcd["macd"])
    out["macd_signal"] = _safe_last(mcd["signal"])
    out["macd_hist"] = _safe_last(mcd["hist"])
    bb = bollinger(close)
    out["bb_upper"] = _safe_last(bb["upper"])
    out["bb_lower"] = _safe_last(bb["lower"])

    if {"open", "high", "low", "volume"}.issubset(df.columns):
        v = vsa(df)
        last = v.iloc[-1]
        out["vsa"] = {
            "sos": bool(last["sos"]),
            "sow": bool(last["sow"]),
            "upthrust": bool(last["upthrust"]),
            "test": bool(last["test"]),
            "vol_ratio": _safe_last(v["vol_ratio"]),
            "close_pos": _safe_last(v["close_pos"]),
        }
    return out


def _safe_last(s: pd.Series) -> float | None:
    if s is None or s.empty:
        return None
    v = s.iloc[-1]
    if pd.isna(v):
        return None
    return float(v)
