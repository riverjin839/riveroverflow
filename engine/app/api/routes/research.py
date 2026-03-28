"""
오토리서치 API — 수동 스캔 실행 + 결과 조회.
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import AsyncSessionLocal
from ...models.ontology import ResearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["research"])


# ── 스키마 ──────────────────────────────────────────────

class ScanRequest(BaseModel):
    symbols: Optional[list[str]] = None   # None → DEFAULT_SYMBOLS
    period_days: int = 60


class ResearchResultOut(BaseModel):
    symbol: str
    name: str
    research_date: str
    period_days: int
    rsi: Optional[float]
    ma5: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    macd_val: Optional[float]
    macd_signal_val: Optional[float]
    high_period: Optional[float]
    high_pct: Optional[float]
    volume_ratio: Optional[float]
    signals: dict
    composite_score: float
    summary: str


def _to_out(r: ResearchResult) -> ResearchResultOut:
    return ResearchResultOut(
        symbol=r.symbol,
        name=r.name,
        research_date=r.research_date.isoformat() if r.research_date else "",
        period_days=r.period_days,
        rsi=r.rsi,
        ma5=r.ma5,
        ma20=r.ma20,
        ma60=r.ma60,
        macd_val=r.macd_val,
        macd_signal_val=r.macd_signal_val,
        high_period=r.high_period,
        high_pct=r.high_pct,
        volume_ratio=r.volume_ratio,
        signals=r.signals or {},
        composite_score=r.composite_score or 0.0,
        summary=r.summary or "",
    )


# ── 엔드포인트 ─────────────────────────────────────────

@router.post("/scan", response_model=list[ResearchResultOut])
async def run_scan(body: ScanRequest, request: Request):
    """수동 오토리서치 실행. 종목 입력 없으면 KOSPI 기본 20종목을 사용한다."""
    researcher = getattr(request.app.state, "researcher", None)
    if researcher is None:
        raise HTTPException(status_code=503, detail="Researcher가 초기화되지 않았습니다.")

    if body.period_days < 20 or body.period_days > 504:
        raise HTTPException(status_code=422, detail="period_days는 20~504 사이여야 합니다.")

    results = await researcher.run(symbols=body.symbols, period_days=body.period_days)
    return [ResearchResultOut(**r) for r in results]


@router.get("/results/latest", response_model=list[ResearchResultOut])
async def get_latest_results(
    min_score: float = 0.0,
    signal: Optional[str] = None,
):
    """가장 최근 리서치 날짜의 결과를 반환한다."""
    async with AsyncSessionLocal() as session:
        # 가장 최근 날짜 조회
        latest_date_row = (
            await session.execute(
                select(ResearchResult.research_date)
                .order_by(desc(ResearchResult.research_date))
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest_date_row is None:
            return []

        stmt = (
            select(ResearchResult)
            .where(
                ResearchResult.research_date == latest_date_row,
                ResearchResult.composite_score >= min_score,
            )
            .order_by(desc(ResearchResult.composite_score))
        )
        rows = (await session.execute(stmt)).scalars().all()

    # 시그널 필터 (JSONB 내부 값으로 Python에서 필터)
    if signal:
        rows = [r for r in rows if _has_signal(r.signals or {}, signal)]

    return [_to_out(r) for r in rows]


@router.get("/results", response_model=list[ResearchResultOut])
async def get_results(
    symbol: Optional[str] = None,
    research_date: Optional[date] = None,
    min_score: float = 0.0,
    limit: int = 100,
):
    """리서치 결과 조회. symbol·날짜·최소 스코어 필터 가능."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ResearchResult)
            .where(ResearchResult.composite_score >= min_score)
            .order_by(desc(ResearchResult.research_date), desc(ResearchResult.composite_score))
            .limit(limit)
        )
        if symbol:
            stmt = stmt.where(ResearchResult.symbol == symbol)
        if research_date:
            stmt = stmt.where(ResearchResult.research_date == research_date)

        rows = (await session.execute(stmt)).scalars().all()

    return [_to_out(r) for r in rows]


def _has_signal(signals: dict, signal_filter: str) -> bool:
    """시그널 키워드가 signals dict 값 어딘가에 포함되는지 확인."""
    for v in signals.values():
        if isinstance(v, str) and signal_filter.lower() in v.lower():
            return True
    return False
