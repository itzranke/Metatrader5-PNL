"""Core models — Phase 1 (BLUEPRINT §9, KEPUTUSAN-FINAL §5).

Cakupan fase ini: users, sessions, roles/permissions (RBAC), brokers,
trading_accounts, mt5_connections, connector_devices.
Tabel trades/journal/analytics dst. ditambahkan di fase berikutnya via Alembic.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.db import Base

# PK: BIGSERIAL di PostgreSQL, INTEGER (autoincrement) di SQLite (test/CI)
BIGINT = BigInteger().with_variant(Integer, "sqlite")

# ---------------------------------------------------------------- mixins


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- RBAC

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BIGINT, ForeignKey("users.id"), primary_key=True),
    Column("role_id", BIGINT, ForeignKey("roles.id"), primary_key=True),
)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


# ---------------------------------------------------------------- users


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    session_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    twofa_secret: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)  # user|admin
    locale: Mapped[str] = mapped_column(String(10), default="id", nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    auth_tokens: Mapped[list[AuthToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    accounts: Mapped[list[TradingAccount]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[list[ConnectorDevice]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    roles_m2m: Mapped[list[Role]] = relationship(secondary=user_roles)


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_user", "user_id"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")


# ---------------------------------------------------------------- broker & accounts


class Broker(Base):
    __tablename__ = "brokers"
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    server: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    popularity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class TradingAccount(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "trading_accounts"
    __table_args__ = (
        UniqueConstraint("login", "server", name="uq_account_login_server"),
        Index("ix_accounts_user_active", "user_id", "is_active"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    broker_id: Mapped[int | None] = mapped_column(ForeignKey("brokers.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    login: Mapped[str] = mapped_column(String(50), nullable=False)
    server: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="mt5", nullable=False)  # mt5|demo|manual
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    leverage: Mapped[int | None] = mapped_column(Integer)
    broker_tz: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # offset menit dari UTC
    hf_preset: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="accounts")
    connection: Mapped[MT5Connection | None] = relationship(
        back_populates="account", uselist=False, cascade="all, delete-orphan"
    )


class AuthToken(TimestampMixin, Base):
    """Token sekali pakai: verifikasi email & reset password (hash, TTL)."""
    __tablename__ = "auth_tokens"
    __table_args__ = (Index("ix_auth_tokens_user_kind", "user_id", "kind"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # verify_email | reset_password
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="auth_tokens")


# ---------------------------------------------------------------- connector


class ConnectorDevice(TimestampMixin, Base):
    __tablename__ = "connector_devices"
    __table_args__ = (Index("ix_devices_user", "user_id"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    device_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # argon2 hash
    client_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    pairing_code_hash: Mapped[str | None] = mapped_column(String(255))
    pairing_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(45), default="", nullable=False)
    state: Mapped[str] = mapped_column(
        String(20), default="DISCONNECTED", nullable=False
    )  # §8.7 state machine
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="devices")
    connections: Mapped[list[MT5Connection]] = relationship(
        back_populates="device", cascade="all, delete-orphan"
    )


class MT5Connection(TimestampMixin, Base):
    __tablename__ = "mt5_connections"
    __table_args__ = (Index("ix_connections_state", "state"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(
        ForeignKey("trading_accounts.id"), unique=True, nullable=False
    )
    connector_device_id: Mapped[int] = mapped_column(
        ForeignKey("connector_devices.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(String(20), default="DISCONNECTED", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_deal_ticket: Mapped[str | None] = mapped_column(String(64))  # sync inkremental
    last_error: Mapped[str | None] = mapped_column(String(500))

    account: Mapped[TradingAccount] = relationship(back_populates="connection")
    device: Mapped[ConnectorDevice] = relationship(back_populates="connections")


# ---------------------------------------------------------------- trading data


class Trade(TimestampMixin, SoftDeleteMixin, Base):
    """Posisi tertutup — 1 baris = 1 round-trip (Phase 3: akun demo)."""
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "ticket", name="uq_trade_account_ticket"),
        Index("ix_trades_account_close_time", "trading_account_id", "close_time"),
        Index("ix_trades_account_symbol", "trading_account_id", "symbol"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ticket: Mapped[str] = mapped_column(String(64), nullable=False)  # deal in
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy | sell
    volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    net_profit: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    gross_profit: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    swap: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    commission: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    mae: Mapped[float | None] = mapped_column(Numeric(20, 8))  # ekskursi merugikan maks (currency)
    mfe: Mapped[float | None] = mapped_column(Numeric(20, 8))
    mae_pct: Mapped[float | None]
    mfe_pct: Mapped[float | None]
    r_multiple: Mapped[float | None]
    risk_amount: Mapped[float | None] = mapped_column(Numeric(20, 8))
    source: Mapped[str] = mapped_column(String(10), default="sync", nullable=False)  # sync|manual
    partial_closes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Deal(TimestampMixin, Base):
    """Deal mentah MT5 (audit + partial close)."""
    __tablename__ = "deals"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "deal_ticket", name="uq_deal_account_ticket"),
        Index("ix_deals_account_time", "trading_account_id", "time"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    deal_ticket: Mapped[str] = mapped_column(String(64), nullable=False)
    order_ticket: Mapped[str] = mapped_column(String(64), nullable=False)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 buy,1 sell,2 buy_close,3 sell_close
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    swap: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    commission: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    comment: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128))


class Position(Base):
    """Posisi terbuka (snapshot live dari connector / demo)."""
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "ticket", name="uq_position_account_ticket"),
        Index("ix_positions_account", "trading_account_id"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ticket: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Numeric(20, 8))
    floating_pnl: Mapped[float | None] = mapped_column(Numeric(20, 8))
    sl: Mapped[float | None] = mapped_column(Numeric(20, 8))
    tp: Mapped[float | None] = mapped_column(Numeric(20, 8))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ---------------------------------------------------------------- snapshots & statistics


class EquitySnapshot(TimestampMixin, Base):
    __tablename__ = "equity_snapshots"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "ts", name="uq_equity_account_ts"),
        Index("ix_equity_account_ts", "trading_account_id", "ts"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    comment: Mapped[str] = mapped_column(String(100), default="", nullable=False)


class BalanceSnapshot(TimestampMixin, Base):
    __tablename__ = "balance_snapshots"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "ts", name="uq_balance_account_ts"),
        Index("ix_balance_account_ts", "trading_account_id", "ts"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    comment: Mapped[str] = mapped_column(String(100), default="", nullable=False)


class DailyStatistic(TimestampMixin, Base):
    """Agregasi per hari — cache analytics (BLUEPRINT §12)."""
    __tablename__ = "daily_statistics"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "day", name="uq_daily_account_day"),
        Index("ix_daily_account_day", "trading_account_id", "day"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loss_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    be_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    gross_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    gross_loss: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    win_rate: Mapped[float | None]
    profit_factor: Mapped[float | None]
    max_drawdown: Mapped[float | None]
    expectancy: Mapped[float | None]
    best_trade: Mapped[float | None] = mapped_column(Numeric(20, 8))
    worst_trade: Mapped[float | None] = mapped_column(Numeric(20, 8))
    avg_win: Mapped[float | None] = mapped_column(Numeric(20, 8))
    avg_loss: Mapped[float | None] = mapped_column(Numeric(20, 8))
    r_sum: Mapped[float | None]
    score: Mapped[float | None]
    recalculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MonthlyStatistic(TimestampMixin, Base):
    __tablename__ = "monthly_statistics"
    __table_args__ = (
        UniqueConstraint("trading_account_id", "month", name="uq_monthly_account_month"),
        Index("ix_monthly_account_month", "trading_account_id", "month"),
    )
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # tanggal 1 bulan tsb
    total_trades: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    win_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    loss_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    gross_profit: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    gross_loss: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    win_rate: Mapped[float | None]
    profit_factor: Mapped[float | None]
    max_drawdown: Mapped[float | None]
    recalculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------- journal & psychology


class JournalEntry(TimestampMixin, Base):
    """Jurnal per trade — inti fitur jurnal (notes/setup/emosi/tag)."""
    __tablename__ = "journal_entries"
    __table_args__ = (Index("ix_journal_user_date", "user_id", "entry_date"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"))
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    setup: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    emotion_before: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    emotion_during: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    emotion_after: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1–5
    fear: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    greed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revenge: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fomo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    boredom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    discipline: Mapped[int] = mapped_column(Integer, default=3, nullable=False)  # 1–5
    rule_adherence: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason_entry: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    reason_exit: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    notes: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    lesson: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    plan_match: Mapped[bool | None]

    tags_m2m: Mapped[list[Tag]] = relationship(
        secondary="trade_tags", back_populates="journal_m2m"
    )


class Tag(Base):
    """Katalog tag milik user."""
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#2dd4a7", nullable=False)

    journal_m2m: Mapped[list[JournalEntry]] = relationship(
        secondary="trade_tags", back_populates="tags_m2m"
    )


trade_tags = Table(
    "trade_tags",
    Base.metadata,
    Column("journal_entry_id", BIGINT, ForeignKey("journal_entries.id"), primary_key=True),
    Column("tag_id", BIGINT, ForeignKey("tags.id"), primary_key=True),
)


class PsychologyEntry(TimestampMixin, Base):
    """Tracker psikologi — bebas atau terkait jurnal."""
    __tablename__ = "psychology_entries"
    __table_args__ = (Index("ix_psychology_user_ts", "user_id", "ts"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int | None] = mapped_column(ForeignKey("trading_accounts.id"))
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mood: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    focus: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    notes: Mapped[str] = mapped_column(String(1000), default="", nullable=False)


# ---------------------------------------------------------------- dana


class Deposit(TimestampMixin, Base):
    __tablename__ = "deposits"
    __table_args__ = (Index("ix_deposits_account", "trading_account_id"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)


class Withdrawal(TimestampMixin, Base):
    __tablename__ = "withdrawals"
    __table_args__ = (Index("ix_withdrawals_account", "trading_account_id"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    trading_account_id: Mapped[int] = mapped_column(ForeignKey("trading_accounts.id"), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="", nullable=False)
