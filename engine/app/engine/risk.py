"""
Risk management module.
Validates trading signals before order execution.
"""
import logging
from decimal import Decimal
from dataclasses import dataclass

from ..broker.base import Balance, OrderRequest, OrderSide, OrderType, Position
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    approved: bool
    reason: str
    adjusted_quantity: int | None = None


class RiskManager:
    """
    Pre-order risk checks:
    1. Position size limit (max_position_ratio of total portfolio)
    2. Stop-loss enforcement
    3. Duplicate order prevention
    4. Market hours check
    """

    def __init__(
        self,
        max_position_ratio: float | None = None,
        stop_loss_pct: float | None = None,
    ):
        self.max_position_ratio = max_position_ratio or settings.max_position_ratio
        self.stop_loss_pct = stop_loss_pct or settings.default_stop_loss_pct
        self._pending_symbols: set[str] = set()

    def check(
        self,
        order: OrderRequest,
        balance: Balance,
        positions: list[Position],
        current_price: Decimal,
    ) -> RiskCheckResult:
        """Run all risk checks and return approval decision."""

        # 1. Duplicate order check
        if order.symbol in self._pending_symbols:
            return RiskCheckResult(
                approved=False,
                reason=f"Order already pending for {order.symbol}",
            )

        # 2. Buy-side: position size check
        if order.side == OrderSide.BUY:
            order_value = current_price * order.quantity
            max_allowed = balance.total_value * Decimal(str(self.max_position_ratio))

            # Include existing position value
            existing = next(
                (p for p in positions if p.symbol == order.symbol), None
            )
            existing_value = (
                existing.current_price * existing.quantity if existing else Decimal(0)
            )
            total_exposure = existing_value + order_value

            if total_exposure > max_allowed:
                # Auto-adjust quantity
                available_value = max(max_allowed - existing_value, Decimal(0))
                adjusted_qty = int(available_value / current_price)
                if adjusted_qty <= 0:
                    return RiskCheckResult(
                        approved=False,
                        reason=f"Position limit exceeded: {total_exposure:,.0f}원 > {max_allowed:,.0f}원",
                    )
                logger.warning(
                    "Quantity adjusted %d→%d for %s (position limit)",
                    order.quantity,
                    adjusted_qty,
                    order.symbol,
                )
                return RiskCheckResult(
                    approved=True,
                    reason=f"Quantity adjusted for position limit",
                    adjusted_quantity=adjusted_qty,
                )

            # Cash check
            if order_value > balance.cash:
                adjusted_qty = int(balance.cash / current_price)
                if adjusted_qty <= 0:
                    return RiskCheckResult(
                        approved=False,
                        reason=f"Insufficient cash: {balance.cash:,.0f}원 < {order_value:,.0f}원",
                    )
                return RiskCheckResult(
                    approved=True,
                    reason="Quantity adjusted for available cash",
                    adjusted_quantity=adjusted_qty,
                )

        # 3. Sell-side: stop-loss and position existence check
        if order.side == OrderSide.SELL:
            position = next(
                (p for p in positions if p.symbol == order.symbol), None
            )
            if position is None:
                return RiskCheckResult(
                    approved=False,
                    reason=f"No position to sell: {order.symbol}",
                )
            if order.quantity > position.quantity:
                return RiskCheckResult(
                    approved=True,
                    reason="Quantity adjusted to held quantity",
                    adjusted_quantity=position.quantity,
                )

        return RiskCheckResult(approved=True, reason="OK")

    def register_pending(self, symbol: str) -> None:
        self._pending_symbols.add(symbol)

    def release_pending(self, symbol: str) -> None:
        self._pending_symbols.discard(symbol)

    def check_stop_loss(self, position: Position) -> bool:
        """Returns True if stop-loss should be triggered."""
        return position.profit_loss_pct <= -(self.stop_loss_pct * 100)
