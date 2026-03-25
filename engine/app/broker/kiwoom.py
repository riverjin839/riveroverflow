"""
Kiwoom Securities broker implementation.
Communicates with kiwoom-bridge service (Windows container running pywin32 COM → REST).
"""
import logging
from datetime import datetime
from decimal import Decimal

import httpx

from .base import (
    AbstractBroker,
    Balance,
    MarketPrice,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RealtimeCallback,
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class KiwoomBroker(AbstractBroker):
    """Kiwoom Securities broker via bridge service."""

    def __init__(self):
        self._base_url = settings.kiwoom_bridge_url
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    @property
    def name(self) -> str:
        return "Kiwoom"

    async def authenticate(self) -> None:
        """Connect to Kiwoom bridge and trigger login."""
        resp = await self._client.post("/auth/login")
        resp.raise_for_status()
        logger.info("Kiwoom bridge authenticated")

    async def get_balance(self) -> Balance:
        resp = await self._client.get("/account/balance")
        resp.raise_for_status()
        data = resp.json()
        return Balance(
            total_value=Decimal(str(data["total_value"])),
            cash=Decimal(str(data["cash"])),
            stock_value=Decimal(str(data["stock_value"])),
            profit_loss=Decimal(str(data["profit_loss"])),
            profit_loss_pct=float(data["profit_loss_pct"]),
        )

    async def get_positions(self) -> list[Position]:
        resp = await self._client.get("/account/positions")
        resp.raise_for_status()
        return [
            Position(
                symbol=p["symbol"],
                name=p["name"],
                quantity=int(p["quantity"]),
                avg_price=Decimal(str(p["avg_price"])),
                current_price=Decimal(str(p["current_price"])),
                profit_loss=Decimal(str(p["profit_loss"])),
                profit_loss_pct=float(p["profit_loss_pct"]),
            )
            for p in resp.json()
        ]

    async def get_market_price(self, symbol: str) -> MarketPrice:
        resp = await self._client.get(f"/market/price/{symbol}")
        resp.raise_for_status()
        d = resp.json()
        return MarketPrice(
            symbol=symbol,
            name=d["name"],
            price=Decimal(str(d["price"])),
            open=Decimal(str(d["open"])),
            high=Decimal(str(d["high"])),
            low=Decimal(str(d["low"])),
            volume=int(d["volume"]),
            change=Decimal(str(d["change"])),
            change_pct=float(d["change_pct"]),
            timestamp=datetime.fromisoformat(d["timestamp"]),
        )

    async def get_ohlcv(
        self, symbol: str, period: str = "D", count: int = 100
    ) -> list[dict]:
        resp = await self._client.get(
            f"/market/ohlcv/{symbol}",
            params={"period": period, "count": count},
        )
        resp.raise_for_status()
        return resp.json()

    async def place_order(self, order: OrderRequest) -> OrderResult:
        payload = {
            "symbol": order.symbol,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": str(order.price) if order.price else None,
        }
        resp = await self._client.post("/order", json=payload)
        resp.raise_for_status()
        d = resp.json()
        return OrderResult(
            order_id=d["order_id"],
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=order.price or Decimal("0"),
            status=OrderStatus(d.get("status", "pending")),
        )

    async def cancel_order(self, order_id: str) -> bool:
        resp = await self._client.delete(f"/order/{order_id}")
        return resp.status_code == 200

    async def subscribe_realtime(
        self, symbols: list[str], callback: RealtimeCallback
    ) -> None:
        # Kiwoom bridge supports SSE for realtime
        # This is handled separately by the engine runner via bridge SSE endpoint
        logger.info("Kiwoom realtime subscription requested for: %s", symbols)

    async def unsubscribe_realtime(self, symbols: list[str]) -> None:
        await self._client.post("/realtime/unsubscribe", json={"symbols": symbols})
