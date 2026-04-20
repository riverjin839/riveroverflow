"""하이브리드 시그널 생성기 (룰 + LLM).

흐름:
1. 수급·지표·VSA 특성을 계산 (룰 베이스)
2. 특성 요약을 Claude 에게 전달해 시그널 + 근거 리포트 생성
3. 결과를 dict 로 반환 (라우터에서 DB 저장)
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from .. import indicators, flow as flow_mod
from . import claude_client

logger = logging.getLogger(__name__)


async def generate(broker, symbol: str, mode: str = "day") -> dict[str, Any]:
    market = await broker.get_market_price(symbol)
    ohlcv = await broker.get_ohlcv(symbol, "D", 200)
    df = pd.DataFrame(ohlcv) if ohlcv else pd.DataFrame()

    ind = indicators.latest_snapshot(df) if not df.empty else {}
    flows = await flow_mod.fetch_flow(symbol, days=5) if mode == "swing" else []

    features = {
        "symbol": symbol,
        "name": market.name,
        "price": float(market.price),
        "change_pct": market.change_pct or 0.0,
        "indicators": ind,
        "recent_flow": flows[-5:] if flows else [],
    }

    # 룰 기반 1차 판정
    signal, confidence = _rule_decide(ind, market.change_pct or 0.0, mode)

    entry = float(market.price)
    sl_pct = 0.03 if mode == "day" else 0.05
    tp_pct = 0.05 if mode == "day" else 0.08

    stop_loss = round(entry * (1 - sl_pct), 2) if signal == "buy" else None
    take_profit = round(entry * (1 + tp_pct), 2) if signal == "buy" else None

    # LLM 근거 리포트
    prompt = _build_prompt(mode, features, signal)
    rationale = await claude_client.complete(prompt, max_tokens=600)

    return {
        "symbol": symbol,
        "name": market.name,
        "signal": signal,
        "entry_price": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "confidence": round(confidence, 3),
        "rationale": rationale,
        "features": features,
    }


def _rule_decide(ind: dict, change_pct: float, mode: str) -> tuple[str, float]:
    """간단 룰:
    - VSA SOS + RSI < 45 → buy (높은 신뢰도)
    - VSA SOW + RSI > 55 → sell
    - 종가가 MA20 > MA60 (정배열) + MACD hist > 0 → buy
    - 그 외 hold
    """
    vsa = ind.get("vsa") or {}
    rsi_v = ind.get("rsi14")
    ma20 = ind.get("ma20")
    ma60 = ind.get("ma60")
    macd_hist = ind.get("macd_hist")
    close = ind.get("close")

    if vsa.get("sos") and (rsi_v is None or rsi_v < 45):
        return "buy", 0.75
    if vsa.get("sow") and (rsi_v is None or rsi_v > 55):
        return "sell", 0.70
    if (
        ma20 and ma60 and close
        and ma20 > ma60
        and close >= ma20
        and (macd_hist or 0) > 0
    ):
        return "buy", 0.55 if mode == "day" else 0.60
    if rsi_v is not None and rsi_v < 25:
        return "buy", 0.50
    if rsi_v is not None and rsi_v > 75:
        return "sell", 0.50
    return "hold", 0.30


def _build_prompt(mode: str, features: dict, rule_signal: str) -> str:
    mode_ko = "데이 트레이딩" if mode == "day" else "눌림 스윙"
    return f"""다음 종목에 대한 {mode_ko} 관점의 매매 제안을 작성해 줘.
룰 엔진 1차 판정: {rule_signal}

입력 특성:
- 종목: {features['name']} ({features['symbol']})
- 현재가: {features['price']} ({features['change_pct']:.2f}%)
- 주요 지표: {features['indicators']}
- 최근 수급(5일): {features['recent_flow']}

요청:
1. 위 특성을 근거로 매수/매도/관망 중 어떤 관점이 우세한지 2~4문장으로 설명
2. 진입 시 유의할 점 (손절·익절 자리, 체크해야 할 뉴스/수급)
3. 최종 메시지는 "제안" 이라는 표현을 포함
"""
