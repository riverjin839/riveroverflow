"""HANRIVER 테이블 정의.

- Phase 1: MarketIndex, NewsItem
- Phase 2: StockFlow, Disclosure, Watchlist, AlertRule
- Phase 3: AiSignal, AiReport, NewsScore
- Phase 4: TradingJournal, ReplayBookmark, BacktestResult
- Phase 5: DailyReport (리포트 큐)
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime, Text, JSON, Index, BigInteger, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# ── Phase 1 ────────────────────────────────────────────
class MarketIndex(Base):
    __tablename__ = "market_indices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (Index("ix_market_indices_code_ts", "code", "ts"),)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    importance: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ── Phase 2 ────────────────────────────────────────────
class StockFlow(Base):
    """일별 수급 데이터 (외국인/기관/개인 순매수)."""
    __tablename__ = "stock_flows"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    foreign_net: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)
    institution_net: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)
    individual_net: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)
    program_net: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)
    short_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 0), nullable=True)

    __table_args__ = (Index("ix_stock_flows_symbol_date", "symbol", "trade_date"),)


class Disclosure(Base):
    """DART 공시."""
    __tablename__ = "disclosures"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    corp_name: Mapped[str] = mapped_column(String(100), nullable=False)
    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    rcept_no: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    rcept_dt: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Watchlist(Base):
    """관심 종목."""
    __tablename__ = "hanriver_watchlist"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # CSV
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    """가격 도달 / 수급 이상 등 알림 규칙."""
    __tablename__ = "hanriver_alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)  # price_above | price_below | volume_spike | flow_reversal
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_triggered: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Phase 3 ────────────────────────────────────────────
class AiSignal(Base):
    """AI 매매 시그널."""
    __tablename__ = "hanriver_ai_signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # day | swing
    signal: Mapped[str] = mapped_column(String(16), nullable=False)  # buy | sell | hold
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    take_profit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), default=0)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)  # Claude 생성 근거
    features: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class AiReport(Base):
    """Claude 생성 리포트 (daily/weekly/event/stock)."""
    __tablename__ = "hanriver_ai_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # daily | weekly | event | stock
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class NewsScore(Base):
    """뉴스 importance LLM 스코어링 결과."""
    __tablename__ = "hanriver_news_scores"

    news_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    importance: Mapped[str] = mapped_column(String(16), nullable=False)
    symbols: Mapped[str | None] = mapped_column(Text, nullable=True)  # CSV of tagged symbols
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Phase 4 ────────────────────────────────────────────
class TradingJournalEntry(Base):
    """매매 일지 (자동 초안 + 사용자 메모)."""
    __tablename__ = "hanriver_journal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trade_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy | sell
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    setup: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 셋업 태그 (VSA_SOS, pullback 등)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 생성 초안
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 사용자 코멘트
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    """백테스트 결과 요약."""
    __tablename__ = "hanriver_backtest_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)  # win_rate, profit_factor, sharpe, mdd
    trades: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
