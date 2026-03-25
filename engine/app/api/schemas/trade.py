from datetime import datetime
from pydantic import BaseModel, ConfigDict


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    symbol: str
    name: str | None
    side: str
    order_type: str
    quantity: int
    price: float
    total_value: float
    status: str
    strategy_id: str | None
    broker: str
    signal_reason: str | None
    created_at: datetime
    filled_at: datetime | None


class TradeListOut(BaseModel):
    trades: list[TradeOut]
    total: int


class TradeStats(BaseModel):
    total_trades: int
    total_sell_value: float
