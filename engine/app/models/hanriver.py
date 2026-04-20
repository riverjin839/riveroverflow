"""HANRIVER 시황 대시보드 테이블.

- market_indices: 지수 스냅샷 (실시간 틱 누적; Week 4 이후 TimescaleDB hypertable 승격 예정)
- news_items: 뉴스/공시 통합 피드
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, DateTime, Text, JSON, Index, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class MarketIndex(Base):
    __tablename__ = "market_indices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3), nullable=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # kr_index | global_index | fx | commodity | sentiment

    __table_args__ = (
        Index("ix_market_indices_code_ts", "code", "ts"),
    )


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)  # hankyung | dart | ...
    published_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    importance: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")  # Phase 3에서 LLM 스코어링
    raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
