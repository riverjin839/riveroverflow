"""오늘의 상한가 종목 수집 + 상승 이유 분석.

- 1차 수집: 네이버 금융 순위 페이지 (HTML 스크래핑)
  - 상한가: sise_upper.naver
  - 급등:   sise_rise.naver (≥10%)
  - 네이버는 장중 실시간 반영 — pykrx 대비 안정적
- 2차 수집 (fallback): pykrx 일일 등락률 (장 마감 후 T-1 데이터)
- 종목별 enrich: 네이버 뉴스 + DART 공시 + 네이버 모바일 실시간 거래대금
- Claude: 뉴스·공시를 요약해 '상승 이유'를 자연어로 작성
- 결과는 날짜 기준 in-memory 캐시 (장중에는 30초 간격으로 재생성 가능)
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from typing import TypedDict

from . import disclosures as disclosures_mod
from . import naver_ranking
from .ai import claude_client
from .naver import _HEADERS, NAVER_MOBILE_BASE, fetch_naver_stock

logger = logging.getLogger(__name__)

LIMIT_UP_THRESHOLD = 29.5   # 한국 주식 상한가 제한폭 +30%
SURGE_THRESHOLD = 10.0      # 강세 종목 기준

# (date_key, 'live'|'daily') → (ts, payload) 캐시
_cache: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_LIVE = 30.0   # 장중 실시간 응답 캐시
_CACHE_TTL_DAILY = 3600  # 과거 날짜 캐시


class LimitUpItem(TypedDict):
    symbol: str
    name: str
    market: str
    close: float
    change_pct: float
    volume: int
    trading_value: int
    category: str           # limit_up | surge
    reason: str | None
    news: list[dict]
    disclosures: list[dict]


def _is_today(target: date) -> bool:
    return target == date.today()


async def _fetch_stock_news(symbol: str, limit: int = 5) -> list[dict]:
    import httpx
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

    items = []
    if isinstance(data, dict):
        for group in data.get("items", []):
            if isinstance(group, dict) and "items" in group:
                items.extend(group["items"])
            elif isinstance(group, dict) and "title" in group:
                items.append(group)
    if not items and isinstance(data, list):
        items = data

    import re
    out: list[dict] = []
    for it in items[:limit]:
        title = it.get("title") or it.get("title_text") or ""
        if not title:
            continue
        title = re.sub(r"<[^>]+>", "", title)
        out.append({
            "title": title,
            "office": it.get("officeName") or it.get("office") or "",
            "url": it.get("linkUrl") or it.get("url") or "",
            "published": it.get("datetime") or it.get("pubDate") or "",
        })
    return out


async def _explain_reason(
    item: dict, news: list[dict], disclosures: list[dict],
) -> str:
    if not news and not disclosures:
        return "관련 뉴스·공시 수집 실패 또는 게시 없음. 수급·테마 급등 가능성."

    prompt = f"""다음 종목이 오늘 급등한 이유를 한국어 2~3문장으로 요약해 줘.
근거가 뉴스/공시에 명확히 있으면 인용, 없으면 추정 표현 사용.

종목: {item['name']} ({item['symbol']}) · {item['market']}
등락률: +{item['change_pct']}%
거래대금: {item['trading_value']:,}원

최근 뉴스:
{chr(10).join(f"- [{n['office']}] {n['title']}" for n in news) or "(없음)"}

최근 공시:
{chr(10).join(f"- {d['report_name']}" for d in disclosures) or "(없음)"}

