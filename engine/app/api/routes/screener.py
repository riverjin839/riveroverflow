import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

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
