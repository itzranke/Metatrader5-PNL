"""Schema Phase 6 — Jurnal trading, tags, screenshot."""
from datetime import datetime

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    trading_account_id: int
    trade_id: int | None = None
    entry_date: datetime
    setup: str = Field(default="", max_length=100)
    emotion_before: str = Field(default="", max_length=30)
    emotion_during: str = Field(default="", max_length=30)
    emotion_after: str = Field(default="", max_length=30)
    confidence: int = Field(default=3, ge=1, le=5)
    fear: bool = False
    greed: bool = False
    revenge: bool = False
    fomo: bool = False
    boredom: bool = False
    discipline: int = Field(default=3, ge=1, le=5)
    rule_adherence: bool = True
    reason_entry: str = Field(default="", max_length=255)
    reason_exit: str = Field(default="", max_length=255)
    notes: str = Field(default="", max_length=2000)
    lesson: str = Field(default="", max_length=1000)
    plan_match: bool | None = None
    tags: list[str] = Field(default_factory=list, max_length=10)


class JournalUpdate(BaseModel):
    setup: str | None = Field(default=None, max_length=100)
    emotion_before: str | None = Field(default=None, max_length=30)
    emotion_during: str | None = Field(default=None, max_length=30)
    emotion_after: str | None = Field(default=None, max_length=30)
    confidence: int | None = Field(default=None, ge=1, le=5)
    fear: bool | None = None
    greed: bool | None = None
    revenge: bool | None = None
    fomo: bool | None = None
    boredom: bool | None = None
    discipline: int | None = Field(default=None, ge=1, le=5)
    rule_adherence: bool | None = None
    reason_entry: str | None = Field(default=None, max_length=255)
    reason_exit: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    lesson: str | None = Field(default=None, max_length=1000)
    plan_match: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=10)


class JournalOut(BaseModel):
    id: int
    trading_account_id: int
    trade_id: int | None
    entry_date: datetime
    setup: str
    emotion_before: str
    emotion_during: str
    emotion_after: str
    confidence: int
    fear: bool
    greed: bool
    revenge: bool
    fomo: bool
    boredom: bool
    discipline: int
    rule_adherence: bool
    reason_entry: str
    reason_exit: str
    notes: str
    lesson: str
    plan_match: bool | None
    screenshot_path: str | None
    tags: list[str] = Field(default_factory=list)
    trade_symbol: str | None = None
    trade_net_profit: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#2dd4a7", max_length=20)


class TagOut(BaseModel):
    id: int
    name: str
    color: str

    model_config = {"from_attributes": True}
