from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.trade import Trade
from ..schemas.trade import TradeOut, TradeListOut, TradeStats

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=TradeListOut)
async def list_trades(
    symbol: str | None = Query(None),
    strategy_id: str | None = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    q = select(Trade).order_by(desc(Trade.created_at)).limit(limit).offset(offset)
    if symbol:
        q = q.where(Trade.symbol == symbol)
    if strategy_id:
        q = q.where(Trade.strategy_id == strategy_id)

    result = await db.execute(q)
    trades = result.scalars().all()
    return TradeListOut(trades=[TradeOut.model_validate(t) for t in trades], total=len(trades))


@router.get("/stats", response_model=TradeStats)
async def get_trade_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(
        select(
            func.count(Trade.id).label("total"),
            func.sum(
                func.case((Trade.side == "sell", Trade.total_value), else_=0)
            ).label("total_sell_value"),
        )
    )
    row = result.one()
    return TradeStats(total_trades=row.total or 0, total_sell_value=float(row.total_sell_value or 0))
