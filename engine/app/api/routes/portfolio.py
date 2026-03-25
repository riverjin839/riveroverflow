from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated

from ...broker.base import AbstractBroker
from ...broker.kis import KISBroker

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Dependency: get broker instance from app state
def get_broker(request) -> AbstractBroker:
    return request.app.state.broker


@router.get("/balance")
async def get_balance(broker: AbstractBroker = Depends(get_broker)):
    try:
        balance = await broker.get_balance()
        return {
            "total_value": str(balance.total_value),
            "cash": str(balance.cash),
            "stock_value": str(balance.stock_value),
            "profit_loss": str(balance.profit_loss),
            "profit_loss_pct": balance.profit_loss_pct,
            "currency": balance.currency,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Broker error: {e}")


@router.get("/positions")
async def get_positions(broker: AbstractBroker = Depends(get_broker)):
    try:
        positions = await broker.get_positions()
        return [
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
        ]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Broker error: {e}")


@router.get("/market/{symbol}")
async def get_market_price(symbol: str, broker: AbstractBroker = Depends(get_broker)):
    try:
        price = await broker.get_market_price(symbol)
        return {
            "symbol": price.symbol,
            "name": price.name,
            "price": str(price.price),
            "open": str(price.open),
            "high": str(price.high),
            "low": str(price.low),
            "volume": price.volume,
            "change": str(price.change),
            "change_pct": price.change_pct,
            "timestamp": price.timestamp.isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Broker error: {e}")


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    period: str = "D",
    count: int = 100,
    broker: AbstractBroker = Depends(get_broker),
):
    try:
        data = await broker.get_ohlcv(symbol, period=period, count=count)
        return data
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Broker error: {e}")
