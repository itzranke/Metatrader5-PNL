"""Phase 7 — Export CSV (BLUEPRINT §27, versi MVP sinkron).

Deviasi sadar: blueprint §27 memakai job async (RQ) + tabel exports + signed URL.
MVP tanpa worker → CSV di-stream langsung (csv stdlib, BOM UTF-8 agar terbuka
rapi di Excel). Excel/PDF + async job menyusul di Phase 2 (lihat §32).
Maks 50.000 baris dengan header peringatan — sama dengan batas blueprint.
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from packages.db import get_session
from packages.db.models import JournalEntry, Trade, TradingAccount, User

router = APIRouter(tags=["export"])

MAX_ROWS = 50000


def _account_or_404(db: Session, account_id: int, user: User) -> TradingAccount:
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    return acc


def _csv_response(rows: list[dict], filename: str) -> Response:
    buf = io.StringIO()
    buf.write("\ufeff")  # BOM UTF-8 → Excel membaca aksen dengan benar
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else [])
    if rows:
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/accounts/{account_id}/export/trades.csv")
def export_trades(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    rows = db.scalars(
        select(Trade).where(Trade.trading_account_id == account_id, Trade.deleted_at.is_(None))
    ).all()
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS]
    data = [
        {
            "ticket": t.ticket,
            "symbol": t.symbol,
            "side": t.side,
            "volume": float(t.volume),
            "open_price": float(t.open_price),
            "close_price": float(t.close_price),
            "open_time": t.open_time.isoformat(),
            "close_time": t.close_time.isoformat(),
            "net_profit": float(t.net_profit or 0),
            "gross_profit": float(t.gross_profit or 0),
            "swap": float(t.swap or 0),
            "commission": float(t.commission or 0),
            "r_multiple": float(t.r_multiple) if t.r_multiple is not None else "",
            "source": t.source,
            "terpotong": "ya — >50.000 baris" if len(rows) == MAX_ROWS else "",
        }
        for t in rows
    ]
    return _csv_response(data, f"trades-{account_id}.csv")


@router.get("/accounts/{account_id}/export/journal.csv")
def export_journal(
    account_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, account_id, user)
    entries = db.scalars(
        select(JournalEntry)
        .where(JournalEntry.trading_account_id == account_id)
        .order_by(JournalEntry.entry_date.asc())
    ).all()
    if len(entries) > MAX_ROWS:
        entries = entries[:MAX_ROWS]
    data = []
    for e in entries:
        trade = db.get(Trade, e.trade_id) if e.trade_id else None
        data.append(
            {
                "entry_date": e.entry_date.isoformat(),
                "setup": e.setup,
                "emotion_before": e.emotion_before,
                "emotion_during": e.emotion_during,
                "emotion_after": e.emotion_after,
                "confidence": e.confidence,
                "discipline": e.discipline,
                "fear": e.fear, "greed": e.greed, "revenge": e.revenge,
                "fomo": e.fomo, "boredom": e.boredom,
                "rule_adherence": e.rule_adherence,
                "reason_entry": e.reason_entry,
                "reason_exit": e.reason_exit,
                "notes": e.notes,
                "lesson": e.lesson,
                "plan_match": e.plan_match if e.plan_match is not None else "",
                "tags": "|".join(t.name for t in e.tags_m2m),
                "trade_symbol": trade.symbol if trade else "",
                "trade_net_profit": float(trade.net_profit or 0) if trade else "",
            }
        )
    return _csv_response(data, f"journal-{account_id}.csv")
