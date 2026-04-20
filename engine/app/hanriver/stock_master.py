"""종목 마스터 — pykrx 로 KOSPI·KOSDAQ 전종목을 메모리에 적재하고
한글명·영문·코드 부분 일치로 검색한다.

- 하루 1회 갱신 (TTL 24h)
- pykrx 호출 실패 시에도 서비스가 살아 있도록 빈 master 를 반환
- 검색은 exact > prefix > substring 순으로 스코어링
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import TypedDict

logger = logging.getLogger(__name__)

_TTL = 24 * 3600
_master: list["StockEntry"] | None = None
_loaded_at: float = 0.0
_lock = asyncio.Lock()


class StockEntry(TypedDict):
    symbol: str
    name: str
    market: str


def _load_sync() -> list[StockEntry]:
    """KOSPI+KOSDAQ 전종목을 벌크로 적재.

    per-ticker 호출은 2500+회 → 수분 소요. 네이버 시가총액 페이지를
    페이지네이션으로 스크랩하면 한 페이지당 50종목을 단일 HTTP 호출로
    가져와 ~30초 내에 완료된다.
    """
    import re
    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Referer": "https://finance.naver.com/",
    }

    out: list[StockEntry] = []

    def scrape(sosok: str, market: str) -> None:
        base = "https://finance.naver.com/sise/sise_market_sum.naver"
        for page in range(1, 50):  # 넉넉히 49페이지 (종목 수 증가 대비)
            try:
                r = requests.get(
                    base, params={"sosok": sosok, "page": page},
                    headers=headers, timeout=6,
                )
                r.raise_for_status()
                html = r.content.decode("euc-kr", errors="replace")
            except Exception as e:
                logger.warning("market_sum fetch failed sosok=%s page=%d: %s", sosok, page, e)
                break
            soup = BeautifulSoup(html, "html.parser")
            table = soup.select_one("table.type_2")
            if not table:
                break
            page_count = 0
            for a in table.select("a.tltle"):
                href = a.get("href", "")
                m = re.search(r"code=(\d{6})", href)
                if not m:
                    continue
                symbol = m.group(1)
                name = a.get_text(strip=True)
                if not name:
                    continue
                out.append(StockEntry(symbol=symbol, name=name, market=market))
                page_count += 1
            if page_count == 0:
                # 빈 페이지 도달 = 끝
                break

    # KOSPI(sosok=0), KOSDAQ(sosok=1)
    scrape("0", "KOSPI")
    scrape("1", "KOSDAQ")

    # 중복 제거 (간혹 교차 노출)
    seen: set[str] = set()
    dedup: list[StockEntry] = []
    for e in out:
        if e["symbol"] in seen:
            continue
        seen.add(e["symbol"])
        dedup.append(e)

    if not dedup:
        # 네이버 스크래핑 실패 시 pykrx 로 최소한의 코드 목록이라도 확보
        try:
            from pykrx import stock as krx
            for market in ("KOSPI", "KOSDAQ"):
                for t in krx.get_market_ticker_list(market=market):
                    dedup.append(StockEntry(symbol=t, name=t, market=market))
        except Exception as e:
            logger.warning("pykrx fallback failed: %s", e)

    logger.info("stock master loaded: %d entries", len(dedup))
    return dedup


async def ensure_loaded(force: bool = False) -> list[StockEntry]:
    global _master, _loaded_at
    now = time.time()
    if not force and _master is not None and (now - _loaded_at) < _TTL:
        return _master
    async with _lock:
        if not force and _master is not None and (time.time() - _loaded_at) < _TTL:
            return _master
        loaded = await asyncio.get_event_loop().run_in_executor(None, _load_sync)
        _master = loaded
        _loaded_at = time.time()
        return loaded


def _score(q: str, name: str, symbol: str) -> int:
    """높을수록 먼저 노출."""
    q_low = q.lower()
    n_low = name.lower()
    if symbol == q:
        return 1000
    if symbol.startswith(q):
        return 900
    if name == q:
        return 800
    if n_low.startswith(q_low):
        return 700
    if q in name:
        return 500
    if q_low in n_low:
        return 400
    if q in symbol:
        return 200
    return 0


async def search(q: str, limit: int = 10) -> list[StockEntry]:
    q = q.strip()
    if not q:
        return []

    entries = await ensure_loaded()
    if not entries:
        return []

    scored: list[tuple[int, StockEntry]] = []
    for e in entries:
        s = _score(q, e["name"], e["symbol"])
        if s > 0:
            scored.append((s, e))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [e for _, e in scored[:limit]]
