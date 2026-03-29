"""
증권사 리포트 API

  POST /api/v1/reports/fetch          — NAVER Finance에서 최신 리포트 수집 후 DB 저장
  GET  /api/v1/reports/recent         — 최신 리포트 N건 조회
  GET  /api/v1/reports/firms          — 등록된 증권사 목록
  GET  /api/v1/reports                — 필터(종목·증권사·기간) 조회
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc, distinct
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ...core.database import AsyncSessionLocal
from ...engine.report_fetcher import fetch_naver_reports
from ...models.ontology import SecuritiesReport

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


# ── 출력 스키마 ──────────────────────────────────────────

class ReportOut(BaseModel):
    id: int
    symbol: Optional[str]
    company_name: str
    securities_firm: str
    title: str
    target_price: Optional[float]
    report_date: str
    url: str
    source: str


def _to_out(r: SecuritiesReport) -> ReportOut:
    return ReportOut(
        id=r.id,
        symbol=r.symbol,
        company_name=r.company_name,
        securities_firm=r.securities_firm,
        title=r.title,
        target_price=r.target_price,
        report_date=r.report_date.isoformat() if r.report_date else "",
        url=r.url,
        source=r.source,
    )


# ── 엔드포인트 ────────────────────────────────────────────

@router.post("/fetch", response_model=dict)
async def fetch_reports(pages: int = Query(default=3, ge=1, le=10)):
    """NAVER Finance에서 최근 증권사 리포트를 수집해 DB에 저장한다.

    - pages: 수집 페이지 수 (기본 3 ≈ 최근 60건)
    - nid 기반 중복 제거 후 신규 건만 INSERT
    """
    raw = await fetch_naver_reports(pages=pages)
    if not raw:
        return {"fetched": 0, "saved": 0, "message": "수집된 리포트가 없습니다."}

    saved = 0
    async with AsyncSessionLocal() as session:
        for item in raw:
            nid = item.get("nid")
            # nid 있으면 중복 체크
            if nid:
                exists = (await session.execute(
                    select(SecuritiesReport.id).where(
                        SecuritiesReport.nid == nid,
                        SecuritiesReport.source == item.get("source", "naver"),
                    )
                )).scalar_one_or_none()
                if exists:
                    continue

            session.add(SecuritiesReport(**item))
            saved += 1

        await session.commit()

    logger.info("증권사 리포트 저장: %d/%d건", saved, len(raw))
    return {"fetched": len(raw), "saved": saved}


@router.get("/recent", response_model=list[ReportOut])
async def get_recent_reports(limit: int = Query(default=50, ge=1, le=200)):
    """최신 리포트를 날짜순으로 반환한다."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(SecuritiesReport)
            .order_by(desc(SecuritiesReport.report_date), desc(SecuritiesReport.id))
            .limit(limit)
        )).scalars().all()
    return [_to_out(r) for r in rows]


@router.get("/firms", response_model=list[str])
async def get_firms():
    """DB에 저장된 증권사 이름 목록(중복 제거, 가나다순)을 반환한다."""
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            select(distinct(SecuritiesReport.securities_firm))
            .order_by(SecuritiesReport.securities_firm)
        )).scalars().all()
    return [r for r in rows if r]


@router.get("", response_model=list[ReportOut])
async def get_reports(
    symbol: Optional[str] = None,
    firm: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """리포트 목록 조회.

    - symbol: 종목코드 (6자리)
    - firm: 증권사 이름 (부분 일치)
    - date_from / date_to: 발행일 범위
    """
    async with AsyncSessionLocal() as session:
        stmt = (
            select(SecuritiesReport)
            .order_by(desc(SecuritiesReport.report_date), desc(SecuritiesReport.id))
            .limit(limit)
        )
        if symbol:
            stmt = stmt.where(SecuritiesReport.symbol == symbol.strip())
        if firm:
            stmt = stmt.where(SecuritiesReport.securities_firm.ilike(f"%{firm.strip()}%"))
        if date_from:
            stmt = stmt.where(SecuritiesReport.report_date >= date_from)
        if date_to:
            stmt = stmt.where(SecuritiesReport.report_date <= date_to)

        rows = (await session.execute(stmt)).scalars().all()
    return [_to_out(r) for r in rows]
