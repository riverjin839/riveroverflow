"""Daily/Weekly/Stock 리포트 생성.

시장 스냅샷과 뉴스 요약을 담아 Claude 에게 전달.
프롬프트는 고정 템플릿 → prompt cache 활용.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import market_snapshot
from ...models.hanriver import NewsItem
from . import claude_client


async def build(
    report_type: str,
    subject: str,
    broker=None,
    session: AsyncSession | None = None,
) -> str:
    if report_type == "daily":
        return await _daily(session)
    if report_type == "weekly":
        return await _weekly(session)
    if report_type == "stock":
        return await _stock(broker, subject)
    return "지원하지 않는 리포트 타입"


async def _market_summary_text() -> str:
    kr = await market_snapshot.get_kr_indices()
    glo = await market_snapshot.get_global_indices()
    fx = await market_snapshot.get_fx_commodities()
    sent = await market_snapshot.get_sentiment()
    lines = ["[국내]"] + [f"- {q.name}: {q.price} ({q.change_pct}%)" for q in kr]
    lines.append("[해외]")
    lines += [f"- {q.name}: {q.price} ({q.change_pct}%)" for q in glo]
    lines.append("[환율/원자재]")
    lines += [f"- {q.name}: {q.price} ({q.change_pct}%)" for q in fx]
    lines.append("[심리]")
    lines += [f"- {q.name}: {q.price}" for q in sent]
    return "\n".join(lines)


async def _recent_news_text(session: AsyncSession | None, limit: int = 15) -> str:
    if session is None:
        return ""
    rows = (await session.execute(
        select(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit)
    )).scalars().all()
    return "\n".join(f"- [{n.source}] {n.title}" for n in rows)


async def _daily(session) -> str:
    market = await _market_summary_text()
    news = await _recent_news_text(session)
    prompt = f"""오늘 한국 주식 시장 일일 리포트를 마크다운으로 작성해 줘.

# 시장 스냅샷
{market}

# 최근 뉴스
{news}

요청 섹션:
1. **시장 요약** (3~4문장)
2. **섹터 동향**
3. **수급 포인트**
4. **내일 관전 포인트**
5. **관심 제안 종목 (있으면)**

각 섹션은 2~4개 bullet 로 간결하게.
"""
    return await claude_client.complete(prompt, max_tokens=1600, temperature=0.5)


async def _weekly(session) -> str:
    market = await _market_summary_text()
    news = await _recent_news_text(session, limit=30)
    prompt = f"""이번 주 한국 주식 시장 주간 리뷰를 마크다운으로 작성해 줘.

{market}

주요 뉴스:
{news}

요청 섹션:
1. **주간 시장 개요**
2. **주도 섹터 / 소외 섹터**
3. **매크로 이슈 (금리·환율·원자재)**
4. **다음 주 핵심 이벤트 캘린더 (예상)**
5. **트레이딩 관점 제안**
"""
    return await claude_client.complete(prompt, max_tokens=2000, temperature=0.5)


async def _stock(broker, symbol: str) -> str:
    if broker is None:
        return f"(브로커 미초기화) {symbol} 리포트를 생성할 수 없습니다."
    market = await broker.get_market_price(symbol)
    prompt = f"""종목 심층 리포트를 마크다운으로 작성해 줘.

종목: {market.name} ({symbol})
현재가: {market.price} ({market.change_pct}%)

요청 섹션:
1. **개요** — 업황과 포지션
2. **차트 해석** — 추세·지지/저항
3. **수급 관찰**
4. **뉴스·공시 체크리스트**
5. **데이/스윙 관점 제안** — 각각 매수 자리 / 손절 / 목표가
6. **리스크 요인**
"""
    return await claude_client.complete(prompt, max_tokens=1800, temperature=0.5)
