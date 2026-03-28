"""
조건식 엔진 — OHLCV DataFrame에서 N일 연속 패턴 조건을 평가한다.

지원 조건:
  - consecutive_bullish:              N일 연속 양봉 (close > open)
  - consecutive_bearish_no_wick:      N일 연속 꼬리없는 음봉 (close < open, wick ≤ wick_pct%)
  - trading_value_consecutive:        N일 연속 거래대금(close×volume) >= threshold억
  - monthly_cumulative_trading_value: N개월 누적 거래대금 합계 >= threshold억
  - price_above_ma:                   현재가(종가) > 이동평균(ma_period일)
  - symbol_in_list:                   종목코드가 지정 목록에 포함
"""
from typing import Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field


class ConditionSpec(BaseModel):
    type: Literal[
        "consecutive_bullish",
        "consecutive_bearish_no_wick",
        "trading_value_consecutive",
        "monthly_cumulative_trading_value",
        "price_above_ma",
        "symbol_in_list",
    ]
    n: int = Field(default=3, ge=1, le=20, description="연속 일수")
    threshold: float = Field(default=0.0, ge=0, description="거래대금 기준 (억 KRW)")
    wick_pct: float = Field(default=1.0, ge=0, le=100, description="꼬리 허용 비율 (%)")
    months: int = Field(default=1, ge=1, le=12, description="누적 거래대금 기준 개월수")
    ma_period: int = Field(default=20, description="이동평균 기간 (5/20/60/120/200)")
    symbols: list[str] = Field(default_factory=list, description="허용 종목코드 목록")

    def label(self) -> str:
        """사람이 읽기 쉬운 한글 설명"""
        if self.type == "consecutive_bullish":
            return f"{self.n}일 연속 양봉"
        elif self.type == "consecutive_bearish_no_wick":
            return f"{self.n}일 연속 꼬리없는 음봉 (꼬리 {self.wick_pct}% 이내)"
        elif self.type == "trading_value_consecutive":
            t = int(self.threshold)
            return f"거래대금 {self.n}일 연속 {t:,}억 이상"
        elif self.type == "monthly_cumulative_trading_value":
            t = int(self.threshold)
            return f"{self.months}개월 누적 거래대금 {t:,}억 이상"
        elif self.type == "price_above_ma":
            return f"현재가 MA{self.ma_period} 상회"
        elif self.type == "symbol_in_list":
            return f"종목 리스트 포함 ({len(self.symbols)}개)"
        return self.type


def evaluate_conditions(
    df: pd.DataFrame,
    conditions: list[ConditionSpec],
    symbol: Optional[str] = None,
) -> bool:
    """모든 조건을 AND 논리로 평가. df는 OHLCV 컬럼(open/high/low/close/volume)을 가져야 한다."""
    if df is None or df.empty:
        return False
    for cond in conditions:
        if not _eval_one(df, cond, symbol):
            return False
    return True


def _eval_one(
    df: pd.DataFrame, cond: ConditionSpec, symbol: Optional[str] = None
) -> bool:
    # ── 종목 리스트 조건 (df 불필요) ─────────────────────
    if cond.type == "symbol_in_list":
        if not cond.symbols:
            return True  # 목록 비어있으면 모두 통과
        return bool(symbol and symbol in cond.symbols)

    # ── MA 상회 조건 ──────────────────────────────────────
    if cond.type == "price_above_ma":
        if len(df) < cond.ma_period:
            return False
        ma = df["close"].rolling(cond.ma_period).mean().iloc[-1]
        current = df["close"].iloc[-1]
        return bool(pd.notna(ma) and current > ma)

    # ── 월 누적 거래대금 조건 ─────────────────────────────
    if cond.type == "monthly_cumulative_trading_value":
        days_needed = cond.months * 22  # 월 22거래일 기준
        if len(df) < days_needed:
            return False
        tail = df.tail(days_needed)
        total_tv = float((tail["close"] * tail["volume"]).sum())
        return total_tv >= cond.threshold * 1e8

    # ── 연속 N일 조건 (tail 필요) ─────────────────────────
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
