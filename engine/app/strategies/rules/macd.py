"""
MACD (Moving Average Convergence Divergence) Strategy.
BUY when MACD line crosses above Signal line.
SELL when MACD line crosses below Signal line.
"""
import pandas_ta as ta

from ..base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig


class MACDStrategy(AbstractStrategy):
    """
    Params:
        fast (int): Fast EMA period. Default: 12
        slow (int): Slow EMA period. Default: 26
        signal (int): Signal EMA period. Default: 9
    """

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        p = config.params
        self.fast: int = int(p.get("fast", 12))
        self.slow: int = int(p.get("slow", 26))
        self.signal_period: int = int(p.get("signal", 9))

        self._prev_macd: dict[str, float] = {}
        self._prev_signal: dict[str, float] = {}

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        df = snapshot.ohlcv
        min_bars = self.slow + self.signal_period
        if len(df) < min_bars:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Not enough data ({len(df)}/{min_bars} bars)",
            )

        closes = df["close"].astype(float)
        macd_df = ta.macd(closes, fast=self.fast, slow=self.slow, signal=self.signal_period)

        if macd_df is None or macd_df.empty:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason="MACD calculation failed",
            )

        macd_col = f"MACD_{self.fast}_{self.slow}_{self.signal_period}"
        sig_col = f"MACDs_{self.fast}_{self.slow}_{self.signal_period}"
        hist_col = f"MACDh_{self.fast}_{self.slow}_{self.signal_period}"

        macd_val = float(macd_df[macd_col].iloc[-1])
        sig_val = float(macd_df[sig_col].iloc[-1])
        hist_val = float(macd_df[hist_col].iloc[-1])

        prev_macd = self._prev_macd.get(snapshot.symbol)
        prev_sig = self._prev_signal.get(snapshot.symbol)

        self._prev_macd[snapshot.symbol] = macd_val
        self._prev_signal[snapshot.symbol] = sig_val

        if prev_macd is None or prev_sig is None:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason="Initializing MACD state",
            )

        # MACD crosses above signal line → BUY
        if prev_macd <= prev_sig and macd_val > sig_val:
            confidence = min(abs(hist_val) / 500 + 0.5, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                reason=f"MACD 상향돌파: MACD={macd_val:.2f}, Signal={sig_val:.2f}",
                metadata={"macd": macd_val, "signal": sig_val, "histogram": hist_val},
            )

        # MACD crosses below signal line → SELL
        if prev_macd >= prev_sig and macd_val < sig_val:
            confidence = min(abs(hist_val) / 500 + 0.5, 1.0)
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                reason=f"MACD 하향돌파: MACD={macd_val:.2f}, Signal={sig_val:.2f}",
                metadata={"macd": macd_val, "signal": sig_val, "histogram": hist_val},
            )

        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.HOLD,
            confidence=0.0,
            reason=f"MACD={macd_val:.2f}, Signal={sig_val:.2f}",
        )
