"""Phase 8 — Mutasi dana (deposit/withdrawal) + performance score.

Deposit/withdrawal: BLUEPRINT §32 Phase 2 ("melengkapi laporan").
Score: BLUEPRINT §13 (bobot komponen + penalti data, lihat analytics).
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.schemas.score import MoneyCreate, MoneyListOut, MoneyOut, ScoreOut
from packages.analytics import performance_score
from packages.db import get_session
from packages.db.models import (
    Deposit,
    JournalEntry,
    Trade,
    TradingAccount,
    User,
    Withdrawal,
)

router = APIRouter(tags=["score", "money"])


def _account_or_404(db: Session, account_id: int, user: User) -> TradingAccount:
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    return acc


def _money_out(row, kind: str) -> MoneyOut:
    return MoneyOut(
        id=row.id, kind=kind, amount=float(row.amount), ts=row.ts, method=row.method, note=row.note
    )


@router.get("/accounts/{account_id}/score", response_model=ScoreOut)
def account_score(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Skor performa 0–100 (BLUEPRINT §13)."""
    _account_or_404(db, account_id, user)
    trades = db.scalars(
        select(Trade).where(
            Trade.trading_account_id == account_id,
            Trade.deleted_at.is_(None),
        )
    ).all()
    trade_dicts = [
        {
            "net_profit": float(t.net_profit or 0),
            "gross_profit": float(t.gross_profit or 0),
            "open_time": t.open_time,
            "close_time": t.close_time,
            "r_multiple": float(t.r_multiple) if t.r_multiple is not None else None,
            "mae": float(t.mae) if t.mae is not None else None,
            "mfe": float(t.mfe) if t.mfe is not None else None,
        }
        for t in trades
    ]
    journals = db.scalars(
        select(JournalEntry).where(JournalEntry.trading_account_id == account_id)
    ).all()
    n_j = len(journals)
    if n_j:
        plan_match = sum(1 for j in journals if j.plan_match is True)
        adherence = sum(1 for j in journals if j.rule_adherence)
        revenge = sum(1 for j in journals if j.revenge)
        stable = sum(
            1 for j in journals if not (j.fear or j.greed or j.revenge or j.fomo or j.boredom)
        )
        result = performance_score(
            trade_dicts,
            plan_match_rate=plan_match / n_j,
            rule_adherence_rate=adherence / n_j,
            revenge_ratio=revenge / n_j,
            emotion_stability=stable / n_j,
            journal_count=n_j,
        )
    else:
        result = performance_score(trade_dicts, journal_count=0)
    return ScoreOut(**result)


@router.get("/accounts/{account_id}/money", response_model=MoneyListOut)
def list_money(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    deposits = db.scalars(
        select(Deposit).where(Deposit.trading_account_id == account_id).order_by(Deposit.ts.desc())
    ).all()
    withdrawals = db.scalars(
        select(Withdrawal)
        .where(Withdrawal.trading_account_id == account_id)
        .order_by(Withdrawal.ts.desc())
    ).all()
    items = [_money_out(d, "deposit") for d in deposits] + [
        _money_out(w, "withdrawal") for w in withdrawals
    ]
    items.sort(key=lambda x: x.ts, reverse=True)
    total_dep = sum(float(d.amount) for d in deposits)
    total_wd = sum(float(w.amount) for w in withdrawals)
    return MoneyListOut(
        net_deposits=round(total_dep - total_wd, 2),
        total_deposits=round(total_dep, 2),
        total_withdrawals=round(total_wd, 2),
        items=items,
    )


@router.post("/accounts/{account_id}/deposits", status_code=201, response_model=MoneyOut)
def create_deposit(
    account_id: int,
    body: MoneyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    acc = _account_or_404(db, account_id, user)
    row = Deposit(
        user_id=user.id,
        trading_account_id=acc.id,
        amount=body.amount,
        ts=body.ts or datetime.now(UTC),
        method=body.method,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _money_out(row, "deposit")


@router.post("/accounts/{account_id}/withdrawals", status_code=201, response_model=MoneyOut)
def create_withdrawal(
    account_id: int,
    body: MoneyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    acc = _account_or_404(db, account_id, user)
    row = Withdrawal(
        user_id=user.id,
        trading_account_id=acc.id,
        amount=body.amount,
        ts=body.ts or datetime.now(UTC),
        method=body.method,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _money_out(row, "withdrawal")


@router.delete("/money/{kind}/{row_id}", status_code=204)
def delete_money(
    kind: str,
    row_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    model = Deposit if kind == "deposit" else Withdrawal if kind == "withdrawal" else None
    if model is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jenis mutasi tidak dikenal")
    row = db.get(model, row_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mutasi tidak ditemukan")
    db.delete(row)
    db.commit()
