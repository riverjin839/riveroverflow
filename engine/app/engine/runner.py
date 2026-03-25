"""
Core trading engine loop.
MarketData → Strategy.evaluate() → Risk.check() → Broker.order() → Redis publish
"""
import asyncio
import json
import logging
from datetime import datetime
from decimal import Decimal

import pandas as pd

from ..broker.base import AbstractBroker, MarketPrice, OrderRequest, OrderSide, OrderType
from ..core.config import settings
from ..core.redis import publish, CHANNEL_TRADES, CHANNEL_MARKET, CHANNEL_PORTFOLIO
from ..strategies.base import AbstractStrategy, MarketSnapshot, SignalType
from .risk import RiskManager

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Main auto-trading engine.
    Manages strategies, subscribes to market data, executes orders.
    """

    def __init__(self, broker: AbstractBroker):
        self._broker = broker
        self._strategies: dict[str, AbstractStrategy] = {}
        self._risk = RiskManager()
        self._running = False
        self._ohlcv_cache: dict[str, pd.DataFrame] = {}

    def add_strategy(self, strategy: AbstractStrategy) -> None:
        self._strategies[strategy.strategy_id] = strategy
        logger.info("Strategy added: %s", strategy)

    def remove_strategy(self, strategy_id: str) -> None:
        self._strategies.pop(strategy_id, None)

    async def start(self) -> None:
        if self._running:
            logger.warning("Engine already running")
            return

        self._running = True
        logger.info("Trading engine starting...")

        await self._broker.authenticate()

        # Subscribe to realtime data for all strategy symbols
        all_symbols = set()
        for strategy in self._strategies.values():
            all_symbols.update(strategy.symbols)

        if all_symbols:
            await self._broker.subscribe_realtime(
                list(all_symbols), self._on_market_data
            )

        # Main evaluation loop
        asyncio.create_task(self._evaluation_loop())

        # Portfolio snapshot publisher
        asyncio.create_task(self._portfolio_loop())

        logger.info("Engine running. Monitoring %d symbols.", len(all_symbols))

    async def stop(self) -> None:
        self._running = False
        all_symbols = set()
        for strategy in self._strategies.values():
            all_symbols.update(strategy.symbols)
        if all_symbols:
            await self._broker.unsubscribe_realtime(list(all_symbols))
        logger.info("Engine stopped.")

    async def _on_market_data(self, price: MarketPrice) -> None:
        """Callback from broker realtime subscription."""
        event = {
            "type": "price",
            "symbol": price.symbol,
            "name": price.name,
            "price": str(price.price),
            "change_pct": price.change_pct,
            "volume": price.volume,
            "time": price.timestamp.isoformat(),
        }
        await publish(CHANNEL_MARKET, json.dumps(event))

    async def _evaluation_loop(self) -> None:
        """Periodic strategy evaluation loop."""
        while self._running:
            try:
                await self._evaluate_all_strategies()
            except Exception as e:
                logger.exception("Evaluation loop error: %s", e)
            await asyncio.sleep(settings.engine_poll_interval_sec)

    async def _evaluate_all_strategies(self) -> None:
        balance = await self._broker.get_balance()
        positions = await self._broker.get_positions()

        for strategy in self._strategies.values():
            if not strategy.config.enabled:
                continue
            for symbol in strategy.symbols:
                try:
                    await self._evaluate_symbol(strategy, symbol, balance, positions)
                except Exception as e:
                    logger.error("Error evaluating %s/%s: %s", strategy.strategy_id, symbol, e)

    async def _evaluate_symbol(
        self, strategy, symbol: str, balance, positions
    ) -> None:
        # Refresh OHLCV cache
        if symbol not in self._ohlcv_cache:
            ohlcv_data = await self._broker.get_ohlcv(symbol, period="D", count=120)
            df = pd.DataFrame(ohlcv_data)
            self._ohlcv_cache[symbol] = df
        else:
            df = self._ohlcv_cache[symbol]

        price_data = await self._broker.get_market_price(symbol)

        snapshot = MarketSnapshot(
            symbol=symbol,
            current_price=float(price_data.price),
            ohlcv=df,
            timestamp=datetime.utcnow(),
        )

        signal = strategy.evaluate(snapshot)

        if not signal.is_actionable:
            return

        if signal.confidence < 0.6:
            logger.debug("Signal confidence too low: %.2f for %s", signal.confidence, symbol)
            return

        logger.info(
            "Signal: %s %s %s (confidence=%.2f, reason=%s)",
            signal.signal_type, symbol, strategy.strategy_id,
            signal.confidence, signal.reason,
        )

        # Determine quantity (simple: use 5% of portfolio per trade)
        trade_value = balance.total_value * Decimal("0.05")
        quantity = max(1, int(trade_value / price_data.price))

        order = OrderRequest(
            symbol=symbol,
            side=OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            strategy_id=strategy.strategy_id,
        )

        # Risk check
        risk_result = self._risk.check(order, balance, positions, price_data.price)
        if not risk_result.approved:
            logger.warning("Order rejected by risk manager: %s", risk_result.reason)
            return

        if risk_result.adjusted_quantity is not None:
            order.quantity = risk_result.adjusted_quantity

        # Execute order
        self._risk.register_pending(symbol)
        try:
            result = await self._broker.place_order(order)
            logger.info("Order placed: %s", result)

            event = {
                "type": "trade",
                "order_id": result.order_id,
                "symbol": symbol,
                "side": order.side.value,
                "quantity": order.quantity,
                "price": str(result.price),
                "strategy_id": strategy.strategy_id,
                "signal_reason": signal.reason,
                "time": datetime.utcnow().isoformat(),
            }
            await publish(CHANNEL_TRADES, json.dumps(event))

        finally:
            self._risk.release_pending(symbol)

    async def _portfolio_loop(self) -> None:
        """Publish portfolio snapshots every 10 seconds."""
        while self._running:
            try:
                balance = await self._broker.get_balance()
                positions = await self._broker.get_positions()
                event = {
                    "type": "portfolio",
                    "total_value": str(balance.total_value),
                    "cash": str(balance.cash),
                    "stock_value": str(balance.stock_value),
                    "profit_loss": str(balance.profit_loss),
                    "profit_loss_pct": balance.profit_loss_pct,
                    "positions": [
                        {
                            "symbol": p.symbol,
                            "name": p.name,
                            "quantity": p.quantity,
                            "avg_price": str(p.avg_price),
                            "current_price": str(p.current_price),
                            "profit_loss": str(p.profit_loss),
                            "profit_loss_pct": p.profit_loss_pct,
                        }
                        for p in positions
                    ],
                    "time": datetime.utcnow().isoformat(),
                }
                await publish(CHANNEL_PORTFOLIO, json.dumps(event))
            except Exception as e:
                logger.error("Portfolio loop error: %s", e)
            await asyncio.sleep(10)
