"""Core models — Phase 1 (BLUEPRINT §9, KEPUTUSAN-FINAL §5).

Cakupan fase ini: users, sessions, roles/permissions (RBAC), brokers,
trading_accounts, mt5_connections, connector_devices.
Tabel trades/journal/analytics dst. ditambahkan di fase berikutnya via Alembic.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
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

    sessions: Mapped[list[Session]] = relationship(
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


# ---------------------------------------------------------------- connector


class ConnectorDevice(TimestampMixin, Base):
    __tablename__ = "connector_devices"
    __table_args__ = (Index("ix_devices_user", "user_id"),)
    id: Mapped[int] = mapped_column(BIGINT, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_name: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    device_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # argon2 hash
    client_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
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
