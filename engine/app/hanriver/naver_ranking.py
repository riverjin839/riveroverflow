"""네이버 금융 순위 스크래퍼.

pykrx 는 KRX 공공 API 의존이라 장중에 JSON 400 을 자주 반환한다.
네이버 금융 순위 페이지는 HTML 이 안정적이고 장중 실시간 반영된다.

- 상한가: https://finance.naver.com/sise/sise_upper.naver
- 급등:   https://finance.naver.com/sise/sise_rise.naver
- 거래대금: https://finance.naver.com/sise/sise_quant.naver

모두 동일한 테이블 구조. KOSPI + KOSDAQ 각각 파라미터로 가져온다.
"""
from __future__ import annotations

import logging
import re
from typing import Literal, TypedDict

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NAVER_FINANCE_BASE = "https://finance.naver.com/sise"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

RankKind = Literal["upper", "rise", "quant"]  # 상한가 / 급등 / 거래대금 상위
SosokKind = Literal["0", "1"]  # 0=KOSPI, 1=KOSDAQ


class RankRow(TypedDict):
    symbol: str
    name: str
    close: float
    change: float
    change_pct: float
    volume: int
    market: str  # KOSPI | KOSDAQ


def _to_int(s: str) -> int:
    s = s.replace(",", "").replace("+", "").replace("%", "").strip()
    if not s or s == "-":
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _to_float(s: str) -> float:
    s = s.replace(",", "").replace("+", "").replace("%", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


async def _fetch_page(kind: RankKind, sosok: SosokKind) -> str:
    url = f"{NAVER_FINANCE_BASE}/sise_{kind}.naver"
    params = {"sosok": sosok}
    async with httpx.AsyncClient(timeout=6.0, headers=_HEADERS) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        # 네이버는 EUC-KR 계열을 사용하기도 함. httpx 가 meta 를 못 읽으면 cp949 강제
        if "charset" not in r.headers.get("content-type", "").lower():
            try:
                return r.content.decode("euc-kr")
            except UnicodeDecodeError:
                return r.text
        return r.text


def _parse_rank_table(html: str, market: str) -> list[RankRow]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.type_5")
    if not table:
        return []

    rows: list[RankRow] = []
    for tr in table.select("tr"):
        tds = tr.find_all("td")
        if len(tds) < 7:
            continue
        a = tds[1].find("a", href=True)
        if not a:
            continue
        href = a.get("href", "")
        m = re.search(r"code=(\d{6})", href)
        if not m:
            continue
        symbol = m.group(1)
        name = a.get_text(strip=True)
        close = _to_float(tds[2].get_text(strip=True))
        change = _to_float(tds[3].get_text(strip=True))
        change_pct = _to_float(tds[4].get_text(strip=True))
        volume = _to_int(tds[5].get_text(strip=True))
        # 전일 대비 방향 (하락 시 - 부호 반영)
        cls_join = " ".join(tds[3].get("class", [])) + " " + " ".join(tds[4].get("class", []))
        if "nv01" in cls_join or "down" in cls_join.lower():
            change = -abs(change)
            change_pct = -abs(change_pct)

        rows.append(RankRow(
            symbol=symbol, name=name, close=close, change=change,
            change_pct=change_pct, volume=volume, market=market,
        ))
    return rows


async def fetch_upper_limit() -> list[RankRow]:
    """상한가 종목 (KOSPI + KOSDAQ 통합)."""
    import asyncio
    kospi_html, kosdaq_html = await asyncio.gather(
        _fetch_page("upper", "0"),
        _fetch_page("upper", "1"),
        return_exceptions=True,
    )
    out: list[RankRow] = []
    if isinstance(kospi_html, str):
        out.extend(_parse_rank_table(kospi_html, "KOSPI"))
    if isinstance(kosdaq_html, str):
        out.extend(_parse_rank_table(kosdaq_html, "KOSDAQ"))
    return out


async def fetch_top_risers(min_change_pct: float = 10.0) -> list[RankRow]:
    """급등주 — 등락률 ≥ min_change_pct 필터."""
    import asyncio
    kospi_html, kosdaq_html = await asyncio.gather(
        _fetch_page("rise", "0"),
        _fetch_page("rise", "1"),
        return_exceptions=True,
    )
    merged: list[RankRow] = []
    if isinstance(kospi_html, str):
        merged.extend(_parse_rank_table(kospi_html, "KOSPI"))
    if isinstance(kosdaq_html, str):
        merged.extend(_parse_rank_table(kosdaq_html, "KOSDAQ"))
    return [r for r in merged if r["change_pct"] >= min_change_pct]


async def fetch_top_by_volume() -> list[RankRow]:
    """거래대금 상위. 거래량 기준이 아닌 대금 기반은 페이지 구조상 별도 파라미터 필요."""
    import asyncio
    kospi_html, kosdaq_html = await asyncio.gather(
        _fetch_page("quant", "0"),
        _fetch_page("quant", "1"),
        return_exceptions=True,
    )
    out: list[RankRow] = []
    if isinstance(kospi_html, str):
        out.extend(_parse_rank_table(kospi_html, "KOSPI"))
    if isinstance(kosdaq_html, str):
        out.extend(_parse_rank_table(kosdaq_html, "KOSDAQ"))
    out.sort(key=lambda r: r["volume"] * r["close"], reverse=True)
    return out[:50]
