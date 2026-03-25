import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.trade import StrategyConfig as StrategyConfigModel
from ..schemas.strategy import StrategyConfigIn, StrategyConfigOut

router = APIRouter(prefix="/strategies", tags=["strategies"])

# Available strategy types
AVAILABLE_STRATEGIES = [
    {"type": "ma_cross", "name": "이동평균 교차", "description": "골든/데드 크로스 전략"},
    {"type": "rsi", "name": "RSI", "description": "과매수/과매도 신호 전략"},
    {"type": "macd", "name": "MACD", "description": "MACD 교차 전략"},
    {"type": "ml_base", "name": "ML 기반", "description": "머신러닝 예측 전략 (모델 필요)"},
]


@router.get("/available")
async def list_available_strategies():
    return AVAILABLE_STRATEGIES


@router.get("", response_model=list[StrategyConfigOut])
async def list_strategies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(StrategyConfigModel))
    configs = result.scalars().all()
    return [StrategyConfigOut.model_validate(c) for c in configs]


@router.post("", response_model=StrategyConfigOut, status_code=201)
async def create_strategy(body: StrategyConfigIn, db: AsyncSession = Depends(get_db)):
    config = StrategyConfigModel(
        name=body.name,
        strategy_type=body.strategy_type,
        symbols=json.dumps(body.symbols),
        params=json.dumps(body.params),
        enabled=body.enabled,
        broker=body.broker,
    )
    db.add(config)
    await db.flush()
    await db.refresh(config)
    return StrategyConfigOut.model_validate(config)


@router.put("/{strategy_id}/toggle", response_model=StrategyConfigOut)
async def toggle_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StrategyConfigModel).where(StrategyConfigModel.id == strategy_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Strategy not found")
    config.enabled = not config.enabled
    await db.flush()
    return StrategyConfigOut.model_validate(config)


@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StrategyConfigModel).where(StrategyConfigModel.id == strategy_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.delete(config)
