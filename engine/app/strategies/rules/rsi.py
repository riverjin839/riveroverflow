"""
RSI (Relative Strength Index) Strategy.
BUY when RSI < oversold threshold (과매도).
SELL when RSI > overbought threshold (과매수).
"""
import pandas_ta as ta

from ..base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig


class RSIStrategy(AbstractStrategy):
    """
    Params:
        period (int): RSI period. Default: 14
        oversold (float): Buy threshold. Default: 30
        overbought (float): Sell threshold. Default: 70
    """

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        p = config.params
        self.period: int = int(p.get("period", 14))
        self.oversold: float = float(p.get("oversold", 30.0))
        self.overbought: float = float(p.get("overbought", 70.0))

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        df = snapshot.ohlcv
        if len(df) < self.period + 1:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Not enough data ({len(df)}/{self.period + 1} bars)",
            )

        closes = df["close"].astype(float)
        rsi_series = ta.rsi(closes, length=self.period)
        rsi = float(rsi_series.iloc[-1])

        if rsi < self.oversold:
            # More oversold = higher confidence
            confidence = min((self.oversold - rsi) / self.oversold * 2, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                reason=f"RSI 과매도: {rsi:.1f} < {self.oversold}",
                metadata={"rsi": rsi},
            )

        if rsi > self.overbought:
            # More overbought = higher confidence
            confidence = min((rsi - self.overbought) / (100 - self.overbought) * 2, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                reason=f"RSI 과매수: {rsi:.1f} > {self.overbought}",
                metadata={"rsi": rsi},
            )

        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.HOLD,
            confidence=0.0,
            reason=f"RSI 중립: {rsi:.1f}",
            metadata={"rsi": rsi},
        )
