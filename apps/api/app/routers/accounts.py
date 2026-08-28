"""Phase 3 — Trading Accounts (BLUEPRINT §20, KEPUTUSAN-FINAL DR-03/DR-17).

- GET /accounts — daftar akun user + status koneksi
- POST /accounts — buat akun MT5 (quota 2/user) atau akun demo "Data Contoh"
- PATCH /accounts/:id · DELETE /accounts/:id (soft delete, tenant-scoped)
- GET /meta/broker-presets — preset "Isi Akun Demo HF Markets"
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.schemas.account import AccountCreate, AccountOut, AccountUpdate, BrokerPresetOut
from apps.api.app.services.demo import generate_demo_account
from packages.config import get_settings
from packages.db import get_session
from packages.db.models import Broker, TradingAccount, User

router = APIRouter(tags=["accounts"])

# Preset tombol "Isi Akun Demo HF Markets" (password diisi user sendiri)
HF_PRESETS = [{"name": "HF Markets Demo", "login": "49155931", "server": "HFMarketsGlobal-Demo"}]


def _to_out(acc: TradingAccount) -> AccountOut:
    out = AccountOut.model_validate(acc)
    if acc.connection is not None:
        out.connection_state = acc.connection.state
        out.last_synced_at = acc.connection.last_synced_at
    return out


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    rows = db.scalars(
        select(TradingAccount)
        .where(TradingAccount.user_id == user.id, TradingAccount.deleted_at.is_(None))
        .order_by(TradingAccount.created_at.desc())
    ).all()
    return [_to_out(acc) for acc in rows]


@router.post("/accounts", status_code=201, response_model=AccountOut)
def create_account(
    body: AccountCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if body.kind == "demo":
        existing = db.scalar(
            select(TradingAccount).where(
                TradingAccount.user_id == user.id,
                TradingAccount.kind == "demo",
                TradingAccount.deleted_at.is_(None),
            )
        )
        if existing is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Akun Data Contoh sudah ada")
        acc = generate_demo_account(db, user.id, name=body.name or "Data Contoh")
        db.commit()
        db.refresh(acc)
        return _to_out(acc)

    # akun MT5 asli
    if not body.login or not body.server:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "login dan server wajib diisi")
    settings = get_settings()
    count = db.scalar(
        select(func.count())
        .select_from(TradingAccount)
        .where(TradingAccount.user_id == user.id, TradingAccount.kind == "mt5", TradingAccount.deleted_at.is_(None))
    )
    if count >= settings.max_accounts_per_user:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Batas {settings.max_accounts_per_user} akun MT5 per user tercapai",
        )
    exists = db.scalar(
        select(TradingAccount).where(
            TradingAccount.login == body.login,
            TradingAccount.server == body.server,
            TradingAccount.deleted_at.is_(None),
        )
    )
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Akun dengan login/server ini sudah terdaftar")

    acc = TradingAccount(
        user_id=user.id,
        name=body.name or f"{body.login}@{body.server}",
        login=body.login,
        server=body.server,
        kind="mt5",
        currency=body.currency or "USD",
        leverage=body.leverage,
        broker_tz=body.broker_tz or 0,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return _to_out(acc)


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(
    account_id: int,
    body: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(acc, field, value)
    db.commit()
    db.refresh(acc)
    return _to_out(acc)


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    acc.deleted_at = datetime.now(timezone.utc)
    if acc.connection is not None:
        db.delete(acc.connection)  # putuskan koneksi
    db.commit()


@router.get("/meta/broker-presets", response_model=list[BrokerPresetOut])
def broker_presets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Tombol 'Isi Akun Demo HF Markets' — isi login+server, password diisi user."""
    presets = [BrokerPresetOut(**p) for p in HF_PRESETS]
    rows = db.scalars(select(Broker).order_by(Broker.popularity.desc())).all()
    for b in rows:
        if not any(p.server == b.server for p in presets):
            presets.append(BrokerPresetOut(name=b.name, login="", server=b.server))
    return presets
