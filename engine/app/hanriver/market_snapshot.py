"""HANRIVER 시황 데이터 수집 서비스.

Week 1 범위: 스냅샷 엔드포인트에 필요한 in-memory 캐시 + 스텁 데이터.
Week 2에서 yfinance / pykrx / RSS 크롤러를 실제로 연결한다.

설계 원칙:
- 외부 API 장애 시에도 대시보드가 깨지지 않도록 stale fallback 보장
- 카테고리별 TTL을 다르게 설정 (지수 5초, 환율 30초, 심리 60초)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    code: str
    name: str
    price: float
    change_pct: float | None = None
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stale: bool = False


# Phase 1 기준 종목 정의. Week 2에서 KIS / yfinance 실데이터로 교체.
KR_INDICES: list[tuple[str, str]] = [
    ("KOSPI", "코스피"),
    ("KOSDAQ", "코스닥"),
    ("KOSPI200", "코스피200"),
    ("KOSPI_NIGHT_FUT", "코스피 야간선물"),
]

GLOBAL_INDICES: list[tuple[str, str]] = [
    ("DJI", "다우"),
    ("IXIC", "나스닥"),
    ("GSPC", "S&P500"),
    ("RUT", "러셀2000"),
    ("N225", "니케이"),
    ("SSEC", "상해"),
    ("HSI", "홍콩H"),
    ("TWII", "대만 가권"),
]

FX_COMMODITIES: list[tuple[str, str]] = [
    ("USD_KRW", "원/달러"),
    ("DXY", "달러인덱스"),
    ("WTI", "WTI"),
    ("GOLD", "금"),
    ("BTC", "비트코인"),
    ("US10Y", "미국채 10년"),
]

SENTIMENT: list[tuple[str, str]] = [
    ("VIX", "VIX"),
    ("FNG", "Fear&Greed"),
    ("EWY", "MSCI Korea ETF"),
    ("NDF_1M", "원/달러 1M NDF"),
]

SECTORS: list[tuple[str, str]] = [
    ("SEMI", "반도체"),
    ("BATTERY", "2차전지"),
    ("BIO", "바이오"),
    ("FINANCE", "금융"),
    ("CONSTRUCT", "건설"),
    ("SHIPBUILD", "조선"),
    ("AUTO", "자동차"),
    ("INTERNET", "인터넷"),
]


# 스텁: Week 2에서 실제 fetcher로 교체. 값은 재현 가능하도록 종목 코드 해시 기반.
def _stub_price(code: str, base: float) -> float:
    import hashlib

    seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
    drift = ((seed + int(time.time()) // 60) % 1000 - 500) / 10000.0
    return round(base * (1 + drift), 4)


def _stub_change_pct(code: str) -> float:
    import hashlib

    seed = int(hashlib.md5((code + "chg").encode()).hexdigest()[:8], 16)
    return round(((seed + int(time.time()) // 120) % 600 - 300) / 100.0, 2)


def _stub_quote(code: str, name: str, base: float) -> Quote:
    return Quote(
        code=code,
        name=name,
        price=_stub_price(code, base),
        change_pct=_stub_change_pct(code),
        stale=True,
    )


_BASE_PRICES: dict[str, float] = {
    "KOSPI": 2612.0, "KOSDAQ": 844.0, "KOSPI200": 347.0, "KOSPI_NIGHT_FUT": 341.0,
    "DJI": 38500.0, "IXIC": 15700.0, "GSPC": 5100.0, "RUT": 2050.0,
    "N225": 39000.0, "SSEC": 3050.0, "HSI": 6500.0, "TWII": 18900.0,
    "USD_KRW": 1362.0, "DXY": 104.3, "WTI": 82.0, "GOLD": 2345.0,
    "BTC": 67800.0, "US10Y": 4.28,
    "VIX": 13.8, "FNG": 52.0, "EWY": 61.2, "NDF_1M": 1365.2,
    "SEMI": 0.0, "BATTERY": 0.0, "BIO": 0.0, "FINANCE": 0.0,
    "CONSTRUCT": 0.0, "SHIPBUILD": 0.0, "AUTO": 0.0, "INTERNET": 0.0,
}


class _TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[float, object]] = {}
        self._lock = asyncio.Lock()

    async def get_or_compute(
        self,
        key: str,
        ttl_seconds: float,
        loader: Callable[[], Awaitable[object]],
    ) -> object:
        now = time.time()
        cached = self._store.get(key)
        if cached and now - cached[0] < ttl_seconds:
            return cached[1]
        async with self._lock:
            cached = self._store.get(key)
            if cached and time.time() - cached[0] < ttl_seconds:
                return cached[1]
            value = await loader()
            self._store[key] = (time.time(), value)
            return value


_cache = _TTLCache()


async def _collect(codes: list[tuple[str, str]]) -> list[Quote]:
    return [_stub_quote(code, name, _BASE_PRICES.get(code, 100.0)) for code, name in codes]


async def get_kr_indices() -> list[Quote]:
    return await _cache.get_or_compute("kr_indices", 5.0, lambda: _collect(KR_INDICES))


async def get_global_indices() -> list[Quote]:
    return await _cache.get_or_compute("global_indices", 30.0, lambda: _collect(GLOBAL_INDICES))


async def get_fx_commodities() -> list[Quote]:
    return await _cache.get_or_compute("fx_commodities", 30.0, lambda: _collect(FX_COMMODITIES))


async def get_sentiment() -> list[Quote]:
    return await _cache.get_or_compute("sentiment", 60.0, lambda: _collect(SENTIMENT))


async def get_sector_heatmap() -> list[Quote]:
    return await _cache.get_or_compute("sectors", 30.0, lambda: _collect(SECTORS))
