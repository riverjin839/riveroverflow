"""HANRIVER 시황 대시보드 API.

상세 스펙: docs/HANRIVER_PHASE1_SPEC.md §4
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...hanriver import market_snapshot, news_feed

router = APIRouter(prefix="/hanriver", tags=["hanriver"])


class QuoteResponse(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float | None
    ts: datetime
    stale: bool


class NewsResponse(BaseModel):
    id: int
    source: str
    title: str
    url: str
    importance: str
    published_at: datetime


def _to_quote_response(q) -> QuoteResponse:
    return QuoteResponse(
        code=q.code,
        name=q.name,
        price=q.price,
        change_pct=q.change_pct,
        ts=q.ts,
        stale=q.stale,
    )


@router.get("/indices/kr", response_model=list[QuoteResponse])
async def get_kr_indices():
    return [_to_quote_response(q) for q in await market_snapshot.get_kr_indices()]


@router.get("/indices/global", response_model=list[QuoteResponse])
async def get_global_indices():
    return [_to_quote_response(q) for q in await market_snapshot.get_global_indices()]


@router.get("/fx", response_model=list[QuoteResponse])
async def get_fx():
    return [_to_quote_response(q) for q in await market_snapshot.get_fx_commodities()]


@router.get("/sentiment", response_model=list[QuoteResponse])
async def get_sentiment():
    return [_to_quote_response(q) for q in await market_snapshot.get_sentiment()]


@router.get("/heatmap/sectors", response_model=list[QuoteResponse])
async def get_sector_heatmap():
    return [_to_quote_response(q) for q in await market_snapshot.get_sector_heatmap()]


@router.get("/news", response_model=list[NewsResponse])
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    items = await news_feed.list_news(session, limit)
    return [
        NewsResponse(
            id=n.id,
            source=n.source,
            title=n.title,
            url=n.url,
            importance=n.importance,
            published_at=n.published_at,
        )
        for n in items
    ]
