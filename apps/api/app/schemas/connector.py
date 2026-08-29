"""Schemas Phase 4 — Connector pairing, heartbeat & sync (BLUEPRINT §8)."""
from datetime import datetime

from pydantic import BaseModel, Field


class PairRequestOut(BaseModel):
    device_id: int
    code: str
    expires_at: datetime


class PairIn(BaseModel):
    code: str = Field(min_length=4, max_length=16)
    client_id: str = Field(min_length=8, max_length=64)
    device_name: str = Field(default="", max_length=100)
    version: str = Field(default="", max_length=20)


class PairOut(BaseModel):
    device_id: int
    device_key: str  # hanya dikembalikan sekali — server simpan hash


class HeartbeatOut(BaseModel):
    ok: bool
    server_time: datetime


class DealIn(BaseModel):
    deal_ticket: str = Field(min_length=1, max_length=64)
    order_ticket: str = Field(min_length=1, max_length=64)
    time: datetime
    type: int
    symbol: str = Field(min_length=1, max_length=32)
    volume: float
    price: float
    profit: float = 0
    swap: float = 0
    commission: float = 0
    comment: str = Field(default="", max_length=255)
    external_id: str | None = Field(default=None, max_length=128)


class PositionIn(BaseModel):
    ticket: str = Field(min_length=1, max_length=64)
    symbol: str = Field(min_length=1, max_length=32)
    side: str = Field(pattern="^(buy|sell)$")
    volume: float
    open_price: float
    open_time: datetime
    current_price: float | None = None
    floating_pnl: float | None = None
    sl: float | None = None
    tp: float | None = None


class ExcursionIn(BaseModel):
    """MAE/MFE dari connector (BLUEPRINT §14) — pts = pergerakan harga simbol."""

    ticket: str = Field(min_length=1, max_length=64)
    mae_pts: float = Field(ge=0)
    mfe_pts: float = Field(ge=0)
    mae_currency: float | None = Field(default=None)
    mfe_currency: float | None = Field(default=None)
    samples: int = Field(default=1, ge=0)


class SyncIn(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    server: str = Field(min_length=1, max_length=100)
    kind: str = Field(default="full", pattern="^(full|incremental)$")
    last_ticket: str | None = Field(default=None, max_length=64)
    deals: list[DealIn] = Field(default_factory=list, max_length=500)
    positions: list[PositionIn] = Field(default_factory=list)
    excursions: list[ExcursionIn] = Field(default_factory=list)





class SyncOut(BaseModel):
    accepted: int
    duplicates: int
    closed_positions: int
    last_ticket: str | None
    state: str


class DeviceOut(BaseModel):
    id: int
    device_name: str
    state: str
    version: str
    last_seen_at: datetime | None
    created_at: datetime
    accounts: list[str] = Field(default_factory=list)  # "login@server (state)"

    model_config = {"from_attributes": True}
