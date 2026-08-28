"""Phase 5 — PnL Dashboard & Analytics endpoints (BLUEPRINT §12, §17).

Metrik dihitung live dari trades (skala MVP: <10k trade — cukup cepat).
Optimasi ke daily_statistics cache menyusul bila perlu (BLUEPRINT §12 strategi).
"""
from datetime import UTC, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.schemas.dashboard import (
    AccountOverviewAggregate,
    CalendarDay,
    EquityPoint,
    MonthlyStatOut,
    OverviewOut,
    PositionOut,
    TradeOut,
    TradesPage,
)
from packages.analytics import calendar_days, equity_curve, monthly_summary, summarize
from packages.db import get_session
from packages.db.models import (
    BalanceSnapshot,
    EquitySnapshot,
    Position,
    Trade,
    TradingAccount,
    User,
)

router = APIRouter(tags=["dashboard"])


def _account_or_404(db: Session, account_id: int, user: User) -> TradingAccount:
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    return acc


def _trades_query(db: Session, account_id: int, days: int | None = None):
    q = select(Trade).where(Trade.trading_account_id == account_id, Trade.deleted_at.is_(None))
    if days:
        since = datetime.now(UTC) - timedelta(days=days)
        q = q.where(Trade.close_time >= since)
    return q


def _as_float(v) -> float | None:
    if v is None:
        return None
    return round(float(v), 2)


def _trade_dict(t: Trade) -> dict:
    return {
        "net_profit": _as_float(t.net_profit) or 0.0,
        "gross_profit": _as_float(t.gross_profit) or 0.0,
        "open_time": t.open_time,
        "close_time": t.close_time,
        "r_multiple": _as_float(t.r_multiple),
    }


def _recent_pnl(db: Session, account_id: int, start: datetime) -> float:
    rows = db.scalars(
        select(Trade.net_profit).where(
            Trade.trading_account_id == account_id,
            Trade.deleted_at.is_(None),
            Trade.close_time >= start,
        )
    ).all()
    return round(sum(_as_float(v) or 0 for v in rows), 2)


@router.get("/accounts/overview", response_model=AccountOverviewAggregate)
def aggregate_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Agregasi lintas semua akun user (multi-account, BLUEPRINT §32 Phase 2)."""
    accs = db.scalars(
        select(TradingAccount).where(
            TradingAccount.user_id == user.id, TradingAccount.deleted_at.is_(None)
        )
    ).all()
    ids = [a.id for a in accs]
    net = 0.0
    if ids:
        rows = db.scalars(
            select(Trade.net_profit).where(
                Trade.trading_account_id.in_(ids), Trade.deleted_at.is_(None)
            )
        ).all()
        net = round(sum(_as_float(v) or 0 for v in rows), 2)
    positions = db.scalars(
        select(Position).where(Position.trading_account_id.in_(ids))
    ).all() if ids else []
    return AccountOverviewAggregate(
        accounts=len(accs),
        net_profit_total=net,
        open_positions=len(positions),
        floating_pnl=round(sum(_as_float(p.floating_pnl) or 0 for p in positions), 2),
    )


@router.get("/accounts/{account_id}/overview", response_model=OverviewOut)
def account_overview(
    account_id: int,
    days: int | None = Query(default=None, ge=1, le=3650),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    acc = _account_or_404(db, account_id, user)
    q = _trades_query(db, account_id, days)
    trades = [_trade_dict(t) for t in db.scalars(q).all()]

    now = datetime.now(UTC)
    today_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
    month_start = datetime.combine(now.date().replace(day=1), time.min, tzinfo=UTC)

    positions = db.scalars(
        select(Position).where(Position.trading_account_id == account_id)
    ).all()

    last_balance = db.scalar(
        select(BalanceSnapshot.value)
        .where(BalanceSnapshot.trading_account_id == account_id)
        .order_by(BalanceSnapshot.ts.desc())
        .limit(1)
    )
    last_equity = db.scalar(
        select(EquitySnapshot.value)
        .where(EquitySnapshot.trading_account_id == account_id)
        .order_by(EquitySnapshot.ts.desc())
        .limit(1)
    )

    return OverviewOut(
        account_id=acc.id,
        account_name=acc.name,
        currency=acc.currency,
        days=days or 0,
        balance=_as_float(last_balance),
        equity=_as_float(last_equity),
        open_positions=len(positions),
        floating_pnl=round(sum(_as_float(p.floating_pnl) or 0 for p in positions), 2),
        today_pnl=_recent_pnl(db, account_id, today_start),
        month_pnl=_recent_pnl(db, account_id, month_start),
        summary=summarize(trades),
    )


@router.get("/accounts/{account_id}/equity", response_model=list[EquityPoint])
def account_equity(
    account_id: int,
    days: int | None = Query(default=None, ge=1, le=3650),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Equity curve: snapshot bila ada; fallback P&L kumulatif dari trades."""
    acc = _account_or_404(db, account_id, user)
    snapshots = db.scalars(
        select(EquitySnapshot)
        .where(EquitySnapshot.trading_account_id == account_id)
        .order_by(EquitySnapshot.ts.asc())
    ).all()
    if snapshots:
        return [
            EquityPoint(ts=s.ts, equity=_as_float(s.value) or 0.0) for s in snapshots
        ]
    q = _trades_query(db, account_id, days)
    trades = [_trade_dict(t) for t in db.scalars(q).all()]
    return [EquityPoint(ts=datetime.fromisoformat(p["ts"]), equity=p["equity"]) for p in equity_curve(trades)]


@router.get("/accounts/{account_id}/calendar", response_model=list[CalendarDay])
def account_calendar(
    account_id: int,
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """P&L per hari — kalender heatmap (BLUEPRINT §17)."""
    _account_or_404(db, account_id, user)
    q = _trades_query(db, account_id)
    trades = [_trade_dict(t) for t in db.scalars(q).all()]
    return [CalendarDay(**d) for d in calendar_days(trades, month)]


@router.get("/accounts/{account_id}/trades", response_model=TradesPage)
def account_trades(
    account_id: int,
    symbol: str | None = Query(default=None, max_length=32),
    side: str | None = Query(default=None, pattern="^(buy|sell)$"),
    result: str | None = Query(default=None, pattern="^(win|loss|be)$"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    q = select(Trade).where(Trade.trading_account_id == account_id, Trade.deleted_at.is_(None))
    if symbol:
        q = q.where(Trade.symbol == symbol)
    if side:
        q = q.where(Trade.side == side)
    if result == "win":
        q = q.where(Trade.net_profit > 0)
    elif result == "loss":
        q = q.where(Trade.net_profit < 0)
    elif result == "be":
        q = q.where(Trade.net_profit == 0)
    if from_:
        q = q.where(Trade.close_time >= from_)
    if to:
        q = q.where(Trade.close_time <= to)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Trade.close_time.desc()).offset(offset).limit(limit)).all()
    return TradesPage(total=total, offset=offset, items=[TradeOut.model_validate(t) for t in rows])


@router.get("/accounts/{account_id}/monthly", response_model=list[MonthlyStatOut])
def account_monthly(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    q = _trades_query(db, account_id)
    trades = [_trade_dict(t) for t in db.scalars(q).all()]
    return [MonthlyStatOut(**s) for s in monthly_summary(trades)]


@router.get("/accounts/{account_id}/positions", response_model=list[PositionOut])
def account_positions(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    rows = db.scalars(
        select(Position)
        .where(Position.trading_account_id == account_id)
        .order_by(Position.open_time.desc())
    ).all()
    return [PositionOut.model_validate(p) for p in rows]
