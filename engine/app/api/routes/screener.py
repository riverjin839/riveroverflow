import asyncio
import logging
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from ...engine.condition_engine import ConditionSpec, evaluate_conditions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screener", tags=["screener"])

DEFAULT_SYMBOLS = [
    "005930", "000660", "035420", "005380", "051910",
    "006400", "035720", "000270", "028260", "096770",
    "017670", "030200", "003550", "066570", "032830",
    "018260", "009150", "010130", "011170", "004020",
]


class NewHighResult(BaseModel):
    symbol: str
    name: str
    current_price: float
    high_52w: float
    high_pct: float
    volume: int
    is_new_high: bool


async def _scan_symbol(
    broker,
    symbol: str,
    period_days: int,
    threshold_pct: float,
) -> Optional[NewHighResult]:
    try:
        ohlcv_data, market = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: broker._get_ohlcv_sync(symbol, "D", period_days)
            ) if hasattr(broker, "_get_ohlcv_sync") else broker.get_ohlcv(symbol, "D", period_days),
            broker.get_market_price(symbol),
        )
        if not ohlcv_data:
            return None

        high_52w = max(float(c["high"]) for c in ohlcv_data)
        current_price = float(market.price)
        high_pct = round(current_price / high_52w * 100, 2) if high_52w > 0 else 0.0

        if high_pct < threshold_pct:
            return None

        return NewHighResult(
            symbol=symbol,
            name=market.name,
            current_price=current_price,
            high_52w=high_52w,
            high_pct=high_pct,
            volume=int(market.volume),
            is_new_high=(current_price >= high_52w),
        )
    except Exception as e:
        logger.warning("신고가 스캔 실패 symbol=%s: %s", symbol, e)
        return None


class ConditionScanRequest(BaseModel):
    symbols: Optional[list[str]] = None   # None → DEFAULT_SYMBOLS
    conditions: list[ConditionSpec]
    period_days: int = 30                 # OHLCV 조회 기간 (충분한 여유분 포함)


class ConditionScanResult(BaseModel):
    symbol: str
    name: str
    current_price: float
    volume: int
    matched_conditions: list[str]   # 한글 설명


def _required_fetch_count(conditions: list[ConditionSpec], period_days: int) -> int:
    """조건 타입에 따라 필요한 최소 OHLCV 행 수를 계산한다."""
    extra = period_days + 20
    for c in conditions:
        if c.type == "monthly_cumulative_trading_value":
            extra = max(extra, c.months * 22 + 10)
        elif c.type == "price_above_ma":
            extra = max(extra, c.ma_period + 10)
    return max(extra, 40)


async def _condition_scan_symbol(
    broker,
    symbol: str,
    conditions: list[ConditionSpec],
    period_days: int,
) -> Optional[ConditionScanResult]:
    try:
        fetch_count = _required_fetch_count(conditions, period_days)
        ohlcv_data, market = await asyncio.gather(
            broker.get_ohlcv(symbol, "D", fetch_count),
            broker.get_market_price(symbol),
        )
        if not ohlcv_data or len(ohlcv_data) < 2:
            return None

        df = pd.DataFrame(ohlcv_data)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["open", "high", "low", "close", "volume"])

        if not evaluate_conditions(df, conditions, symbol=symbol):
            return None

        return ConditionScanResult(
            symbol=symbol,
            name=market.name,
            current_price=float(market.price),
            volume=int(market.volume),
            matched_conditions=[c.label() for c in conditions],
        )
    except Exception as e:
        logger.warning("조건 스캔 실패 symbol=%s: %s", symbol, e)
        return None


@router.post("/conditions", response_model=list[ConditionScanResult])
async def scan_conditions(body: ConditionScanRequest, request: Request):
    """커스텀 조건 스크리닝.

    - conditions: 평가할 조건 목록 (AND 논리)
    - symbols: 종목코드 목록 (없으면 KOSPI 기본 20종목)
    - period_days: OHLCV 조회 기간 (기본 30일)
    """
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="브로커가 초기화되지 않았습니다.")

    if not body.conditions:
        raise HTTPException(status_code=422, detail="최소 1개 이상의 조건을 입력해야 합니다.")

    if body.period_days < 5 or body.period_days > 504:
        raise HTTPException(status_code=422, detail="period_days는 5~504 사이여야 합니다.")

    symbol_list = body.symbols if body.symbols else DEFAULT_SYMBOLS

    invalid = [s for s in symbol_list if not s.isdigit() or len(s) != 6]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"종목코드는 6자리 숫자여야 합니다. 잘못된 입력: {', '.join(invalid)} (예: 005930)",
        )

    tasks = [
        _condition_scan_symbol(broker, sym, body.conditions, body.period_days)
        for sym in symbol_list
    ]
    results = await asyncio.gather(*tasks)

    hits = [r for r in results if r is not None]
    hits.sort(key=lambda r: r.current_price, reverse=True)
    logger.info("조건 스크리닝 완료: %d/%d 종목 매칭", len(hits), len(symbol_list))
    return hits


@router.get("/new-highs", response_model=list[NewHighResult])
async def get_new_highs(
    request: Request,
    symbols: Optional[str] = None,
    period_days: int = 252,
    threshold_pct: float = 97.0,
):
    """52주 신고가 종목 스크리너.

    - symbols: 쉼표 구분 종목코드 (없으면 KOSPI 주요 20종목)
    - period_days: 기간 (기본 252거래일 = 52주)
    - threshold_pct: 신고가 대비 최소 비율 % (기본 97%)
    """
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="브로커가 초기화되지 않았습니다.")

    if period_days < 1 or period_days > 504:
        raise HTTPException(status_code=422, detail="period_days는 1~504 사이여야 합니다.")
    if threshold_pct < 50 or threshold_pct > 100:
        raise HTTPException(status_code=422, detail="threshold_pct는 50~100 사이여야 합니다.")

    symbol_list = (
        [s.strip() for s in symbols.split(",") if s.strip()]
        if symbols
        else DEFAULT_SYMBOLS
    )

    # 6자리 숫자 종목코드만 허용 (종목명 입력 방지)
    invalid = [s for s in symbol_list if not s.isdigit() or len(s) != 6]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"종목코드는 6자리 숫자여야 합니다. 잘못된 입력: {', '.join(invalid)} (예: 005930)",
        )

    tasks = [
        _scan_symbol(broker, sym, period_days, threshold_pct)
        for sym in symbol_list
    ]
    results = await asyncio.gather(*tasks)

    hits = [r for r in results if r is not None]
    hits.sort(key=lambda r: r.high_pct, reverse=True)
    return hits
