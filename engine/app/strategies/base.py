"""
Abstract strategy interface - plugin architecture.
Each strategy evaluates market data and returns a Signal.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import pandas as pd


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class MarketSnapshot:
    """Market data snapshot passed to strategy.evaluate()."""
    symbol: str
    current_price: float
    ohlcv: pd.DataFrame          # columns: time, open, high, low, close, volume
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Pre-computed indicators (populated by engine runner)
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    volume_ma20: float | None = None


@dataclass
class Signal:
    """Trading signal emitted by a strategy."""
    strategy_id: str
    symbol: str
    signal_type: SignalType
    confidence: float            # 0.0 to 1.0
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_actionable(self) -> bool:
        return self.signal_type in (SignalType.BUY, SignalType.SELL)


@dataclass
class StrategyConfig:
    """Strategy configuration (stored in DB, editable from UI)."""
    strategy_id: str
    strategy_type: str           # "ma_cross", "rsi", "macd", etc.
    symbols: list[str]           # 모니터링 종목 코드
    params: dict[str, Any]       # strategy-specific parameters
    enabled: bool = True
    broker: str = "KIS"          # "KIS" | "Kiwoom"


class AbstractStrategy(ABC):
    """Base class for all trading strategies."""

    def __init__(self, config: StrategyConfig):
        self.config = config

    @property
    def strategy_id(self) -> str:
        return self.config.strategy_id

    @property
    def symbols(self) -> list[str]:
        return self.config.symbols

    @abstractmethod
    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        """
        Evaluate market snapshot and return a trading signal.
        Must be synchronous and deterministic.
        """

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.strategy_id}, symbols={self.symbols})"
