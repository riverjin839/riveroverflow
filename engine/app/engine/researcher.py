"""
AutoResearcher: 종목별 기술적 지표를 자동으로 분석하고 ResearchResult를 생성한다.

온톨로지 아키텍처에서 이 클래스는 "Research" 액션을 실행하는 엔진이다.
  - 입력:  종목 목록 + 기간(일)
  - 처리:  RSI / MA / MACD / 52주 고가 / 거래량 비율 계산
  - 출력:  ResearchResult DB 저장 + OntologyObject(research) 생성
"""
import asyncio
import logging
from datetime import date, datetime
from typing import Optional

import pandas as pd
import pandas_ta as ta
from sqlalchemy import select

from ..broker.base import AbstractBroker
from ..core.database import AsyncSessionLocal
from ..models.ontology import OntologyLink, OntologyObject, ResearchResult

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = [
    "005930", "000660", "035420", "005380", "051910",
    "006400", "035720", "000270", "028260", "096770",
    "017670", "030200", "003550", "066570", "032830",
    "018260", "009150", "010130", "011170", "004020",
]


def _build_summary(name: str, signals: dict, score: float) -> str:
    parts = []
    rsi_sig = signals.get("rsi", "neutral")
    if rsi_sig == "oversold":
        parts.append("RSI 과매도 구간")
    elif rsi_sig == "overbought":
        parts.append("RSI 과매수 구간")

    ma_sig = signals.get("ma", "")
    if ma_sig == "golden_cross":
        parts.append("골든크로스")
    elif ma_sig == "dead_cross":
        parts.append("데드크로스")

    macd_sig = signals.get("macd", "")
    if macd_sig == "bullish":
        parts.append("MACD 강세")

    high_pct = signals.get("high_pct", 0)
    if high_pct and high_pct >= 95:
        parts.append(f"기간 고가 {high_pct:.1f}% 근접")

    vol_sig = signals.get("volume", "")
    if vol_sig == "spike":
        parts.append("거래량 급증")

    label = "강세" if score >= 70 else "중립" if score >= 40 else "약세"
    summary_text = " / ".join(parts) if parts else "특이 신호 없음"
    return f"[{label} {score:.0f}점] {name}: {summary_text}"


