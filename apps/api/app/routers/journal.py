"""Phase 6 — Jurnal Trading (BLUEPRINT §2 fitur E1, §17 drill-down).

CRUD jurnal per trade (opsional tanpa trade = mode manual), tag many-to-many,
screenshot upload (file lokal — pindah ke R2 saat cloud, §21).
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.schemas.journal import JournalCreate, JournalOut, JournalUpdate, TagCreate, TagOut
from packages.config import get_settings
from packages.db import get_session
from packages.db.models import (
    JournalEntry,
    Tag,
    Trade,
    TradingAccount,
    User,
    trade_tags,
)

router = APIRouter(tags=["journal"])

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _account_or_404(db: Session, account_id: int, user: User) -> TradingAccount:
    acc = db.get(TradingAccount, account_id)
    if acc is None or acc.user_id != user.id or acc.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Akun tidak ditemukan")
    return acc


def _get_or_create_tags(db: Session, user_id: int, names: list[str]) -> list[Tag]:
    tags = []
    for name in names[:10]:
        name = name.strip().lower()
        if not name:
            continue
        tag = db.scalar(select(Tag).where(Tag.user_id == user_id, Tag.name == name))
        if tag is None:
            tag = Tag(user_id=user_id, name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def _journal_out(db: Session, entry: JournalEntry) -> JournalOut:
    out = JournalOut.model_validate(entry)
    out.tags = [t.name for t in entry.tags_m2m]
    if entry.trade_id:
        trade = db.get(Trade, entry.trade_id)
        if trade is not None:
            out.trade_symbol = trade.symbol
            out.trade_net_profit = float(trade.net_profit or 0)
    return out


@router.get("/journal", response_model=list[JournalOut])
def list_journal(
    tag: str | None = None,
    setup: str | None = None,
    month: str | None = None,  # YYYY-MM
    account_id: int | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    q = select(JournalEntry).where(JournalEntry.user_id == user.id)
    if account_id:
        q = q.where(JournalEntry.trading_account_id == account_id)
    if setup:
        q = q.where(JournalEntry.setup == setup)
    if month:
        q = q.where(func.strftime("%Y-%m", JournalEntry.entry_date) == month)
    if tag:
        q = q.join(JournalEntry.tags_m2m).where(Tag.name == tag)
    rows = db.scalars(q.order_by(JournalEntry.entry_date.desc()).limit(min(limit, 200))).all()
    return [_journal_out(db, e) for e in rows]


@router.post("/journal", status_code=201, response_model=JournalOut)
def create_journal(
    body: JournalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    _account_or_404(db, body.trading_account_id, user)
    if body.trade_id is not None:
        trade = db.get(Trade, body.trade_id)
        if trade is None or trade.user_id != user.id or trade.trading_account_id != body.trading_account_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Trade tidak ditemukan")
    entry = JournalEntry(
        user_id=user.id,
        trading_account_id=body.trading_account_id,
        trade_id=body.trade_id,
        entry_date=body.entry_date,
        setup=body.setup.strip().lower(),
        emotion_before=body.emotion_before,
        emotion_during=body.emotion_during,
        emotion_after=body.emotion_after,
        confidence=body.confidence,
        fear=body.fear, greed=body.greed, revenge=body.revenge,
        fomo=body.fomo, boredom=body.boredom,
        discipline=body.discipline,
        rule_adherence=body.rule_adherence,
        reason_entry=body.reason_entry,
        reason_exit=body.reason_exit,
        notes=body.notes,
        lesson=body.lesson,
        plan_match=body.plan_match,
    )
    db.add(entry)
    db.flush()
    entry.tags_m2m = _get_or_create_tags(db, user.id, body.tags)
    db.commit()
    db.refresh(entry)
    return _journal_out(db, entry)


@router.get("/journal/{entry_id}", response_model=JournalOut)
def get_journal(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jurnal tidak ditemukan")
    return _journal_out(db, entry)


@router.patch("/journal/{entry_id}", response_model=JournalOut)
def update_journal(
    entry_id: int,
    body: JournalUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jurnal tidak ditemukan")
    for field in (
        "setup", "emotion_before", "emotion_during", "emotion_after",
        "confidence", "fear", "greed", "revenge", "fomo", "boredom",
        "discipline", "rule_adherence", "reason_entry", "reason_exit",
        "notes", "lesson", "plan_match",
    ):
        value = getattr(body, field)
        if value is not None:
            setattr(entry, field, value.strip().lower() if field == "setup" and isinstance(value, str) else value)
    if body.tags is not None:
        entry.tags_m2m = _get_or_create_tags(db, user.id, body.tags)
    db.commit()
    db.refresh(entry)
    return _journal_out(db, entry)


@router.delete("/journal/{entry_id}", status_code=204)
def delete_journal(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jurnal tidak ditemukan")
    # hapus relasi tag dulu (association table)
    db.execute(trade_tags.delete().where(trade_tags.c.journal_entry_id == entry.id))
    db.delete(entry)
    db.commit()


@router.post("/journal/{entry_id}/screenshot", response_model=JournalOut)
async def upload_screenshot(
    entry_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    entry = db.get(JournalEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Jurnal tidak ditemukan")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Format gambar tidak didukung")
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Maksimal 5 MB")
    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / filename).write_bytes(data)
    entry.screenshot_path = filename
    db.commit()
    db.refresh(entry)
    return _journal_out(db, entry)


@router.get("/tags", response_model=list[TagOut])
def list_tags(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    rows = db.scalars(
        select(Tag).where(Tag.user_id == user.id).order_by(Tag.name.asc())
    ).all()
    return [TagOut.model_validate(t) for t in rows]


@router.post("/tags", status_code=201, response_model=TagOut)
def create_tag(
    body: TagCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    name = body.name.strip().lower()
    existing = db.scalar(select(Tag).where(Tag.user_id == user.id, Tag.name == name))
    if existing is not None:
        existing.color = body.color
        db.commit()
        db.refresh(existing)
        return TagOut.model_validate(existing)
    tag = Tag(user_id=user.id, name=name, color=body.color)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)
