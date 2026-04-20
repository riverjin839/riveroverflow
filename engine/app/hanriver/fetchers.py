"""HANRIVER 실시세 fetcher.

- KR 지수/업종: pykrx (KRX 공공 데이터, 인증 불필요)
- 해외 지수/환율/원자재/VIX: yfinance
- F&G Index: alternative.me (크립토 공포탐욕지수 — 시장 지수와는 다르지만 참고용)

모든 fetcher는 예외 발생 시 None을 반환하고 상위 캐시가 stub으로 fallback 한다.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────
# pykrx: 국내 지수
# ────────────────────────────────────────────────────────────

_PYKRX_INDEX_CODES: dict[str, str] = {
    "KOSPI": "1001",
    "KOSPI200": "1028",
    "KOSDAQ": "2001",
}

# KOSPI 섹터 지수 (업종별). 코드 참고: pykrx docs
_PYKRX_SECTOR_CODES: dict[str, tuple[str, str]] = {
    "SEMI": ("1012", "전기전자"),
    "BATTERY": ("1014", "운수장비"),   # 현대차·기아 포함, 2차전지는 KOSDAQ 쪽이 큰 비중
    "BIO": ("1008", "의약품"),
    "FINANCE": ("1020", "금융업"),
    "CONSTRUCT": ("1017", "건설업"),
    "SHIPBUILD": ("1011", "기계"),
    "STEEL": ("1010", "철강금속"),
    "CHEMICAL": ("1007", "화학"),
}


def _pykrx_index_sync(code: str) -> tuple[float, float] | None:
    """최근 영업일 종가와 전일 대비 등락률 반환."""
    from pykrx import stock as krx

    end = date.today()
    start = end - timedelta(days=10)
    df = krx.get_index_ohlcv_by_date(
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
        code,
    )
    if df is None or df.empty or len(df) < 1:
        return None
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else last
    close = float(last["종가"])
    prev_close = float(prev["종가"])
    change_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0
    return close, round(change_pct, 3)


async def fetch_pykrx_index(code: str) -> tuple[float, float] | None:
    try:
        return await asyncio.get_event_loop().run_in_executor(
            None, _pykrx_index_sync, code
        )
    except Exception as e:
        logger.warning("pykrx index fetch failed code=%s: %s", code, e)
        return None


async def fetch_kr_indices() -> dict[str, tuple[float, float]]:
    tasks = {name: fetch_pykrx_index(code) for name, code in _PYKRX_INDEX_CODES.items()}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out: dict[str, tuple[float, float]] = {}
    for name, r in zip(tasks.keys(), results):
        if isinstance(r, tuple):
            out[name] = r
    return out


async def fetch_sector_indices() -> dict[str, tuple[float, float]]:
    tasks = {
        name: fetch_pykrx_index(code) for name, (code, _label) in _PYKRX_SECTOR_CODES.items()
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    out: dict[str, tuple[float, float]] = {}
    for name, r in zip(tasks.keys(), results):
        if isinstance(r, tuple):
            out[name] = r
    return out


# ────────────────────────────────────────────────────────────
# yfinance: 해외 지수, 환율, 원자재, VIX
# ────────────────────────────────────────────────────────────

YFINANCE_TICKERS: dict[str, str] = {
    # 해외 지수
    "DJI": "^DJI",
    "IXIC": "^IXIC",
    "GSPC": "^GSPC",
    "RUT": "^RUT",
    "N225": "^N225",
    "SSEC": "000001.SS",
    "HSI": "^HSI",
    "TWII": "^TWII",
    # 환율/원자재
    "USD_KRW": "KRW=X",
    "DXY": "DX-Y.NYB",
    "WTI": "CL=F",
    "GOLD": "GC=F",
    "BTC": "BTC-USD",
    "US10Y": "^TNX",
    # 심리
    "VIX": "^VIX",
    "EWY": "EWY",
}


def _yfinance_batch_sync(tickers: list[str]) -> dict[str, tuple[float, float]]:
    import yfinance as yf

    # 2일치 데이터로 전일 대비 계산
    data = yf.download(
        tickers=" ".join(tickers),
        period="5d",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=True,
        group_by="ticker",
    )
    out: dict[str, tuple[float, float]] = {}
    if data is None or data.empty:
        return out

    for t in tickers:
        try:
            # yfinance는 단일 티커면 flat frame, 복수면 multi-index
            if len(tickers) == 1:
                series = data["Close"].dropna()
            else:
                series = data[t]["Close"].dropna()
            if len(series) < 1:
                continue
            close = float(series.iloc[-1])
            prev = float(series.iloc[-2]) if len(series) >= 2 else close
            change_pct = ((close - prev) / prev * 100) if prev else 0.0
            out[t] = (close, round(change_pct, 3))
        except (KeyError, ValueError, IndexError):
            continue
    return out


async def fetch_yfinance_batch(codes: list[str]) -> dict[str, tuple[float, float]]:
    tickers = [YFINANCE_TICKERS[c] for c in codes if c in YFINANCE_TICKERS]
    if not tickers:
        return {}
    try:
        raw = await asyncio.get_event_loop().run_in_executor(
            None, _yfinance_batch_sync, tickers
        )
    except Exception as e:
        logger.warning("yfinance batch fetch failed: %s", e)
        return {}

    # 내부 코드로 키 변환
    ticker_to_code = {v: k for k, v in YFINANCE_TICKERS.items()}
    return {ticker_to_code[t]: v for t, v in raw.items() if t in ticker_to_code}


# ────────────────────────────────────────────────────────────
# alternative.me: Fear & Greed (crypto, 참고용)
# ────────────────────────────────────────────────────────────

async def fetch_fear_greed() -> tuple[float, float] | None:
    """alternative.me 공포탐욕지수. 응답 구조:
    {"data":[{"value":"52","value_classification":"Neutral",...}]}
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get("https://api.alternative.me/fng/?limit=2")
            r.raise_for_status()
            payload = r.json().get("data", [])
            if not payload:
                return None
            today = float(payload[0]["value"])
            yesterday = float(payload[1]["value"]) if len(payload) > 1 else today
            change_pct = ((today - yesterday) / yesterday * 100) if yesterday else 0.0
            return today, round(change_pct, 3)
    except Exception as e:
        logger.warning("F&G fetch failed: %s", e)
        return None
