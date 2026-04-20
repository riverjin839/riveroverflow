"""DART OpenAPI 공시 수집.

API Key 미설정 시 비어 있는 리스트를 반환해 대시보드를 무너뜨리지 않는다.
https://opendart.fss.or.kr/
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import TypedDict

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

DART_BASE = "https://opendart.fss.or.kr/api"


class DisclosureRow(TypedDict):
    corp_name: str
    corp_code: str
    symbol: str | None
    report_name: str
    rcept_no: str
    rcept_dt: str
    url: str


async def list_recent_disclosures(days: int = 1, count: int = 50) -> list[DisclosureRow]:
    api_key = getattr(settings, "dart_api_key", "")
    if not api_key:
        logger.info("DART_API_KEY 미설정 — 공시 수집 스킵")
        return []

    bgn = (date.today() - timedelta(days=days)).strftime("%Y%m%d")
    end = date.today().strftime("%Y%m%d")
    params = {
        "crtfc_key": api_key,
        "bgn_de": bgn,
        "end_de": end,
        "page_count": min(count, 100),
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(f"{DART_BASE}/list.json", params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("DART list fetch failed: %s", e)
        return []

    if data.get("status") != "000":
        logger.warning("DART error: %s %s", data.get("status"), data.get("message"))
        return []

    out: list[DisclosureRow] = []
    for item in data.get("list", [])[:count]:
        rcept_no = item.get("rcept_no", "")
        out.append(DisclosureRow(
            corp_name=item.get("corp_name", ""),
            corp_code=item.get("corp_code", ""),
            symbol=item.get("stock_code") or None,
            report_name=item.get("report_nm", ""),
            rcept_no=rcept_no,
            rcept_dt=item.get("rcept_dt", ""),
            url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}",
        ))
    return out


async def list_symbol_disclosures(symbol: str, days: int = 30) -> list[DisclosureRow]:
    """특정 종목 공시 목록."""
    all_recent = await list_recent_disclosures(days=days, count=100)
    return [d for d in all_recent if d["symbol"] == symbol]
