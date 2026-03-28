"""
ML-based strategy base class.
Subclass this to implement LSTM, XGBoost, or other ML models.
"""
from abc import abstractmethod
from pathlib import Path

import numpy as np
import pandas as pd

from ..base import AbstractStrategy, MarketSnapshot, Signal, SignalType, StrategyConfig


class BaseMLStrategy(AbstractStrategy):
    """
    Base class for ML-driven strategies.
    Subclasses implement _predict() to return a probability score.

    Params:
        model_path (str): Path to saved model file
        buy_threshold (float): Probability above which to BUY. Default: 0.65
        sell_threshold (float): Probability below which to SELL. Default: 0.35
        lookback (int): Number of bars to use as features. Default: 20
    """

    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        p = config.params
        self.model_path: str = p.get("model_path", "")
        self.buy_threshold: float = float(p.get("buy_threshold", 0.65))
        self.sell_threshold: float = float(p.get("sell_threshold", 0.35))
        self.lookback: int = int(p.get("lookback", 20))
        self._model = None
        if self.model_path and Path(self.model_path).exists():
            self._load_model()

    @abstractmethod
    def _load_model(self) -> None:
        """Load the trained ML model from disk."""

    @abstractmethod
    def _predict(self, features: np.ndarray) -> float:
        """
        Predict the probability of an upward price move.
        Returns float in [0, 1].
        """

    def _extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """Extract normalized feature vector from OHLCV DataFrame."""
        closes = df["close"].astype(float)
        highs = df["high"].astype(float)
        lows = df["low"].astype(float)
        volumes = df["volume"].astype(float)

        # RSI (14)
        delta = closes.diff()
        gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        rsi = 100 - (100 / (1 + gain / loss.replace(0, float("nan"))))

        # MACD histogram
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - signal_line

        # Bollinger Bands (20, 2σ)
        sma20 = closes.rolling(20).mean()
        std20 = closes.rolling(20).std()
        bb_upper = sma20 + 2 * std20
        bb_lower = sma20 - 2 * std20

        features = pd.DataFrame()
        features["rsi"] = rsi
        features["macd_hist"] = macd_hist
        features["bb_upper"] = bb_upper
        features["bb_lower"] = bb_lower
        features["volume_ratio"] = volumes / volumes.rolling(20).mean()
        features["hl_ratio"] = (highs - lows) / closes
        features["return_1"] = closes.pct_change(1)
        features["return_5"] = closes.pct_change(5)

        return features.dropna().tail(self.lookback).values.flatten()

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        if self._model is None:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason="ML model not loaded",
            )

        if len(snapshot.ohlcv) < self.lookback + 20:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.HOLD,
                confidence=0.0,
                reason=f"Not enough data ({len(snapshot.ohlcv)} bars)",
            )

        features = self._extract_features(snapshot.ohlcv)
        prob = self._predict(features)

        if prob >= self.buy_threshold:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.BUY,
                confidence=prob,
                reason=f"ML 매수 신호: probability={prob:.2f}",
                metadata={"probability": prob},
            )

        if prob <= self.sell_threshold:
            return Signal(
                strategy_id=self.strategy_id,
                symbol=snapshot.symbol,
                signal_type=SignalType.SELL,
                confidence=1.0 - prob,
                reason=f"ML 매도 신호: probability={prob:.2f}",
                metadata={"probability": prob},
            )

        return Signal(
            strategy_id=self.strategy_id,
            symbol=snapshot.symbol,
            signal_type=SignalType.HOLD,
            confidence=0.0,
            reason=f"ML 중립: probability={prob:.2f}",
        )
