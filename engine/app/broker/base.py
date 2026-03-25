"""
Abstract broker interface.
All broker implementations (KIS, Kiwoom) must conform to this contract.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable, Awaitable


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Balance:
    total_value: Decimal       # 총평가금액
    cash: Decimal              # 예수금
    stock_value: Decimal       # 주식평가금액
    profit_loss: Decimal       # 평가손익
    profit_loss_pct: float     # 수익률 (%)
    currency: str = "KRW"


@dataclass
class Position:
    symbol: str                # 종목코드 (e.g. "005930")
    name: str                  # 종목명
    quantity: int              # 보유수량
    avg_price: Decimal         # 평균단가
    current_price: Decimal     # 현재가
    profit_loss: Decimal       # 평가손익
    profit_loss_pct: float     # 수익률 (%)


@dataclass
class MarketPrice:
    symbol: str
    name: str
    price: Decimal             # 현재가
    open: Decimal
    high: Decimal
    low: Decimal
    volume: int                # 거래량
    change: Decimal            # 전일대비
    change_pct: float          # 등락률 (%)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Decimal | None = None   # limit 주문 시 필수
    strategy_id: str | None = None


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    price: Decimal
    status: OrderStatus
    filled_at: datetime | None = None
    message: str = ""


# Type alias for realtime callback
RealtimeCallback = Callable[[MarketPrice], Awaitable[None]]


class AbstractBroker(ABC):
    """All broker implementations must implement this interface."""

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the broker (fetch/refresh access token)."""

    @abstractmethod
    async def get_balance(self) -> Balance:
        """Return current account balance and portfolio summary."""

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        """Return list of currently held positions."""

    @abstractmethod
    async def get_market_price(self, symbol: str) -> MarketPrice:
        """Fetch current market price for a symbol."""

    @abstractmethod
    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "D",   # D=일, W=주, M=월, m=분
        count: int = 100,
    ) -> list[dict]:
        """Return OHLCV (캔들) data for technical analysis."""

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a buy/sell order."""

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""

    @abstractmethod
    async def subscribe_realtime(
        self,
        symbols: list[str],
        callback: RealtimeCallback,
    ) -> None:
        """Subscribe to real-time price updates for given symbols."""

    @abstractmethod
    async def unsubscribe_realtime(self, symbols: list[str]) -> None:
        """Unsubscribe from real-time price updates."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Broker name identifier."""
