import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, Numeric, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    side: Mapped[str] = mapped_column(String(10), nullable=False)          # buy | sell
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)   # market | limit
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    strategy_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    broker: Mapped[str] = mapped_column(String(20), nullable=False, default="KIS")
    signal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class StrategyConfig(Base):
    __tablename__ = "strategy_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(50), nullable=False)   # ma_cross | rsi | macd
    symbols: Mapped[str] = mapped_column(Text, nullable=False)               # JSON array
    params: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON object
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    broker: Mapped[str] = mapped_column(String(20), default="KIS")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
