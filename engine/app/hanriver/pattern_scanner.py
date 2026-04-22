"""선취매 패턴 스캐너.

사용자가 '동일 패턴 기대 종목'을 찾기 위한 다요인 스코어러.
입력 OHLCV(60일)로부터 다음 특성을 계산해 0~100 점수를 매긴다.

  feature                          가중치   설명
  ─────────────────────────────────────────────────
  base_tightness_20d               25      종가 std/평균 비율이 낮을수록 높음
  ma_alignment                     20      MA20>MA60>MA120, 가격≥MA20
  volume_accumulation              20      3일 평균/20일 평균 거래량 (1.1~1.8 적정)
  vsa_sos_count_20d                15      VSA Sign of Strength 포착 횟수
  not_surged                       10      최근 10일 +5% 이상 봉 ≤ 2 회
  near_20d_high                    10      현재가/20일 고가 = 0.9~1.02

점수 ≥ 60 인 종목을 '패턴 유사 후보'로 간주.
Claude 는 상위 5종목에만 호출해 자연어 해설을 붙인다.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import TypedDict

import numpy as np
import pandas as pd

from . import indicators
from .ai import claude_client
from .stock_master import ensure_loaded as load_master

logger = logging.getLogger(__name__)

MIN_SCORE = 60
MAX_ANALYZE = 5  # Claude 해설 대상 종목 수
CONCURRENCY = 12


@dataclass
class Features:
    base_tightness: float
    ma_alignment: float
    volume_accumulation: float
    vsa_sos_count: float
    not_surged: float
    near_20d_high: float


class Candidate(TypedDict):
    symbol: str
    name: str
    market: str
    close: float
    change_pct: float
    score: int
    features: dict
    reasons: list[str]
    commentary: str | None


WEIGHTS = {
    "base_tightness": 25,
    "ma_alignment": 20,
    "volume_accumulation": 20,
    "vsa_sos_count": 15,
    "not_surged": 10,
    "near_20d_high": 10,
}


# ── feature 계산 ────────────────────────────────────────
def _compute_features(df: pd.DataFrame) -> tuple[Features | None, dict]:
    """df: time/open/high/low/close/volume 60행 이상.

    반환: (Features(0~1 정규화) 또는 None, 원시 메트릭 dict)
    """
    if df is None or len(df) < 30:
        return None, {}
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["close", "volume"])
    if len(df) < 30:
        return None, {}

    close = df["close"]
    last_close = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else last_close
    change_pct_1d = (last_close - prev_close) / prev_close * 100 if prev_close else 0.0

    # 1) base_tightness: 최근 20일 종가 표준편차 / 평균
    tail20 = close.tail(20)
    std_ratio = float(tail20.std() / tail20.mean()) if tail20.mean() else 1.0
    # 0.01 이하 만점, 0.07 이상 0점
    base_tightness = float(np.clip((0.07 - std_ratio) / 0.06, 0, 1))

    # 2) ma_alignment
    ma20 = indicators.sma(close, 20).iloc[-1]
    ma60 = indicators.sma(close, 60).iloc[-1] if len(close) >= 60 else ma20
    ma120 = indicators.sma(close, 120).iloc[-1] if len(close) >= 120 else ma60
    ma20_slope_up = indicators.sma(close, 20).tail(10).is_monotonic_increasing
    align_score = 0.0
    if not np.isnan(ma20) and not np.isnan(ma60):
        if last_close >= ma20 >= ma60:
            align_score += 0.5
        if not np.isnan(ma120) and ma60 >= ma120:
            align_score += 0.3
        if ma20_slope_up:
            align_score += 0.2
    ma_alignment = float(min(align_score, 1.0))

    # 3) volume_accumulation
    vol = df["volume"]
    v3 = float(vol.tail(3).mean()) if len(vol) >= 3 else 0.0
    v20 = float(vol.tail(20).mean()) if len(vol) >= 20 else 1.0
    vol_ratio = v3 / v20 if v20 else 0.0
    # 1.1~1.8 최적, 이 범위 밖은 감점
    if 1.1 <= vol_ratio <= 1.8:
        vol_score = 1.0
    elif 0.9 <= vol_ratio < 1.1:
        vol_score = 0.7
    elif 1.8 < vol_ratio <= 2.5:
        vol_score = 0.6  # 과열 경계
    elif vol_ratio > 2.5:
        vol_score = 0.2  # 이미 터진 거래량
    else:
        vol_score = 0.3
    volume_accumulation = vol_score

    # 4) vsa_sos_count: 최근 20일 내 SOS 횟수
    try:
        vsa_df = indicators.vsa(df)
        sos20 = int(vsa_df["sos"].tail(20).sum())
    except Exception:
        sos20 = 0
    vsa_score = float(min(sos20 / 3.0, 1.0))  # 3회 이상 만점

    # 5) not_surged: 최근 10일 봉별 수익률에서 +5%↑ 카운트
    returns = close.pct_change().tail(10).abs()
    surged_count = int((returns > 0.05).sum())
    not_surged_score = float(max(0.0, 1.0 - surged_count / 3.0))

    # 6) near_20d_high
    high20 = float(df["high"].tail(20).astype(float).max()) if "high" in df.columns else last_close
    ratio = last_close / high20 if high20 else 0.0
    if 0.95 <= ratio <= 1.02:
        near_score = 1.0
    elif 0.90 <= ratio < 0.95:
        near_score = 0.6
    elif 1.02 < ratio <= 1.06:
        near_score = 0.3
    else:
        near_score = 0.0

    features = Features(
        base_tightness=base_tightness,
        ma_alignment=ma_alignment,
        volume_accumulation=volume_accumulation,
        vsa_sos_count=vsa_score,
        not_surged=not_surged_score,
        near_20d_high=near_score,
    )

    raw = {
        "last_close": last_close,
        "change_pct_1d": round(change_pct_1d, 2),
        "std_ratio": round(std_ratio, 4),
        "ma20": float(ma20) if not np.isnan(ma20) else None,
        "ma60": float(ma60) if not np.isnan(ma60) else None,
        "vol_ratio": round(vol_ratio, 2),
        "vsa_sos_20d": sos20,
        "high20": high20,
        "high20_ratio": round(ratio, 3),
        "surged_count_10d": surged_count,
    }
    return features, raw


def _score_and_reasons(feat: Features, raw: dict) -> tuple[int, list[str]]:
    d = asdict(feat)
    total = sum(d[k] * w for k, w in WEIGHTS.items())
    total_int = int(round(total))

    reasons: list[str] = []
    if feat.base_tightness >= 0.7:
        reasons.append(f"타이트 베이스 (20일 σ/μ={raw['std_ratio']:.3f})")
    if feat.ma_alignment >= 0.7:
        reasons.append("이평 정배열 + MA20 상승")
    if feat.volume_accumulation >= 0.7:
        reasons.append(f"조용한 매집 (3/20일 거래량={raw['vol_ratio']:.2f})")
    if feat.vsa_sos_count >= 0.3:
        reasons.append(f"VSA SOS {raw['vsa_sos_20d']}회")
    if feat.not_surged >= 0.7:
        reasons.append("미폭등 구간 (최근 10일 급등봉 적음)")
    if feat.near_20d_high >= 0.7:
        reasons.append(f"20일 고가 근접 ({raw['high20_ratio']:.2f})")
    return total_int, reasons


# ── 유니버스 ─────────────────────────────────────────
async def _universe(kind: str, symbols: list[str] | None) -> list[dict]:
    """스캔 대상 종목 목록."""
    master = await load_master()
    if kind == "custom" and symbols:
        sym_set = {s for s in symbols if s.isdigit() and len(s) == 6}
        return [e for e in master if e["symbol"] in sym_set]
    if kind == "kospi":
        return [e for e in master if e["market"] == "KOSPI"][:300]
    if kind == "kosdaq":
        return [e for e in master if e["market"] == "KOSDAQ"][:200]
    # all (기본): 마스터 상위 500 (시총순 — 네이버 페이지가 시총순)
    return master[:500]


# ── 메인 스캔 ───────────────────────────────────────
async def scan(
    broker,
    kind: str = "all",
    symbols: list[str] | None = None,
    max_results: int = 30,
    min_score: int = MIN_SCORE,
    enable_llm: bool = True,
) -> dict:
    universe = await _universe(kind, symbols)
    sem = asyncio.Semaphore(CONCURRENCY)

    async def eval_one(entry: dict) -> Candidate | None:
        async with sem:
            try:
                ohlcv = await broker.get_ohlcv(entry["symbol"], "D", 60)
            except Exception as e:
                logger.debug("ohlcv fetch failed %s: %s", entry["symbol"], e)
                return None
            if not ohlcv or len(ohlcv) < 30:
                return None
            df = pd.DataFrame(ohlcv)
            feat, raw = _compute_features(df)
            if feat is None:
                return None
            score, reasons = _score_and_reasons(feat, raw)
            if score < min_score:
                return None
            return Candidate(
                symbol=entry["symbol"],
                name=entry["name"],
                market=entry["market"],
                close=raw["last_close"],
                change_pct=raw["change_pct_1d"],
                score=score,
                features={**asdict(feat), **raw},
                reasons=reasons,
                commentary=None,
            )

    results_raw = await asyncio.gather(*(eval_one(e) for e in universe))
    results: list[Candidate] = [r for r in results_raw if r]
    results.sort(key=lambda r: r["score"], reverse=True)
    top = results[:max_results]

    # LLM 해설은 상위 N 종목만 (비용 절감)
    if enable_llm and top:
        await asyncio.gather(*(_explain(c) for c in top[:MAX_ANALYZE]))

    return {
        "universe_kind": kind,
        "universe_size": len(universe),
        "candidate_count": len(results),
        "items": top,
    }


async def _explain(cand: Candidate) -> None:
    prompt = f"""다음 종목이 '선취매 후보' 패턴(타이트 베이스 + 조용한 매집
+ 돌파 임박)에 얼마나 부합하는지 2~3문장으로 평가해 줘.

종목: {cand['name']} ({cand['symbol']}) · {cand['market']}
현재가: {cand['close']:,} ({cand['change_pct']:+.2f}%)
스코어: {cand['score']}/100
매칭 특성: {', '.join(cand['reasons']) or '(없음)'}
지표: {cand['features']}

출력: 2~3문장, 진입 관찰 포인트(저항/지지, 거래량 조건) 포함, 제안 표현.
"""
    try:
        cand["commentary"] = await claude_client.complete(prompt, max_tokens=220, temperature=0.4)
    except Exception as e:
        logger.warning("pattern commentary failed: %s", e)
        cand["commentary"] = None
