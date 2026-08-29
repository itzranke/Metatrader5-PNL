"""Schema Phase 8 — Performance score & mutasi dana (deposit/withdrawal)."""
from datetime import datetime

from pydantic import BaseModel, Field


class MoneyCreate(BaseModel):
    amount: float = Field(gt=0)
    ts: datetime | None = None
    method: str = Field(default="bank", max_length=30)
    note: str = Field(default="", max_length=255)


class MoneyOut(BaseModel):
    id: int
    kind: str  # deposit | withdrawal
    amount: float
    ts: datetime
    method: str
    note: str

    model_config = {"from_attributes": True}


class MoneyListOut(BaseModel):
    net_deposits: float
    total_deposits: float
    total_withdrawals: float
    items: list[MoneyOut]


class ScoreComponent(BaseModel):
    weight: int
    sub: float


class ScoreOut(BaseModel):
    score: int | None
    progress: int
    need: int
    label: str | None
    data_complete: bool
    components: dict[str, ScoreComponent] | None
