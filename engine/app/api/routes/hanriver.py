"""HANRIVER API.

Phase 1: 시황 대시보드
Phase 2: 종목 상세 (차트, 수급, 지표, 공시), 관심종목, 알림
Phase 3: AI 시그널, 리포트
Phase 4: 매매 일지, 복기, 백테스트
Phase 5: Daily/Weekly 자동 리포트
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...hanriver import (
    market_snapshot,
    news_feed,
    flow as flow_mod,
    disclosures as disclosures_mod,
    indicators,
    naver as naver_mod,
    limit_up as limit_up_mod,
    stock_master as stock_master_mod,
)
from ...hanriver.ai import signal_generator, report_builder, news_scoring, coach
from ...hanriver import journal as journal_mod
from ...hanriver import backtest as backtest_mod
from ...hanriver import replay as replay_mod
from ...hanriver.notify import telegram
from ...models.hanriver import (
    Watchlist, AlertRule, AiSignal, AiReport, TradingJournalEntry, BacktestResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/hanriver", tags=["hanriver"])


# ══════════════════════════════════════════════════════
# Phase 1 — 시황 대시보드
# ══════════════════════════════════════════════════════

class QuoteResponse(BaseModel):
    code: str
    name: str
    price: float
    change_pct: float | None
    ts: datetime
    stale: bool


class NewsResponse(BaseModel):
    id: int
    source: str
    title: str
    url: str
    importance: str
    published_at: datetime


def _to_quote(q) -> QuoteResponse:
    return QuoteResponse(
        code=q.code, name=q.name, price=q.price,
        change_pct=q.change_pct, ts=q.ts, stale=q.stale,
    )


@router.get("/indices/kr", response_model=list[QuoteResponse])
async def get_kr_indices():
    return [_to_quote(q) for q in await market_snapshot.get_kr_indices()]


@router.get("/indices/global", response_model=list[QuoteResponse])
async def get_global_indices():
    return [_to_quote(q) for q in await market_snapshot.get_global_indices()]


@router.get("/fx", response_model=list[QuoteResponse])
async def get_fx():
    return [_to_quote(q) for q in await market_snapshot.get_fx_commodities()]


@router.get("/sentiment", response_model=list[QuoteResponse])
async def get_sentiment():
    return [_to_quote(q) for q in await market_snapshot.get_sentiment()]


@router.get("/heatmap/sectors", response_model=list[QuoteResponse])
async def get_sector_heatmap():
    return [_to_quote(q) for q in await market_snapshot.get_sector_heatmap()]


class SearchResult(BaseModel):
    symbol: str
    name: str
    market: str


@router.get("/stocks/search", response_model=list[SearchResult])
async def search_stocks(q: str = Query(..., min_length=1, max_length=40), limit: int = 10):
    """종목 자동완성.
    1차: 로컬 stock master (pykrx 로 적재, 24h TTL) — 오프라인에서도 동작
    2차(비어 있을 때만): 네이버 검색 API
    """
    try:
        items = await stock_master_mod.search(q, limit=limit)
        if items:
            return [SearchResult(**it) for it in items]
    except Exception as e:
        logger.warning("local stock search failed: %s", e)

    # Fallback: Naver
    try:
        items = await naver_mod.search_stock(q, limit=limit)
        return [SearchResult(**it) for it in items]
    except Exception as e:
        logger.warning("naver search failed: %s", e)
        return []


@router.post("/stocks/master/reload")
async def reload_stock_master():
    """종목 마스터 수동 재적재 (일일 리프레시 트리거)."""
    entries = await stock_master_mod.ensure_loaded(force=True)
    return {"count": len(entries)}


@router.get("/limit-up")
async def get_limit_up(date_str: str | None = Query(None, alias="date"), force: bool = False):
    """오늘의 상한가/급등 종목 + 거래대금 + AI 분석 상승 이유.

    - date 미지정 시 최근 영업일
    - 상한가(>=29.5%) 만 LLM 상승이유를 생성, 급등(>=10%) 은 뉴스 제목만 첨부
    - 결과는 날짜 기준으로 메모리 캐시 (force=true 로 재생성 가능)
    """
    target = None
    if date_str:
        try:
            target = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(400, "date 형식은 YYYY-MM-DD")
    return await limit_up_mod.get_limit_up_report(target=target, force=force)


@router.get("/news", response_model=list[NewsResponse])
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    items = await news_feed.list_news(session, limit)
    return [
        NewsResponse(
            id=n.id, source=n.source, title=n.title,
            url=n.url, importance=n.importance, published_at=n.published_at,
        ) for n in items
    ]


# ══════════════════════════════════════════════════════
# Phase 2 — 종목 상세
# ══════════════════════════════════════════════════════

class OhlcvPoint(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockDetailResponse(BaseModel):
    symbol: str
    name: str
    price: float
    change_pct: float
    volume: int
    indicators: dict


@router.get("/stock/{symbol}/ohlcv", response_model=list[OhlcvPoint])
async def get_stock_ohlcv(
    symbol: str,
    period: str = "D",
    count: int = Query(120, ge=20, le=500),
    request: Request = None,
):
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(503, "브로커 미초기화")
    data = await broker.get_ohlcv(symbol, period, count)
    return [OhlcvPoint(**p) for p in data]


@router.get("/stock/{symbol}", response_model=StockDetailResponse)
async def get_stock_detail(symbol: str, request: Request):
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(503, "브로커 미초기화")
    if not symbol.isdigit() or len(symbol) != 6:
        raise HTTPException(400, f"유효한 종목 코드가 아닙니다: '{symbol}'")
    try:
        market = await broker.get_market_price(symbol)
        ohlcv = await broker.get_ohlcv(symbol, "D", 200)
    except Exception as e:
        raise HTTPException(502, f"시세 조회 실패: {e}")

    df = pd.DataFrame(ohlcv)
    snap = indicators.latest_snapshot(df) if not df.empty else {}

    return StockDetailResponse(
        symbol=symbol,
        name=market.name,
        price=float(market.price),
        change_pct=market.change_pct or 0.0,
        volume=int(market.volume),
        indicators=snap,
    )


class FlowResponse(BaseModel):
    trade_date: str
    foreign_net: float
    institution_net: float
    individual_net: float


@router.get("/stock/{symbol}/flow", response_model=list[FlowResponse])
async def get_stock_flow(symbol: str, days: int = Query(30, ge=5, le=180)):
    rows = await flow_mod.fetch_flow(symbol, days)
    return [FlowResponse(**r) for r in rows]


@router.get("/stock/{symbol}/short")
async def get_stock_short(symbol: str):
    data = await flow_mod.fetch_short_balance(symbol)
    return data or {}


class DisclosureResponse(BaseModel):
    corp_name: str
    symbol: str | None
    report_name: str
    rcept_no: str
    rcept_dt: str
    url: str


@router.get("/disclosures", response_model=list[DisclosureResponse])
async def get_disclosures(days: int = 1, limit: int = 50):
    rows = await disclosures_mod.list_recent_disclosures(days=days, count=limit)
    return [DisclosureResponse(**r) for r in rows]


@router.get("/stock/{symbol}/disclosures", response_model=list[DisclosureResponse])
async def get_stock_disclosures(symbol: str, days: int = 30):
    rows = await disclosures_mod.list_symbol_disclosures(symbol, days=days)
    return [DisclosureResponse(**r) for r in rows]


# ── Watchlist ─────────────────────────────────────────
class WatchlistItem(BaseModel):
    id: int
    symbol: str
    name: str
    tags: str | None
    memo: str | None


class WatchlistCreate(BaseModel):
    symbol: str
    name: str
    tags: str | None = None
    memo: str | None = None


@router.get("/watchlist", response_model=list[WatchlistItem])
async def list_watchlist(session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Watchlist).order_by(Watchlist.created_at.desc()))).scalars().all()
    return [WatchlistItem(id=r.id, symbol=r.symbol, name=r.name, tags=r.tags, memo=r.memo) for r in rows]


@router.post("/watchlist", response_model=WatchlistItem)
async def add_watchlist(body: WatchlistCreate, session: AsyncSession = Depends(get_db)):
    w = Watchlist(symbol=body.symbol, name=body.name, tags=body.tags, memo=body.memo)
    session.add(w)
    await session.flush()
    return WatchlistItem(id=w.id, symbol=w.symbol, name=w.name, tags=w.tags, memo=w.memo)


@router.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str, session: AsyncSession = Depends(get_db)):
    await session.execute(delete(Watchlist).where(Watchlist.symbol == symbol))
    return {"status": "ok"}


# ── Alerts ────────────────────────────────────────────
class AlertItem(BaseModel):
    id: int
    symbol: str
    rule_type: str
    threshold: float | None
    enabled: bool
    last_triggered: datetime | None
    memo: str | None


class AlertCreate(BaseModel):
    symbol: str
    rule_type: str
    threshold: float | None = None
    memo: str | None = None


@router.get("/alerts", response_model=list[AlertItem])
async def list_alerts(session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(AlertRule).order_by(AlertRule.created_at.desc()))).scalars().all()
    return [
        AlertItem(
            id=r.id, symbol=r.symbol, rule_type=r.rule_type,
            threshold=float(r.threshold) if r.threshold is not None else None,
            enabled=r.enabled, last_triggered=r.last_triggered, memo=r.memo,
        ) for r in rows
    ]


@router.post("/alerts", response_model=AlertItem)
async def create_alert(body: AlertCreate, session: AsyncSession = Depends(get_db)):
    a = AlertRule(
        symbol=body.symbol, rule_type=body.rule_type,
        threshold=Decimal(str(body.threshold)) if body.threshold is not None else None,
        memo=body.memo,
    )
    session.add(a)
    await session.flush()
    return AlertItem(
        id=a.id, symbol=a.symbol, rule_type=a.rule_type,
        threshold=float(a.threshold) if a.threshold is not None else None,
        enabled=a.enabled, last_triggered=a.last_triggered, memo=a.memo,
    )


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, session: AsyncSession = Depends(get_db)):
    await session.execute(delete(AlertRule).where(AlertRule.id == alert_id))
    return {"status": "ok"}


# ══════════════════════════════════════════════════════
# Phase 3 — AI 엔진
# ══════════════════════════════════════════════════════

class SignalResponse(BaseModel):
    id: int
    symbol: str
    name: str
    mode: str
    signal: str
    entry_price: float | None
    stop_loss: float | None
    take_profit: float | None
    confidence: float
    rationale: str
    created_at: datetime


class GenerateSignalRequest(BaseModel):
    symbol: str
    mode: str = "day"  # day | swing


@router.post("/signals/generate", response_model=SignalResponse)
async def generate_signal(
    body: GenerateSignalRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(503, "브로커 미초기화")

    # 한글명이 실수로 들어오는 경우를 방지 — 숫자 6자리 코드인지 간단 검증
    sym = body.symbol.strip()
    if not sym.isdigit() or len(sym) != 6:
        raise HTTPException(
            status_code=400,
            detail=f"유효한 종목 코드(6자리 숫자)를 선택해 주세요. 입력값: '{body.symbol}'",
        )

    try:
        result = await signal_generator.generate(broker, sym, body.mode)
    except Exception as e:
        logger.warning("signal generation failed symbol=%s: %s", sym, e)
        raise HTTPException(502, f"시그널 생성 실패: {e}")
    sig = AiSignal(
        symbol=result["symbol"], name=result["name"], mode=body.mode,
        signal=result["signal"],
        entry_price=Decimal(str(result["entry_price"])) if result.get("entry_price") else None,
        stop_loss=Decimal(str(result["stop_loss"])) if result.get("stop_loss") else None,
        take_profit=Decimal(str(result["take_profit"])) if result.get("take_profit") else None,
        confidence=Decimal(str(result["confidence"])),
        rationale=result["rationale"],
        features=result.get("features"),
    )
    session.add(sig)
    await session.flush()

    # 텔레그램 알림 (설정되어 있을 때만)
    await telegram.send_signal(sig)

    return SignalResponse(
        id=sig.id, symbol=sig.symbol, name=sig.name, mode=sig.mode,
        signal=sig.signal,
        entry_price=float(sig.entry_price) if sig.entry_price else None,
        stop_loss=float(sig.stop_loss) if sig.stop_loss else None,
        take_profit=float(sig.take_profit) if sig.take_profit else None,
        confidence=float(sig.confidence),
        rationale=sig.rationale,
        created_at=sig.created_at,
    )


@router.get("/signals", response_model=list[SignalResponse])
async def list_signals(limit: int = 30, session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(
        select(AiSignal).order_by(AiSignal.created_at.desc()).limit(limit)
    )).scalars().all()
    return [
        SignalResponse(
            id=r.id, symbol=r.symbol, name=r.name, mode=r.mode,
            signal=r.signal,
            entry_price=float(r.entry_price) if r.entry_price else None,
            stop_loss=float(r.stop_loss) if r.stop_loss else None,
            take_profit=float(r.take_profit) if r.take_profit else None,
            confidence=float(r.confidence), rationale=r.rationale,
            created_at=r.created_at,
        ) for r in rows
    ]


class ReportResponse(BaseModel):
    id: int
    report_type: str
    subject: str
    content_md: str
    created_at: datetime


class GenerateReportRequest(BaseModel):
    report_type: str  # daily | weekly | stock
    subject: str  # 종목명/날짜 등


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    body: GenerateReportRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    broker = getattr(request.app.state, "broker", None)
    md = await report_builder.build(body.report_type, body.subject, broker=broker, session=session)
    rep = AiReport(report_type=body.report_type, subject=body.subject, content_md=md)
    session.add(rep)
    await session.flush()
    return ReportResponse(
        id=rep.id, report_type=rep.report_type, subject=rep.subject,
        content_md=rep.content_md, created_at=rep.created_at,
    )


@router.get("/reports", response_model=list[ReportResponse])
async def list_reports(limit: int = 20, session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(
        select(AiReport).order_by(AiReport.created_at.desc()).limit(limit)
    )).scalars().all()
    return [ReportResponse(
        id=r.id, report_type=r.report_type, subject=r.subject,
        content_md=r.content_md, created_at=r.created_at,
    ) for r in rows]


@router.post("/news/score-recent")
async def score_recent_news(session: AsyncSession = Depends(get_db)):
    """최근 뉴스를 Claude로 importance 스코어링."""
    scored = await news_scoring.score_recent(session, limit=20)
    return {"scored": scored}


# ══════════════════════════════════════════════════════
# Phase 4 — 매매 일지 & 복기 & 백테스트
# ══════════════════════════════════════════════════════

class JournalItem(BaseModel):
    id: int
    trade_date: datetime
    symbol: str
    name: str
    side: str
    quantity: int
    price: float
    pnl: float | None
    setup: str | None
    draft: str | None
    user_note: str | None


@router.post("/journal/sync")
async def journal_sync(session: AsyncSession = Depends(get_db)):
    """내부 trades 테이블 → journal 자동 초안 동기화."""
    count = await journal_mod.sync_from_trades(session)
    return {"synced": count}


@router.get("/journal", response_model=list[JournalItem])
async def list_journal(limit: int = 50, session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(
        select(TradingJournalEntry).order_by(TradingJournalEntry.trade_date.desc()).limit(limit)
    )).scalars().all()
    return [JournalItem(
        id=r.id, trade_date=r.trade_date, symbol=r.symbol, name=r.name,
        side=r.side, quantity=r.quantity, price=float(r.price),
        pnl=float(r.pnl) if r.pnl else None, setup=r.setup,
        draft=r.draft, user_note=r.user_note,
    ) for r in rows]


class JournalUpdateRequest(BaseModel):
    setup: str | None = None
    user_note: str | None = None


@router.patch("/journal/{entry_id}")
async def update_journal(
    entry_id: int, body: JournalUpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    entry = await session.get(TradingJournalEntry, entry_id)
    if not entry:
        raise HTTPException(404, "일지 항목 없음")
    if body.setup is not None:
        entry.setup = body.setup
    if body.user_note is not None:
        entry.user_note = body.user_note
    return {"status": "ok"}


@router.post("/journal/{entry_id}/coach")
async def coach_entry(entry_id: int, session: AsyncSession = Depends(get_db)):
    entry = await session.get(TradingJournalEntry, entry_id)
    if not entry:
        raise HTTPException(404, "일지 항목 없음")
    result = await coach.critique(entry)
    return result


class ReplayRequest(BaseModel):
    symbol: str
    target_date: str  # YYYY-MM-DD


@router.post("/replay")
async def replay(
    body: ReplayRequest, request: Request,
    session: AsyncSession = Depends(get_db),
):
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(503, "브로커 미초기화")
    return await replay_mod.snapshot(
        broker=broker, session=session,
        symbol=body.symbol, target_date=body.target_date,
    )


class BacktestRequest(BaseModel):
    name: str
    symbol: str
    strategy: str  # ma_cross | rsi | vsa
    params: dict[str, Any] = {}
    start_date: str
    end_date: str


@router.post("/backtest/run")
async def run_backtest(
    body: BacktestRequest, request: Request,
    session: AsyncSession = Depends(get_db),
):
    broker = getattr(request.app.state, "broker", None)
    if broker is None:
        raise HTTPException(503, "브로커 미초기화")
    result = await backtest_mod.run(
        broker=broker, symbol=body.symbol,
        strategy=body.strategy, params=body.params,
        start_date=body.start_date, end_date=body.end_date,
    )
    bt = BacktestResult(
        name=body.name,
        strategy_config={"strategy": body.strategy, "params": body.params, "symbol": body.symbol},
        start_date=datetime.fromisoformat(body.start_date),
        end_date=datetime.fromisoformat(body.end_date),
        metrics=result["metrics"],
        trades=result.get("trades"),
    )
    session.add(bt)
    await session.flush()
    return {"id": bt.id, **result}


@router.get("/backtest")
async def list_backtest(limit: int = 20, session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(
        select(BacktestResult).order_by(BacktestResult.created_at.desc()).limit(limit)
    )).scalars().all()
    return [{
        "id": r.id, "name": r.name,
        "strategy_config": r.strategy_config,
        "metrics": r.metrics,
        "created_at": r.created_at.isoformat(),
    } for r in rows]
