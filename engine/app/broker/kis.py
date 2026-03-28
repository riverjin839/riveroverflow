"""
한국투자증권 (Korea Investment & Securities) broker implementation.
Uses the python-kis library: https://github.com/Soju06/python-kis
"""
import asyncio
import logging
from datetime import datetime
from decimal import Decimal

try:
    import kis_api as kis  # python-kis
except ImportError as _e:
    raise ImportError("python-kis 패키지가 설치되지 않았습니다. pip install python-kis") from _e

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


class KISBroker(AbstractBroker):
    """한국투자증권 Open API broker."""

    def __init__(self):
        self._kis: kis.KIS | None = None
        self._account = None

    @property
    def name(self) -> str:
        return "KIS"

    async def authenticate(self) -> None:
        """Initialize KIS client with app key/secret."""
        if not settings.kis_app_key or not settings.kis_app_secret:
            raise ValueError("KIS_APP_KEY and KIS_APP_SECRET must be set")

        self._kis = kis.KIS(
            appkey=settings.kis_app_key,
            appsecret=settings.kis_app_secret,
            virtual_account=settings.kis_is_virtual,
        )
        account_no = settings.kis_account_no
        self._account = self._kis.account(account_no)
        logger.info(
            "KIS authenticated (virtual=%s, account=%s)",
            settings.kis_is_virtual,
            account_no,
        )

    async def get_balance(self) -> Balance:
        """잔고 조회."""
        if self._account is None:
            await self.authenticate()

        # python-kis is synchronous; run in executor
        balance_data = await asyncio.get_event_loop().run_in_executor(
            None, self._account.balance
        )

        return Balance(
            total_value=Decimal(str(balance_data.total_evaluation_amount)),
            cash=Decimal(str(balance_data.cash_balance)),
            stock_value=Decimal(str(balance_data.stock_evaluation_amount)),
            profit_loss=Decimal(str(balance_data.total_profit_loss)),
            profit_loss_pct=float(balance_data.total_profit_loss_rate),
        )

    async def get_positions(self) -> list[Position]:
        """보유 종목 조회."""
        if self._account is None:
            await self.authenticate()

        positions_data = await asyncio.get_event_loop().run_in_executor(
            None, self._account.positions
        )

        return [
            Position(
                symbol=p.symbol,
                name=p.name,
                quantity=int(p.quantity),
                avg_price=Decimal(str(p.average_price)),
                current_price=Decimal(str(p.current_price)),
                profit_loss=Decimal(str(p.profit_loss)),
                profit_loss_pct=float(p.profit_loss_rate),
            )
            for p in positions_data
        ]

    async def get_market_price(self, symbol: str) -> MarketPrice:
        """현재가 조회."""
        if self._kis is None:
            await self.authenticate()

        stock = self._kis.stock(symbol)
        price_data = await asyncio.get_event_loop().run_in_executor(
            None, stock.price
        )

        return MarketPrice(
            symbol=symbol,
            name=price_data.name,
            price=Decimal(str(price_data.price)),
            open=Decimal(str(price_data.open)),
            high=Decimal(str(price_data.high)),
            low=Decimal(str(price_data.low)),
            volume=int(price_data.volume),
            change=Decimal(str(price_data.change)),
            change_pct=float(price_data.change_rate),
            timestamp=datetime.utcnow(),
        )

    async def get_ohlcv(
        self, symbol: str, period: str = "D", count: int = 100
    ) -> list[dict]:
        """일봉/주봉/분봉 OHLCV 데이터 조회."""
        if self._kis is None:
            await self.authenticate()

        stock = self._kis.stock(symbol)

        def _fetch():
            if period == "D":
                return stock.daily_chart(count=count)
            elif period == "W":
                return stock.weekly_chart(count=count)
            elif period == "m":
                return stock.minute_chart(count=count)
            else:
                return stock.daily_chart(count=count)

        chart_data = await asyncio.get_event_loop().run_in_executor(None, _fetch)

        return [
            {
                "time": c.date.isoformat(),
                "open": float(c.open),
                "high": float(c.high),
                "low": float(c.low),
                "close": float(c.close),
                "volume": int(c.volume),
            }
            for c in chart_data
        ]

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """주문 실행."""
        if self._account is None:
            await self.authenticate()

        def _place():
            if order.side == OrderSide.BUY:
                if order.order_type == OrderType.MARKET:
                    return self._account.buy(order.symbol, order.quantity)
                else:
                    return self._account.buy(
                        order.symbol, order.quantity, price=int(order.price)
                    )
            else:
                if order.order_type == OrderType.MARKET:
                    return self._account.sell(order.symbol, order.quantity)
                else:
                    return self._account.sell(
                        order.symbol, order.quantity, price=int(order.price)
                    )

        result = await asyncio.get_event_loop().run_in_executor(None, _place)

        return OrderResult(
            order_id=str(result.order_id),
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=order.price or Decimal("0"),
            status=OrderStatus.PENDING,
            filled_at=None,
        )

    async def cancel_order(self, order_id: str) -> bool:
        """주문 취소."""
        if self._account is None:
            await self.authenticate()

        def _cancel():
            return self._account.cancel(order_id)

        result = await asyncio.get_event_loop().run_in_executor(None, _cancel)
        return bool(result)

    async def subscribe_realtime(
        self, symbols: list[str], callback: RealtimeCallback
    ) -> None:
        """실시간 시세 구독 (WebSocket)."""
        if self._kis is None:
            await self.authenticate()

        # python-kis WebSocket subscription
        async def _on_price(event):
            mp = MarketPrice(
                symbol=event.symbol,
                name=event.name,
                price=Decimal(str(event.price)),
                open=Decimal(str(event.open)),
                high=Decimal(str(event.high)),
                low=Decimal(str(event.low)),
                volume=int(event.volume),
                change=Decimal(str(event.change)),
                change_pct=float(event.change_rate),
            )
            await callback(mp)

        for symbol in symbols:
            self._kis.on("price", symbol, _on_price)

        logger.info("KIS realtime subscribed: %s", symbols)

    async def unsubscribe_realtime(self, symbols: list[str]) -> None:
        """실시간 시세 구독 해제."""
        if self._kis:
            for symbol in symbols:
                self._kis.off("price", symbol)