class AutoResearcher:
    def __init__(self, broker: AbstractBroker):
        self._broker = broker

    async def run(
        self,
        symbols: Optional[list[str]] = None,
        period_days: int = 60,
    ) -> list[dict]:
        """종목별 병렬 분석 후 DB 저장. 결과 요약 리스트 반환."""
        symbol_list = symbols or DEFAULT_SYMBOLS
        logger.info("AutoResearcher 시작: %d종목, 기간=%d일", len(symbol_list), period_days)

        tasks = [self._analyze(sym, period_days) for sym in symbol_list]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results = []
        async with AsyncSessionLocal() as session:
            today = date.today()
            for sym, res in zip(symbol_list, raw_results):
                if isinstance(res, Exception):
                    logger.warning("분석 실패 %s: %s", sym, res)
                    continue
                if res is None:
                    continue

                # 같은 날짜 결과가 있으면 덮어쓰지 않음
                existing = await session.execute(
                    select(ResearchResult).where(
                        ResearchResult.symbol == sym,
                        ResearchResult.research_date == today,
                    )
                )
                if existing.scalar_one_or_none():
                    results.append(self._to_dict(res))
                    continue

                session.add(res)

                # 온톨로지에 Stock 객체 upsert
                stock_key = f"stock:{sym}"
                stock_obj = await session.execute(
                    select(OntologyObject).where(OntologyObject.key == stock_key)
                )
                stock_obj = stock_obj.scalar_one_or_none()
                if not stock_obj:
                    stock_obj = OntologyObject(
                        type="stock",
                        key=stock_key,
                        properties={"symbol": sym, "name": res.name},
                    )
                    session.add(stock_obj)
                    await session.flush()

                # Research 객체 생성
                research_key = f"research:{sym}:{today.isoformat()}"
                research_obj = OntologyObject(
                    type="research",
                    key=research_key,
                    properties={
                        "symbol": sym,
                        "date": today.isoformat(),
                        "score": res.composite_score,
                        "signals": res.signals,
                        "summary": res.summary,
                    },
                )
                session.add(research_obj)
                await session.flush()

                # Stock → researched → Research 링크
                session.add(OntologyLink(
                    subject_id=stock_obj.id,
                    predicate="researched",
                    object_id=research_obj.id,
                    properties={"date": today.isoformat(), "score": res.composite_score},
                ))

                results.append(self._to_dict(res))

            await session.commit()

        results.sort(key=lambda r: r["composite_score"], reverse=True)
        logger.info("AutoResearcher 완료: %d건 저장", len(results))
        return results

    async def _analyze(self, symbol: str, period_days: int) -> Optional[ResearchResult]:
        ohlcv_count = max(period_days + 60, 120)  # 지표 안정화를 위해 여유있게
        try:
            ohlcv, market = await asyncio.gather(
                self._broker.get_ohlcv(symbol, "D", ohlcv_count),
                self._broker.get_market_price(symbol),
            )
        except Exception as e:
            raise RuntimeError(f"{symbol} 데이터 조회 실패: {e}") from e

        if not ohlcv or len(ohlcv) < 20:
            return None

        df = pd.DataFrame(ohlcv)
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["volume"] = df["volume"].astype(float)

        current_price = float(market.price)

        # ── 지표 계산 ──────────────────────────────
        rsi_series = ta.rsi(df["close"], length=14)
        rsi = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else None

        ma5 = float(df["close"].rolling(5).mean().iloc[-1])
        ma20 = float(df["close"].rolling(20).mean().iloc[-1])
        ma60_val = float(df["close"].rolling(60).mean().iloc[-1]) if len(df) >= 60 else None

        macd_df = ta.macd(df["close"], fast=12, slow=26, signal=9)
        macd_val = macd_signal_val = None
        if macd_df is not None and not macd_df.empty:
            macd_col = [c for c in macd_df.columns if "MACD_" in c and "MACDs_" not in c and "MACDh_" not in c]
            sig_col = [c for c in macd_df.columns if "MACDs_" in c]
            if macd_col:
                macd_val = float(macd_df[macd_col[0]].iloc[-1])
            if sig_col:
                macd_signal_val = float(macd_df[sig_col[0]].iloc[-1])

        period_slice = df["high"].tail(period_days)
        high_period = float(period_slice.max()) if not period_slice.empty else None
        high_pct = round(current_price / high_period * 100, 2) if high_period and high_period > 0 else None

        recent_vol = float(df["volume"].iloc[-1])
        avg_vol_20 = float(df["volume"].tail(20).mean())
        volume_ratio = round(recent_vol / avg_vol_20, 2) if avg_vol_20 > 0 else None

        # ── 시그널 판단 ────────────────────────────
        signals: dict = {}
        if rsi is not None:
            signals["rsi"] = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
            signals["rsi_value"] = round(rsi, 1)

        prev_ma5 = float(df["close"].rolling(5).mean().iloc[-2]) if len(df) >= 6 else ma5
        prev_ma20 = float(df["close"].rolling(20).mean().iloc[-2]) if len(df) >= 21 else ma20
        if prev_ma5 <= prev_ma20 and ma5 > ma20:
            signals["ma"] = "golden_cross"
        elif prev_ma5 >= prev_ma20 and ma5 < ma20:
            signals["ma"] = "dead_cross"
        else:
            signals["ma"] = "above_ma20" if current_price > ma20 else "below_ma20"

        if macd_val is not None and macd_signal_val is not None:
            signals["macd"] = "bullish" if macd_val > macd_signal_val else "bearish"

        if high_pct is not None:
            signals["high_pct"] = high_pct
            signals["high_status"] = "new_high" if current_price >= high_period else (
                "near_high" if high_pct >= 95 else "normal"
            )

        if volume_ratio is not None:
            signals["volume"] = "spike" if volume_ratio >= 2.0 else "normal"
            signals["volume_ratio"] = volume_ratio

        # ── 종합 스코어 (0~100) ────────────────────
        score = 0.0
        if rsi is not None and rsi < 30:
            score += 20
        if high_pct is not None and high_pct >= 95:
            score += 25
        if signals.get("ma") == "golden_cross":
            score += 20
        if signals.get("macd") == "bullish":
            score += 15
        if volume_ratio is not None and volume_ratio >= 2.0:
            score += 10
        if current_price > ma20:
            score += 10

        summary = _build_summary(market.name, signals, score)

        return ResearchResult(
            symbol=symbol,
            name=market.name,
            research_date=date.today(),
            period_days=period_days,
            rsi=rsi,
            ma5=ma5,
            ma20=ma20,
            ma60=ma60_val,
            macd_val=macd_val,
            macd_signal_val=macd_signal_val,
            high_period=high_period,
            high_pct=high_pct,
            volume_ratio=volume_ratio,
            signals=signals,
            composite_score=score,
            summary=summary,
        )

    @staticmethod
    def _to_dict(r: ResearchResult) -> dict:
        return {
            "symbol": r.symbol,
            "name": r.name,
            "research_date": r.research_date.isoformat() if r.research_date else None,
            "period_days": r.period_days,
            "rsi": r.rsi,
            "ma5": r.ma5,
            "ma20": r.ma20,
            "ma60": r.ma60,
            "macd_val": r.macd_val,
            "macd_signal_val": r.macd_signal_val,
            "high_period": r.high_period,
            "high_pct": r.high_pct,
            "volume_ratio": r.volume_ratio,
            "signals": r.signals,
            "composite_score": r.composite_score,
            "summary": r.summary,
        }
