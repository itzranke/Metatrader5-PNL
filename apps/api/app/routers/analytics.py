"""Analitik lanjutan — MAE/MFE (BLUEPRINT §14, halaman P14).

Data per trade dari mae_mfe_records (sumber: ticks/candles/none) + ringkasan
distribusi untuk scatter & histogram di web.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from packages.db import get_session
from packages.db.models import MaeMfeRecord, Trade, TradingAccount, User

router = APIRouter(tags=["analytics"])


def _account_or_404(db: Session, account_id: int, user: User) -> TradingAccount:
    acc = db.scalar(
        select(TradingAccount).where(
            TradingAccount.id == account_id,
            TradingAccount.user_id == user.id,
            TradingAccount.deleted_at.is_(None),
        )
    )
    if acc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    return acc


def _bucket(pct: float | None) -> str | None:
    if pct is None:
        return None
    if pct < 0.25:
        return "0–0.25%"
    if pct < 0.5:
        return "0.25–0.5%"
    if pct < 1.0:
        return "0.5–1%"
    if pct < 2.0:
        return "1–2%"
    return ">2%"


BUCKETS = ["0–0.25%", "0.25–0.5%", "0.5–1%", "1–2%", ">2%"]


@router.get("/accounts/{account_id}/analytics/mae-mfe")
def mae_mfe_analytics(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Distribusi MAE/MFE per trade + ringkasan (tenant-safe)."""
    _account_or_404(db, account_id, user)
    rows = db.execute(
        select(MaeMfeRecord, Trade)
        .join(Trade, MaeMfeRecord.trade_id == Trade.id)
        .where(
            MaeMfeRecord.trading_account_id == account_id,
            Trade.deleted_at.is_(None),
        )
        .order_by(Trade.close_time.desc())
    ).all()

    items = []
    mae_pcts, mfe_pcts, mae_rs, mfe_rs = [], [], [], []
    bucket_mae = {b: 0 for b in BUCKETS}
    bucket_mfe = {b: 0 for b in BUCKETS}
    source_counts = {"ticks": 0, "candles": 0, "none": 0}
    for rec, trade in rows:
        items.append({
            "trade_id": trade.id,
            "ticket": trade.ticket,
            "symbol": trade.symbol,
            "side": trade.side,
            "close_time": trade.close_time.isoformat(),
            "net_profit": float(trade.net_profit or 0),
            "mae_pts": float(rec.mae_pts) if rec.mae_pts is not None else None,
            "mfe_pts": float(rec.mfe_pts) if rec.mfe_pts is not None else None,
            "mae_currency": float(rec.mae_currency) if rec.mae_currency is not None else None,
            "mfe_currency": float(rec.mfe_currency) if rec.mfe_currency is not None else None,
            "mae_pct": float(rec.mae_pct) if rec.mae_pct is not None else None,
            "mfe_pct": float(rec.mfe_pct) if rec.mfe_pct is not None else None,
            "mae_r": float(rec.mae_r) if rec.mae_r is not None else None,
            "mfe_r": float(rec.mfe_r) if rec.mfe_r is not None else None,
            "path_source": rec.path_source,
            "samples": rec.samples,
        })
        src = rec.path_source if rec.path_source in source_counts else "none"
        source_counts[src] += 1
        if rec.mae_pct is not None:
            mae_pcts.append(float(rec.mae_pct))
            bucket_mae[_bucket(float(rec.mae_pct)) or "0–0.25%"] += 1
        if rec.mfe_pct is not None:
            mfe_pcts.append(float(rec.mfe_pct))
            bucket_mfe[_bucket(float(rec.mfe_pct)) or "0–0.25%"] += 1
        if rec.mae_r is not None:
            mae_rs.append(float(rec.mae_r))
        if rec.mfe_r is not None:
            mfe_rs.append(float(rec.mfe_r))

    total = len(rows)
    summary = {
        "covered": total,
        "avg_mae_pct": round(sum(mae_pcts) / len(mae_pcts), 4) if mae_pcts else None,
        "avg_mfe_pct": round(sum(mfe_pcts) / len(mfe_pcts), 4) if mfe_pcts else None,
        "avg_mae_r": round(sum(mae_rs) / len(mae_rs), 3) if mae_rs else None,
        "avg_mfe_r": round(sum(mfe_rs) / len(mfe_rs), 3) if mfe_rs else None,
        "ratio_mae_mfe": round(
            (sum(mae_pcts) / len(mae_pcts)) / (sum(mfe_pcts) / len(mfe_pcts)), 3
        ) if mae_pcts and mfe_pcts else None,
        "source_counts": source_counts,
        "buckets_mae": [{"bucket": b, "count": bucket_mae[b]} for b in BUCKETS],
        "buckets_mfe": [{"bucket": b, "count": bucket_mfe[b]} for b in BUCKETS],
    }
    return {"items": items, "summary": summary}
