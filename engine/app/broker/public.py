"""
PublicBroker: pykrx 기반 공공 데이터 브로커.
한국거래소(KRX) 공공 API를 사용하므로 인증 불필요.
시세 조회/OHLCV만 지원; 주문 기능 없음 (개발/데모 전용).
"""
import asyncio
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

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

logger = logging.getLogger(__name__)


class PublicBroker(AbstractBroker):
    """pykrx 기반 KRX 공공 데이터 브로커 (인증 불필요, 읽기 전용)."""

    @property
    def name(self) -> str:
        return "PublicKRX"

    async def authenticate(self) -> None:
        pass  # 인증 불필요

    async def get_ohlcv(
        self,
        symbol: str,
        period: str = "D",
        count: int = 100,
    ) -> list[dict]:
        from pykrx import stock as krx

        end = date.today()
        # 거래일 기준 count봉 확보를 위해 달력일 기준 2배 요청
        start = end - timedelta(days=count * 2)

        def _fetch():
            df = krx.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                symbol,
            )
            return df.tail(count)

        df = await asyncio.get_event_loop().run_in_executor(None, _fetch)

        if df is None or df.empty:
            return []

        return [
            {
                "time": str(idx.date()),
                "open": float(row["시가"]),
                "high": float(row["고가"]),
                "low": float(row["저가"]),
                "close": float(row["종가"]),
                "volume": int(row["거래량"]),
            }
            for idx, row in df.iterrows()
        ]

    async def get_market_price(self, symbol: str) -> MarketPrice:
        from pykrx import stock as krx

        def _fetch_name():
            return krx.get_market_ticker_name(symbol)

        def _fetch_ohlcv():
            end = date.today()
            start = end - timedelta(days=10)
            return krx.get_market_ohlcv_by_date(
                start.strftime("%Y%m%d"),
                end.strftime("%Y%m%d"),
                symbol,
            )

        name, df = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(None, _fetch_name),
            asyncio.get_event_loop().run_in_executor(None, _fetch_ohlcv),
        )

        if df is None or df.empty:
            raise RuntimeError(f"{symbol} 시세 데이터를 가져올 수 없습니다.")

        row = df.iloc[-1]
        prev_close = float(df.iloc[-2]["종가"]) if len(df) >= 2 else float(row["종가"])
        current = float(row["종가"])
        change = current - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        return MarketPrice(
            symbol=symbol,
            name=name or symbol,
            price=Decimal(str(current)),
            open=Decimal(str(row["시가"])),
            high=Decimal(str(row["고가"])),
            low=Decimal(str(row["저가"])),
            volume=int(row["거래량"]),
            change=Decimal(str(round(change, 2))),
            change_pct=round(change_pct, 2),
            timestamp=datetime.utcnow(),
        )

    async def get_balance(self) -> Balance:
        return Balance(
            total_value=Decimal("0"),
            cash=Decimal("0"),
            stock_value=Decimal("0"),
            profit_loss=Decimal("0"),
            profit_loss_pct=0.0,
        )

    async def get_positions(self) -> list[Position]:
        return []

    async def place_order(self, order: OrderRequest) -> OrderResult:
        raise NotImplementedError("PublicBroker는 주문 기능을 지원하지 않습니다.")

    async def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError("PublicBroker는 주문 기능을 지원하지 않습니다.")

    async def subscribe_realtime(
        self, symbols: list[str], callback: RealtimeCallback
    ) -> None:
        pass  # 실시간 미지원

    async def unsubscribe_realtime(self, symbols: list[str]) -> None:
        pass
