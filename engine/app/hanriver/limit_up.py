"""오늘의 상한가 종목 수집 + 상승 이유 분석.

- pykrx: 전체 종목 당일 등락률 + 거래대금 → 상한가(≥29.5%) / 급등(≥10%) 필터
- 네이버 모바일 API: 종목별 최근 뉴스
- Claude: 뉴스·공시를 요약해 '상승 이유'를 자연어로 작성
- 결과는 날짜 기준 in-memory 캐시 (장 마감 후 1회 수집)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, TypedDict

import httpx

from ..core.config import settings
from . import disclosures as disclosures_mod
from .ai import claude_client
from .naver import _HEADERS, NAVER_MOBILE_BASE

logger = logging.getLogger(__name__)

LIMIT_UP_THRESHOLD = 29.5   # 한국 주식 상한가 제한폭 +30%
SURGE_THRESHOLD = 10.0      # 강세 종목 기준

# date(YYYYMMDD) → payload 캐시
_cache: dict[str, dict] = {}


class LimitUpItem(TypedDict):
    symbol: str
    name: str
    close: float
    change_pct: float
    volume: int
    trading_value: int
    category: str           # limit_up | surge
    reason: str | None
    news: list[dict]
    disclosures: list[dict]


def _last_business_day() -> date:
    """오늘이 주말이면 직전 금요일로."""
    today = date.today()
    while today.weekday() >= 5:
        today -= timedelta(days=1)
    return today


def _collect_price_change_sync(target: date) -> list[dict]:
    from pykrx import stock as krx

    day = target.strftime("%Y%m%d")
    # 전일 대비 변동률 — 단일 날짜 조회는 from=to 로
    try:
        df = krx.get_market_price_change_by_ticker(day, day, market="ALL")
    except Exception as e:
        logger.warning("pykrx price change failed date=%s: %s", day, e)
        return []
    if df is None or df.empty:
        return []

    rows: list[dict] = []
    for symbol, row in df.iterrows():
        try:
            change_pct = float(row.get("등락률", 0))
            if change_pct < SURGE_THRESHOLD:
                continue
            rows.append({
                "symbol": symbol,
                "name": str(row.get("종목명", symbol)),
                "close": float(row.get("종가", 0)),
                "change_pct": round(change_pct, 2),
                "volume": int(row.get("거래량", 0)),
                "trading_value": int(row.get("거래대금", 0)),
            })
        except (KeyError, ValueError, TypeError):
            continue
    rows.sort(key=lambda r: r["change_pct"], reverse=True)
    return rows


async def _fetch_stock_news(symbol: str, limit: int = 5) -> list[dict]:
    """네이버 종목 뉴스.
    https://m.stock.naver.com/api/news/stock/{symbol}/all
    """
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_HEADERS) as client:
            r = await client.get(
                f"{NAVER_MOBILE_BASE}/news/stock/{symbol}",
                params={"pageSize": limit, "page": 1},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.debug("naver news fetch failed symbol=%s: %s", symbol, e)
        return []

    # Naver news API 응답은 {"items":[{"items":[...]}]} 또는 {"items":[...]} 형태
    items = []
    if isinstance(data, dict):
        for group in data.get("items", []):
            if isinstance(group, dict) and "items" in group:
                items.extend(group["items"])
            elif isinstance(group, dict) and "title" in group:
                items.append(group)
    if not items and isinstance(data, list):
        items = data

    out: list[dict] = []
    for it in items[:limit]:
        title = it.get("title") or it.get("title_text") or ""
        office = it.get("officeName") or it.get("office") or ""
        url = it.get("linkUrl") or it.get("url") or ""
        published = it.get("datetime") or it.get("pubDate") or ""
        if not title:
            continue
        # HTML 태그 제거
        import re
        title = re.sub(r"<[^>]+>", "", title)
        out.append({
            "title": title,
            "office": office,
            "url": url,
            "published": published,
        })
    return out


async def _explain_reason(
    item: dict,
    news: list[dict],
    disclosures: list[dict],
) -> str:
    if not news and not disclosures:
        return "관련 뉴스·공시 수집 실패 또는 게시 없음. 수급·테마 급등 가능성."

    prompt = f"""다음 종목이 오늘 급등한 이유를 한국어 2~3문장으로 요약해 줘.
근거가 뉴스/공시에 명확히 있으면 인용, 없으면 추정 표현 사용.

종목: {item['name']} ({item['symbol']})
등락률: +{item['change_pct']}%
거래대금: {item['trading_value']:,}원

최근 뉴스:
{chr(10).join(f"- [{n['office']}] {n['title']}" for n in news) or "(없음)"}

최근 공시:
{chr(10).join(f"- {d['report_name']}" for d in disclosures) or "(없음)"}

출력 형식: 줄바꿈 없는 2~3문장. 제안/추정 표현 적극 사용.
"""
    return await claude_client.complete(prompt, max_tokens=220, temperature=0.4)


async def _enrich(item: dict) -> LimitUpItem:
    symbol = item["symbol"]
    news_task = _fetch_stock_news(symbol, limit=5)
    disc_task = disclosures_mod.list_symbol_disclosures(symbol, days=7)
    news, disc = await asyncio.gather(news_task, disc_task)

    # Claude 비용 관리: 상한가만 LLM 분석, 급등은 뉴스 제목만 노출
    category = "limit_up" if item["change_pct"] >= LIMIT_UP_THRESHOLD else "surge"
    reason = None
    if category == "limit_up":
        try:
            reason = await _explain_reason(item, news, disc)
        except Exception as e:
            logger.warning("reason explain failed symbol=%s: %s", symbol, e)
            reason = "분석 실패 — 원자료 확인 권장"

    return LimitUpItem(
        symbol=symbol,
        name=item["name"],
        close=item["close"],
        change_pct=item["change_pct"],
        volume=item["volume"],
        trading_value=item["trading_value"],
        category=category,
        reason=reason,
        news=news,
        disclosures=[
            {"report_name": d["report_name"], "url": d["url"], "rcept_dt": d["rcept_dt"]}
            for d in disc
        ],
    )


async def get_limit_up_report(target: date | None = None, force: bool = False) -> dict:
    if target is None:
        target = _last_business_day()
    key = target.strftime("%Y%m%d")

    if not force and key in _cache:
        return _cache[key]

    raw = await asyncio.get_event_loop().run_in_executor(
        None, _collect_price_change_sync, target
    )
    # 상한가·급등 후보 최대 40개까지만 enrich (과도한 LLM 호출 방지)
    top = raw[:40]
    enriched = await asyncio.gather(*(_enrich(it) for it in top))

    payload = {
        "date": target.isoformat(),
        "limit_up_count": sum(1 for i in enriched if i["category"] == "limit_up"),
        "surge_count": sum(1 for i in enriched if i["category"] == "surge"),
        "total_trading_value": sum(i["trading_value"] for i in enriched),
        "items": list(enriched),
        "generated_at": datetime.utcnow().isoformat(),
    }
    _cache[key] = payload
    return payload
