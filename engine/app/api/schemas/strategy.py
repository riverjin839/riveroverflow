import json
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, field_validator


class StrategyConfigIn(BaseModel):
    name: str
    strategy_type: str
    symbols: list[str]
    params: dict[str, Any] = {}
    enabled: bool = False
    broker: str = "KIS"


class StrategyConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    strategy_type: str
    symbols: list[str]
    params: dict[str, Any]
    enabled: bool
    broker: str
    created_at: datetime
    updated_at: datetime

    @field_validator("symbols", mode="before")
    @classmethod
    def parse_symbols(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    @field_validator("params", mode="before")
    @classmethod
    def parse_params(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v
