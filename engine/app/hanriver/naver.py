"""네이버 금융 실시간 시세 fetcher.

pykrx 는 일봉 종가(T-1) 만 제공하므로 장중 실시간 값이 맞지 않는다.
네이버 모바일 API 는 인증 없이 현재가를 돌려주므로 KR 지수는 네이버에서,
사용 가능한 국내 종목 가격도 네이버에서 가져온다.

엔드포인트 예:
- https://m.stock.naver.com/api/index/KOSPI/basic
- https://m.stock.naver.com/api/stock/005930/basic

상업적 사용 금지 — 개인 연구 목적에 한정.
"""
from __future__ import annotations

import logging
from typing import TypedDict

import httpx

logger = logging.getLogger(__name__)

NAVER_MOBILE_BASE = "https://m.stock.naver.com/api"
NAVER_SEARCH_BASE = "https://ac.stock.naver.com/ac"
# 네이버 지수 코드: KOSPI, KOSDAQ, KPI200
NAVER_INDEX_CODES: dict[str, str] = {
    "KOSPI": "KOSPI",
    "KOSDAQ": "KOSDAQ",
    "KOSPI200": "KPI200",
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Referer": "https://m.stock.naver.com/",
}


class IndexQuote(TypedDict):
    price: float
    change_pct: float


def _parse_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).replace(",", ""))


async def fetch_naver_index(code: str) -> IndexQuote | None:
    naver_code = NAVER_INDEX_CODES.get(code)
    if not naver_code:
        return None
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_HEADERS) as client:
            r = await client.get(f"{NAVER_MOBILE_BASE}/index/{naver_code}/basic")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("naver index fetch failed code=%s: %s", code, e)
        return None

    try:
        return IndexQuote(
            price=_parse_float(data.get("closePrice")),
            change_pct=_parse_float(data.get("fluctuationsRatio")),
        )
    except (KeyError, ValueError) as e:
        logger.warning("naver index parse failed: %s", e)
        return None


async def fetch_naver_indices(codes: list[str]) -> dict[str, tuple[float, float]]:
    """여러 지수를 병렬 조회."""
    import asyncio

    tasks = {c: fetch_naver_index(c) for c in codes}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out: dict[str, tuple[float, float]] = {}
    for code, r in zip(tasks.keys(), results):
        if isinstance(r, dict):
            out[code] = (r["price"], r["change_pct"])
    return out


async def fetch_naver_stock(symbol: str) -> dict | None:
    """종목 실시간 시세 (code 는 6자리 한국 코드)."""
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_HEADERS) as client:
            r = await client.get(f"{NAVER_MOBILE_BASE}/stock/{symbol}/basic")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("naver stock fetch failed symbol=%s: %s", symbol, e)
        return None

    try:
        return {
            "symbol": symbol,
            "name": data.get("stockName") or data.get("stockNameEng") or symbol,
            "price": _parse_float(data.get("closePrice")),
            "change_pct": _parse_float(data.get("fluctuationsRatio")),
            "change": _parse_float(data.get("compareToPreviousClosePrice")),
            "volume": int(_parse_float(data.get("accumulatedTradingVolume"))),
        }
    except (KeyError, ValueError):
        return None


async def search_stock(query: str, limit: int = 10) -> list[dict]:
    """네이버 종목 자동완성. 한글·영문·코드 모두 지원.

    응답 구조가 지속적으로 변하므로 items 를 평탄화하며 dict 만 수집한다.
    """
    query = query.strip()
    if not query:
        return []
    try:
        async with httpx.AsyncClient(timeout=4.0, headers=_HEADERS) as client:
            r = await client.get(
                NAVER_SEARCH_BASE,
                params={"q": query, "target": "stock,index", "_callback": ""},
            )
            r.raise_for_status()
            text = r.text
    except Exception as e:
        logger.warning("naver search fetch failed: %s", e)
        return []

    import json
    import re
    stripped = re.sub(r"^\w*\(", "", text).rstrip(");").rstrip(")").strip()
    try:
        data = json.loads(stripped)
    except (ValueError, json.JSONDecodeError):
        logger.debug("naver search JSON parse failed")
        return []

    # items 은 list[dict] 일 수도 있고 list[list[dict]] 일 수도 있다 — 평탄화
    items = data.get("items", []) if isinstance(data, dict) else []
    flat: list[dict] = []
    for node in items:
        if isinstance(node, list):
            flat.extend(n for n in node if isinstance(n, dict))
        elif isinstance(node, dict):
            flat.append(node)

    out: list[dict] = []
    for it in flat:
        code = it.get("cd") or it.get("code")
        name = it.get("nm") or it.get("name")
        if not code or not name:
            continue
        # <strong> 하이라이트 태그 제거
        name = re.sub(r"<[^>]+>", "", str(name))
        market = it.get("mksNm") or it.get("typeCode") or ""
        out.append({"symbol": str(code), "name": name, "market": str(market)})
        if len(out) >= limit:
            break
    return out
