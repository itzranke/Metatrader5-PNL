"""Laporan bulanan — PDF on-demand + email (BLUEPRINT §25, F7/P18).

Sinkron untuk MVP (tanpa RQ worker — keputusan Phase 7); tenant-safe.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.services.email import send_email
from apps.api.app.services.report import MONTHS_ID, build_monthly_report
from packages.db import get_session
from packages.db.models import TradingAccount, User

router = APIRouter(tags=["reports"])


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


def _validate_month(month: str) -> None:
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Format bulan: YYYY-MM"
        ) from None


@router.get("/accounts/{account_id}/reports/monthly.pdf")
def monthly_report_pdf(
    account_id: int,
    month: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """PDF laporan bulanan (default: bulan berjalan)."""
    acc = _account_or_404(db, account_id, user)
    month = month or datetime.now().strftime("%Y-%m")
    _validate_month(month)
    pdf = build_monthly_report(db, acc, month)
    year, m = int(month[:4]), int(month[5:7])
    fname = f"laporan-{acc.name.lower().replace(' ', '-')}-{MONTHS_ID[m-1].lower()}-{year}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


class ReportEmailIn(BaseModel):
    month: str = Field(pattern=r"^\d{4}-\d{2}$")
    to: str | None = Field(default=None, max_length=254)


@router.post("/accounts/{account_id}/reports/monthly/email")
def monthly_report_email(
    account_id: int,
    body: ReportEmailIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Generate PDF lalu kirim via email (Resend; dev → log console)."""
    acc = _account_or_404(db, account_id, user)
    _validate_month(body.month)
    pdf = build_monthly_report(db, acc, body.month)
    year, m = int(body.month[:4]), int(body.month[5:7])
    fname = f"laporan-{MONTHS_ID[m-1].lower()}-{year}.pdf"
    ok = send_email(
        to=body.to or user.email,
        subject=f"Laporan Bulanan — {MONTHS_ID[m - 1]} {year} · {acc.name}",
        html=(
            f"<p>Halo {user.username},</p>"
            f"<p>Laporan bulanan akun <b>{acc.name}</b> ({body.month}) sudah siap.</p>"
            f"<p>Unduh lampiran PDF untuk ringkasan P&amp;L, metrik, MAE/MFE, dan kalender.</p>"
            f"<p><small>MT5 Journal</small></p>"
        ),
        text=f"Laporan bulanan {body.month} akun {acc.name} — lihat lampiran PDF.",
        attachment=(fname, pdf, "application/pdf"),
    )
    if not ok:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Gagal mengirim email")
    return {"ok": True, "to": body.to or user.email, "filename": fname}
