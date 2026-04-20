"""뉴스 importance 자동 스코어링.

Claude 에게 배치 단위로 뉴스 제목을 주고 상/중/하 라벨을 받는다.
비용을 위해 제목만 먼저 스코어링 — 상위만 본문 요약·entity 태깅.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.hanriver import NewsItem, NewsScore
from . import claude_client

logger = logging.getLogger(__name__)


async def score_recent(session: AsyncSession, limit: int = 20) -> int:
    """최근 뉴스 중 아직 스코어링 안 된 것만 처리."""
    q = (
        select(NewsItem)
        .outerjoin(NewsScore, NewsScore.news_id == NewsItem.id)
        .where(NewsScore.news_id.is_(None))
        .order_by(NewsItem.published_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(q)).scalars().all()
    if not rows:
        return 0

    titles = [{"id": r.id, "title": r.title, "source": r.source} for r in rows]
    prompt = f"""다음 한국 주식 뉴스 제목들의 시장 영향도를 평가해 줘.
각 항목에 대해 JSON 배열로 응답:
[{{"id": 1, "importance": "high|medium|low", "symbols": "005930,000660"}}]

symbols 는 제목에서 명확히 언급된 종목 코드. 없으면 "".

입력:
{json.dumps(titles, ensure_ascii=False)}
"""
    raw = await claude_client.complete(prompt, max_tokens=1200, temperature=0.1)

    try:
        start = raw.find("[")
        end = raw.rfind("]")
        parsed = json.loads(raw[start : end + 1]) if start >= 0 else []
    except (ValueError, json.JSONDecodeError):
        logger.warning("뉴스 스코어링 파싱 실패")
        parsed = []

    counter = 0
    fallback = {r.id: r for r in rows}
    for item in parsed:
        nid = int(item.get("id", 0))
        if nid in fallback:
            score = NewsScore(
                news_id=nid,
                importance=item.get("importance", "unknown"),
                symbols=item.get("symbols") or None,
            )
            session.add(score)
            fallback[nid].importance = item.get("importance", "unknown")
            counter += 1

    # 나머지는 unknown 으로 마킹해 재처리 방지
    for r in rows:
        if r.id not in {int(i.get("id", 0)) for i in parsed}:
            session.add(NewsScore(news_id=r.id, importance="unknown"))
    return counter