출력: 2~3문장, 제안/추정 표현. JSON 이나 bullet 금지.
"""
    return await claude_client.complete(prompt, max_tokens=220, temperature=0.4)


async def _enrich(base: dict, enable_llm: bool) -> LimitUpItem:
    symbol = base["symbol"]
    news_task = _fetch_stock_news(symbol, limit=5)
    disc_task = disclosures_mod.list_symbol_disclosures(symbol, days=7)
    # 실시간 거래대금은 네이버 모바일 API 에서 별도 조회 (volume × close 로 추정도 가능하지만 장중 정확도 위함)
    live_task = fetch_naver_stock(symbol)

    news, disc, live = await asyncio.gather(news_task, disc_task, live_task)

    if live and live.get("volume") and live.get("price"):
        trading_value = int(live["volume"] * live["price"])
        close = live.get("price", base["close"])
        change_pct = live.get("change_pct", base["change_pct"])
        volume = live.get("volume", base["volume"])
    else:
        close = base["close"]
        change_pct = base["change_pct"]
        volume = base["volume"]
        trading_value = int(volume * close) if volume and close else 0

    category = "limit_up" if change_pct >= LIMIT_UP_THRESHOLD else "surge"

    reason: str | None = None
    if enable_llm and category == "limit_up":
        try:
            reason = await _explain_reason(
                {**base, "close": close, "change_pct": change_pct, "trading_value": trading_value},
                news, disc,
            )
        except Exception as e:
            logger.warning("reason explain failed symbol=%s: %s", symbol, e)
            reason = "분석 실패 — 원자료 확인 권장"

    return LimitUpItem(
        symbol=symbol,
        name=base["name"],
        market=base.get("market", ""),
        close=close,
        change_pct=change_pct,
        volume=volume,
        trading_value=trading_value,
        category=category,
        reason=reason,
        news=news,
        disclosures=[
            {"report_name": d["report_name"], "url": d["url"], "rcept_dt": d["rcept_dt"]}
            for d in disc
        ],
    )


def _collect_pykrx_fallback(target: date) -> list[dict]:
    """pykrx fallback — 네이버 실패 시에만 사용."""
    try:
        from pykrx import stock as krx
        day = target.strftime("%Y%m%d")
        df = krx.get_market_price_change_by_ticker(day, day, market="ALL")
    except Exception as e:
        logger.warning("pykrx fallback failed: %s", e)
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
                "market": "KRX",
                "close": float(row.get("종가", 0)),
                "change_pct": round(change_pct, 2),
                "volume": int(row.get("거래량", 0)),
            })
        except (KeyError, ValueError, TypeError):
            continue
    return rows


async def get_limit_up_report(
    target: date | None = None,
    force: bool = False,
    enable_llm: bool = True,
) -> dict:
    if target is None:
        target = date.today()

    key = target.isoformat()
    ttl = _CACHE_TTL_LIVE if _is_today(target) else _CACHE_TTL_DAILY
    now = time.time()
    if not force:
        cached = _cache.get(key)
        if cached and now - cached[0] < ttl:
            return cached[1]

    # 1차: 네이버 순위 (오늘 기준 항상 최신)
    source = "naver"
    if _is_today(target):
        upper_rows, rise_rows = await asyncio.gather(
            naver_ranking.fetch_upper_limit(),
            naver_ranking.fetch_top_risers(min_change_pct=SURGE_THRESHOLD),
        )
        # 상한가를 먼저, 급등에서 중복 제거
        seen = {r["symbol"] for r in upper_rows}
        combined: list[dict] = list(upper_rows)
        for r in rise_rows:
            if r["symbol"] not in seen:
                combined.append(r)
                seen.add(r["symbol"])
    else:
        # 과거 날짜는 pykrx 사용 (네이버 순위 페이지는 당일만 제공)
        combined = await asyncio.get_event_loop().run_in_executor(
            None, _collect_pykrx_fallback, target
        )
        source = "pykrx"

    if not combined and _is_today(target):
        # 네이버가 비어 있으면 pykrx 로 재시도
        combined = await asyncio.get_event_loop().run_in_executor(
            None, _collect_pykrx_fallback, target
        )
        source = "pykrx-fallback"

    combined.sort(key=lambda r: r.get("change_pct", 0), reverse=True)
    top = combined[:40]
    enriched = list(await asyncio.gather(*(_enrich(it, enable_llm) for it in top)))

    payload = {
        "date": target.isoformat(),
        "source": source,
        "limit_up_count": sum(1 for i in enriched if i["category"] == "limit_up"),
        "surge_count": sum(1 for i in enriched if i["category"] == "surge"),
        "total_trading_value": sum(i["trading_value"] for i in enriched),
        "items": enriched,
        "generated_at": datetime.utcnow().isoformat(),
    }
    _cache[key] = (time.time(), payload)
    return payload
