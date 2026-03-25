"""
Moving Average Crossover Strategy.
BUY signal when short MA crosses above long MA (골든크로스).
SELL signal when short MA crosses below long MA (데드크로스).
"""
from ..base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig


class MACrossStrategy(AbstractStrategy):
    """
    Params:
        short_period (int): Short MA period. Default: 5
        long_period (int): Long MA period. Default: 20
        min_confidence (float): Minimum confidence threshold. Default: 0.6
    """

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        p = config.params
        self.short_period: int = int(p.get("short_period", 5))
        self.long_period: int = int(p.get("long_period", 20))
        self.min_confidence: float = float(p.get("min_confidence", 0.6))

        # State for crossover detection (previous values)
        self._prev_short: dict[str, float] = {}
        self._prev_long: dict[str, float] = {}

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        df = snapshot.ohlcv
        if len(df) < self.long_period:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Not enough data ({len(df)}/{self.long_period} bars)",
            )

        closes = df["close"].astype(float)
        short_ma = closes.rolling(self.short_period).mean().iloc[-1]
        long_ma = closes.rolling(self.long_period).mean().iloc[-1]

        prev_short = self._prev_short.get(snapshot.symbol)
        prev_long = self._prev_long.get(snapshot.symbol)

        self._prev_short[snapshot.symbol] = short_ma
        self._prev_long[snapshot.symbol] = long_ma

        if prev_short is None or prev_long is None:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason="Initializing MA crossover state",
            )

        # Golden cross: short MA crosses ABOVE long MA
        if prev_short <= prev_long and short_ma > long_ma:
            spread_pct = abs(short_ma - long_ma) / long_ma
            confidence = min(0.5 + spread_pct * 10, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                reason=f"골든크로스 MA{self.short_period}({short_ma:.0f}) > MA{self.long_period}({long_ma:.0f})",
                metadata={"short_ma": short_ma, "long_ma": long_ma},
            )

        # Dead cross: short MA crosses BELOW long MA
        if prev_short >= prev_long and short_ma < long_ma:
            spread_pct = abs(short_ma - long_ma) / long_ma
            confidence = min(0.5 + spread_pct * 10, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                reason=f"데드크로스 MA{self.short_period}({short_ma:.0f}) < MA{self.long_period}({long_ma:.0f})",
                metadata={"short_ma": short_ma, "long_ma": long_ma},
            )

        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.HOLD,
            confidence=0.0,
            reason=f"MA{self.short_period}={short_ma:.0f}, MA{self.long_period}={long_ma:.0f}",
        )
