"""
조건식 엔진 — OHLCV DataFrame에서 N일 연속 패턴 조건을 평가한다.

지원 조건:
  - consecutive_bullish:         N일 연속 양봉 (close > open)
  - consecutive_bearish_no_wick: N일 연속 꼬리없는 음봉 (close < open, wick ≤ wick_pct%)
  - trading_value_consecutive:   N일 연속 거래대금(close×volume) >= threshold억
"""
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field


class ConditionSpec(BaseModel):
    type: Literal[
        "consecutive_bullish",
        "consecutive_bearish_no_wick",
        "trading_value_consecutive",
    ]
    n: int = Field(default=3, ge=1, le=20, description="연속 일수")
    threshold: float = Field(default=0.0, ge=0, description="거래대금 기준 (억 KRW)")
    wick_pct: float = Field(default=1.0, ge=0, le=100, description="꼬리 허용 비율 (%)")

    def label(self) -> str:
        """사람이 읽기 쉬운 한글 설명"""
        if self.type == "consecutive_bullish":
            return f"{self.n}일 연속 양봉"
        elif self.type == "consecutive_bearish_no_wick":
            return f"{self.n}일 연속 꼬리없는 음봉 (꼬리 {self.wick_pct}% 이내)"
        elif self.type == "trading_value_consecutive":
            t = int(self.threshold)
            return f"거래대금 {self.n}일 연속 {t:,}억 이상"
        return self.type


def evaluate_conditions(df: pd.DataFrame, conditions: list[ConditionSpec]) -> bool:
    """모든 조건을 AND 논리로 평가. df는 OHLCV 컬럼(open/high/low/close/volume)을 가져야 한다."""
    if df is None or df.empty:
        return False
    for cond in conditions:
        if not _eval_one(df, cond):
            return False
    return True


def _eval_one(df: pd.DataFrame, cond: ConditionSpec) -> bool:
    if len(df) < cond.n:
        return False
    tail = df.tail(cond.n)

    if cond.type == "consecutive_bullish":
        return bool((tail["close"] > tail["open"]).all())

    elif cond.type == "consecutive_bearish_no_wick":
        bearish = tail["close"] < tail["open"]
        body_high = tail[["open", "close"]].max(axis=1)
        body_low = tail[["open", "close"]].min(axis=1)
        # 꼬리 = (고가 - 몸통상단) / 종가, (몸통하단 - 저가) / 종가
        upper_wick = (tail["high"] - body_high) / tail["close"].replace(0, float("nan"))
        lower_wick = (body_low - tail["low"]) / tail["close"].replace(0, float("nan"))
        threshold = cond.wick_pct / 100.0
        no_wick = (upper_wick <= threshold) & (lower_wick <= threshold)
        return bool((bearish & no_wick).all())

    elif cond.type == "trading_value_consecutive":
        trading_value = tail["close"] * tail["volume"]
        threshold_krw = cond.threshold * 1e8  # 억 → 원
        return bool((trading_value >= threshold_krw).all())

    return False
