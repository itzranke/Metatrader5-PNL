"""Schema Phase 5 — Dashboard & analytics responses."""
from datetime import datetime

from pydantic import BaseModel


class OverviewOut(BaseModel):
    account_id: int
    account_name: str
    currency: str
    days: int
    balance: float | None = None
    equity: float | None = None
    open_positions: int = 0
    floating_pnl: float = 0
    today_pnl: float = 0
    month_pnl: float = 0
    summary: dict  # dari packages.analytics.summarize


class EquityPoint(BaseModel):
    ts: datetime
    equity: float


class CalendarDay(BaseModel):
    day: str
    net_profit: float
    trades: int
    wins: int


class TradeOut(BaseModel):
    id: int
    ticket: str
    symbol: str
    side: str
    volume: float
    open_price: float
    close_price: float
    open_time: datetime
    close_time: datetime
    net_profit: float
    gross_profit: float
    swap: float
    commission: float
    r_multiple: float | None
    source: str

    model_config = {"from_attributes": True}


class TradesPage(BaseModel):
    total: int
    offset: int
    items: list[TradeOut]


class MonthlyStatOut(BaseModel):
    month: str
    total_trades: int
    win_count: int
    loss_count: int
    net_profit: float
    win_rate: float | None
    profit_factor: float | None


class PositionOut(BaseModel):
    ticket: str
    symbol: str
    side: str
    volume: float
    open_price: float
    open_time: datetime
    current_price: float | None
    floating_pnl: float | None

    model_config = {"from_attributes": True}


class AccountOverviewAggregate(BaseModel):
    accounts: int
    net_profit_total: float
    open_positions: int
    floating_pnl: float
