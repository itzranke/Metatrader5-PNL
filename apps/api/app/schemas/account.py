"""Schemas akun trading (BLUEPRINT §20 — /accounts, /meta)."""
from datetime import datetime

from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    login: str | None = Field(default=None, max_length=50)
    server: str | None = Field(default=None, max_length=100)
    kind: str = "mt5"  # mt5 | demo
    currency: str = "USD"
    leverage: int | None = None
    broker_tz: int = 0  # offset menit dari UTC


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None
    currency: str | None = Field(default=None, max_length=10)
    leverage: int | None = None
    broker_tz: int | None = None


class AccountOut(BaseModel):
    id: int
    name: str
    login: str
    server: str
    kind: str
    currency: str
    leverage: int | None
    broker_tz: int
    hf_preset: bool
    is_active: bool
    created_at: datetime
    connection_state: str | None = None
    last_synced_at: datetime | None = None

    model_config = {"from_attributes": True}


class BrokerPresetOut(BaseModel):
    name: str
    login: str
    server: str
