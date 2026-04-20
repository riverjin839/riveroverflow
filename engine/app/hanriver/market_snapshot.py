"""HANRIVER 시황 데이터 수집 서비스.

- KR 지수/업종: pykrx (KRX 일봉, 당일 종가는 장 마감 후 업데이트됨)
- 해외 지수/환율/원자재/VIX/EWY: yfinance
- F&G: alternative.me (크립토 F&G, 참고용)
- 실데이터 실패 시 스텁으로 fallback 하고 stale=True 로 마킹

카테고리별 TTL:
- KR 지수: 30초
- 해외 지수/환율/원자재/심리: 60초
- 업종 히트맵: 60초
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable

from . import fetchers

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    code: str
    name: str
    price: float
    change_pct: float | None = None
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stale: bool = False


# ────────────────────────────────────────────────────────────
# 심볼 정의
# ────────────────────────────────────────────────────────────

KR_INDICES: list[tuple[str, str]] = [
    ("KOSPI", "코스피"),
    ("KOSDAQ", "코스닥"),
    ("KOSPI200", "코스피200"),
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
    ("FNG", "F&G (crypto)"),
    ("EWY", "MSCI Korea ETF"),
]

SECTORS: list[tuple[str, str]] = [
    ("SEMI", "전기전자"),
    ("BATTERY", "운수장비"),
    ("BIO", "의약품"),
    ("FINANCE", "금융업"),
    ("CONSTRUCT", "건설업"),
    ("SHIPBUILD", "기계"),
    ("STEEL", "철강금속"),
    ("CHEMICAL", "화학"),
]


# 스텁 baseline — 실데이터가 실패했을 때만 렌더링 목적으로 사용
_STUB_BASE: dict[str, float] = {
    "KOSPI": 2612.0, "KOSDAQ": 844.0, "KOSPI200": 347.0,
    "DJI": 38500.0, "IXIC": 15700.0, "GSPC": 5100.0, "RUT": 2050.0,
    "N225": 39000.0, "SSEC": 3050.0, "HSI": 6500.0, "TWII": 18900.0,
    "USD_KRW": 1362.0, "DXY": 104.3, "WTI": 82.0, "GOLD": 2345.0,
    "BTC": 67800.0, "US10Y": 4.28,
    "VIX": 13.8, "FNG": 52.0, "EWY": 61.2,
}


def _stub_quote(code: str, name: str) -> Quote:
    base = _STUB_BASE.get(code, 100.0)
    seed = int(hashlib.md5(code.encode()).hexdigest()[:8], 16)
    drift = ((seed + int(time.time()) // 300) % 1000 - 500) / 10000.0
    change = round(((seed + int(time.time()) // 600) % 600 - 300) / 100.0, 2)
    return Quote(
        code=code,
        name=name,
        price=round(base * (1 + drift), 4),
        change_pct=change,
        stale=True,
    )


# ────────────────────────────────────────────────────────────
# 캐시
# ────────────────────────────────────────────────────────────

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
            try:
                value = await loader()
            except Exception as e:
                logger.warning("loader failed key=%s: %s", key, e)
                if cached:
                    return cached[1]
                raise
            self._store[key] = (time.time(), value)
            return value


_cache = _TTLCache()


# ────────────────────────────────────────────────────────────
# 카테고리별 loader
# ────────────────────────────────────────────────────────────

def _merge_with_stub(
    definitions: list[tuple[str, str]],
    real: dict[str, tuple[float, float]],
) -> list[Quote]:
    """실데이터에 없는 코드는 stub으로 채움."""
    now = datetime.now(timezone.utc)
    out: list[Quote] = []
    for code, name in definitions:
        if code in real:
            price, change_pct = real[code]
            out.append(Quote(code=code, name=name, price=price, change_pct=change_pct, ts=now, stale=False))
        else:
            out.append(_stub_quote(code, name))
    return out


async def _load_kr_indices() -> list[Quote]:
    real = await fetchers.fetch_kr_indices()
    return _merge_with_stub(KR_INDICES, real)


async def _load_global_indices() -> list[Quote]:
    codes = [c for c, _ in GLOBAL_INDICES]
    real = await fetchers.fetch_yfinance_batch(codes)
    return _merge_with_stub(GLOBAL_INDICES, real)


async def _load_fx_commodities() -> list[Quote]:
    codes = [c for c, _ in FX_COMMODITIES]
    real = await fetchers.fetch_yfinance_batch(codes)
    return _merge_with_stub(FX_COMMODITIES, real)


async def _load_sentiment() -> list[Quote]:
    yf_codes = ["VIX", "EWY"]
    real = await fetchers.fetch_yfinance_batch(yf_codes)

    fng = await fetchers.fetch_fear_greed()
    if fng is not None:
        real["FNG"] = fng

    return _merge_with_stub(SENTIMENT, real)


async def _load_sectors() -> list[Quote]:
    real = await fetchers.fetch_sector_indices()
    return _merge_with_stub(SECTORS, real)


# ────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────

async def get_kr_indices() -> list[Quote]:
    return await _cache.get_or_compute("kr_indices", 30.0, _load_kr_indices)


async def get_global_indices() -> list[Quote]:
    return await _cache.get_or_compute("global_indices", 60.0, _load_global_indices)


async def get_fx_commodities() -> list[Quote]:
    return await _cache.get_or_compute("fx_commodities", 60.0, _load_fx_commodities)


async def get_sentiment() -> list[Quote]:
    return await _cache.get_or_compute("sentiment", 60.0, _load_sentiment)


async def get_sector_heatmap() -> list[Quote]:
    return await _cache.get_or_compute("sectors", 60.0, _load_sectors)
