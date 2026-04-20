"""HANRIVER 뉴스 피드 서비스 (Week 1 스텁).

Week 3에서 한경 RSS + DART OpenAPI 연동 예정.
Week 1은 DB에서 최근 레코드를 읽되, 비어 있으면 seed 샘플을 반환한다.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.hanriver import NewsItem


SEED_NEWS: list[dict] = [
    {
        "source": "hankyung",
        "title": "삼성전자, HBM 공급 확대…엔비디아 의존도 낮추기 박차",
        "url": "https://example.com/news/seed-1",
        "importance": "high",
        "offset_minutes": 5,
    },
    {
        "source": "dart",
        "title": "SK하이닉스 / 주요사항보고서 (자기주식 취득)",
        "url": "https://example.com/dart/seed-2",
        "importance": "medium",
        "offset_minutes": 12,
    },
    {
        "source": "hankyung",
        "title": "연준, 9월 금리 동결 가능성 80%…달러 약세 전환",
        "url": "https://example.com/news/seed-3",
        "importance": "medium",
        "offset_minutes": 22,
    },
    {
        "source": "dart",
        "title": "포스코홀딩스 / 타법인 주식 취득결정 공시",
        "url": "https://example.com/dart/seed-4",
        "importance": "medium",
        "offset_minutes": 31,
    },
    {
        "source": "hankyung",
        "title": "코스피 외국인 3거래일 연속 순매수…반도체·금융 선호",
        "url": "https://example.com/news/seed-5",
        "importance": "low",
        "offset_minutes": 44,
    },
]


async def list_news(session: AsyncSession, limit: int = 20) -> list[NewsItem]:
    stmt = select(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    if rows:
        return list(rows)
    return _seed(limit)


def _seed(limit: int) -> list[NewsItem]:
    now = datetime.now(timezone.utc)
    items: list[NewsItem] = []
    for i, s in enumerate(SEED_NEWS[:limit]):
        items.append(
            NewsItem(
                id=-(i + 1),  # 음수 id로 저장 안 된 seed 임을 표시
                source=s["source"],
                title=s["title"],
                url=s["url"],
                importance=s["importance"],
                published_at=now - timedelta(minutes=s["offset_minutes"]),
                raw=None,
            )
        )
    return items
