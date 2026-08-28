"""Phase 4 — MT5 Connector endpoints (BLUEPRINT §8).

Alur:
1. POST /connector/pair-request  (web, JWT) → kode pairing 8 digit, TTL 5 mnt, sekali pakai
2. POST /connector/pair          (connector) → tukar kode → device_id + device_key (sekali)
3. POST /connector/heartbeat     (device auth) → last_seen + state
4. POST /connector/sync          (device auth) → ingest deals/positions, idempoten
5. GET  /connector/devices       (web, JWT) → daftar perangkat user
"""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.core.device_auth import (
    get_current_device,
    hash_pairing_code,
    new_device_key,
    new_pairing_code,
    verify_pairing_code,
)
from apps.api.app.core.security import hash_password
from apps.api.app.schemas.connector import (
    DeviceOut,
    HeartbeatOut,
    PairIn,
    PairOut,
    PairRequestOut,
    SyncIn,
    SyncOut,
)
from packages.db import get_session
from packages.db.models import (
    ConnectorDevice,
    Deal,
    MT5Connection,
    Position,
    TradingAccount,
    User,
)

router = APIRouter(tags=["connector"])

PAIRING_TTL_SECONDS = 300


def _as_aware(dt: datetime) -> datetime:
    """SQLite menyimpan datetime naive → anggap UTC (konsisten dengan Phase 2)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _upsert_deals(db: Session, account_id: int, user_id: int, deals: list) -> tuple[int, int]:
    """Upsert idempoten: UNIQUE(trading_account_id, deal_ticket) → DO NOTHING."""
    if not deals:
        return 0, 0
    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"
    insert = sqlite_insert if dialect == "sqlite" else pg_insert
    stmt = (
        insert(Deal)
        .values(
            [
                {
                    "trading_account_id": account_id,
                    "user_id": user_id,
                    "deal_ticket": d.deal_ticket,
                    "order_ticket": d.order_ticket,
                    "time": d.time,
                    "type": d.type,
                    "symbol": d.symbol,
                    "volume": d.volume,
                    "price": d.price,
                    "profit": d.profit,
                    "swap": d.swap,
                    "commission": d.commission,
                    "comment": d.comment,
                    "external_id": d.external_id,
                }
                for d in deals
            ]
        )
        .on_conflict_do_nothing(index_elements=["trading_account_id", "deal_ticket"])
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0, len(deals) - (result.rowcount or 0)


@router.post("/connector/pair-request", status_code=201, response_model=PairRequestOut)
def pair_request(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Web: buat kode pairing untuk connector (TTL 5 mnt, sekali pakai)."""
    code = new_pairing_code()
    connector_device = ConnectorDevice(
        user_id=user.id,
        device_name="",
        device_key_hash="",  # diisi saat pair
        client_id=None,  # diisi saat pair
        pairing_code_hash=hash_pairing_code(code),
        pairing_expires_at=datetime.now(UTC).replace(microsecond=0)
        + timedelta(seconds=PAIRING_TTL_SECONDS),
        state="PAIRING",
    )
    db.add(connector_device)
    db.commit()
    db.refresh(connector_device)
    return PairRequestOut(
        device_id=connector_device.id, code=code,
        expires_at=connector_device.pairing_expires_at,
    )


@router.post("/connector/pair", response_model=PairOut)
def pair(body: PairIn, db: Session = Depends(get_session)):
    """Connector: tukar kode pairing → device_id + device_key (dikirim sekali)."""
    now = datetime.now(UTC)
    # cari device PAIRING yang code-nya cocok & belum kedaluwarsa
    devices = db.scalars(
        select(ConnectorDevice).where(ConnectorDevice.state == "PAIRING")
    ).all()
    matched = None
    for dev in devices:
        if dev.pairing_expires_at and _as_aware(dev.pairing_expires_at) < now:
            continue
        if verify_pairing_code(body.code, dev.pairing_code_hash or ""):
            matched = dev
            break
    if matched is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kode pairing tidak valid atau kedaluwarsa")
    if matched.client_id and matched.client_id != body.client_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Kode sudah dipakai")
    dup = db.scalar(
        select(ConnectorDevice).where(
            ConnectorDevice.client_id == body.client_id,
            ConnectorDevice.revoked_at.is_(None),
        )
    )
    if dup is not None and dup.id != matched.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Client ID sudah terdaftar di perangkat lain")

    device_key = new_device_key()
    matched.client_id = body.client_id
    matched.device_name = body.device_name or f"Device-{matched.id}"
    matched.version = body.version
    matched.pairing_code_hash = None
    matched.pairing_expires_at = None
    matched.last_seen_at = now
    matched.state = "CONNECTED"
    # hash argon2 — server tidak pernah menyimpan raw key
    matched.device_key_hash = hash_password(device_key)
    db.commit()
    return PairOut(device_id=matched.id, device_key=device_key)


@router.post("/connector/heartbeat", response_model=HeartbeatOut)
def heartbeat(
    device: ConnectorDevice = Depends(get_current_device),
    db: Session = Depends(get_session),
):
    device.state = "CONNECTED"
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    return HeartbeatOut(ok=True, server_time=datetime.now(UTC))


@router.post("/connector/sync", response_model=SyncOut)
def sync(
    body: SyncIn,
    device: ConnectorDevice = Depends(get_current_device),
    db: Session = Depends(get_session),
):
    """Connector: kirim batch deals + snapshot posisi (maks 500 deal/batch)."""
    now = datetime.now(UTC)
    device.last_seen_at = now
    device.state = "CONNECTED"

    account = db.scalar(
        select(TradingAccount).where(
            TradingAccount.user_id == device.user_id,
            TradingAccount.login == body.login,
            TradingAccount.server == body.server,
            TradingAccount.deleted_at.is_(None),
        )
    )
    if account is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Akun tidak ditemukan — daftarkan dulu di web (halaman Akun)",
        )

    conn = account.connection
    if conn is None:
        conn = MT5Connection(
            user_id=device.user_id,
            trading_account_id=account.id,
            connector_device_id=device.id,
            state="SYNCING",
        )
        db.add(conn)
        db.commit()
        db.refresh(conn)
    elif conn.connector_device_id != device.id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Akun ini sudah dipair dengan perangkat lain"
        )

    accepted, duplicates = _upsert_deals(db, account.id, device.user_id, body.deals)

    # posisi: replace-all (diff server-side; posisi hilang = ditutup)
    existing = {
        p.ticket: p
        for p in db.scalars(
            select(Position).where(Position.trading_account_id == account.id)
        ).all()
    }
    incoming = {p.ticket: p for p in body.positions}
    closed = 0
    for ticket, pos in incoming.items():
        prev = existing.get(ticket)
        if prev is None:
            db.add(
                Position(
                    user_id=device.user_id,
                    trading_account_id=account.id,
                    ticket=ticket,
                    symbol=pos.symbol,
                    side=pos.side,
                    volume=pos.volume,
                    open_price=pos.open_price,
                    open_time=pos.open_time,
                    current_price=pos.current_price,
                    floating_pnl=pos.floating_pnl,
                    sl=pos.sl,
                    tp=pos.tp,
                )
            )
        else:
            prev.volume = pos.volume  # partial close → volume berkurang
            prev.current_price = pos.current_price
            prev.floating_pnl = pos.floating_pnl
            prev.sl = pos.sl
            prev.tp = pos.tp
    for ticket, prev in existing.items():
        if ticket not in incoming:
            db.delete(prev)  # posisi tidak ada lagi di MT5 = sudah ditutup
            closed += 1

    last_ticket = body.last_ticket
    conn.state = "SYNCED"
    conn.last_synced_at = now
    conn.last_error = None
    if last_ticket:
        conn.last_deal_ticket = last_ticket
    db.commit()
    return SyncOut(
        accepted=accepted,
        duplicates=duplicates,
        closed_positions=closed,
        last_ticket=conn.last_deal_ticket,
        state=conn.state,
    )


@router.get("/connector/devices", response_model=list[DeviceOut])
def list_devices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    devices = db.scalars(
        select(ConnectorDevice)
        .where(ConnectorDevice.user_id == user.id, ConnectorDevice.revoked_at.is_(None))
        .order_by(ConnectorDevice.created_at.desc())
    ).all()
    out = []
    for dev in devices:
        item = DeviceOut.model_validate(dev)
        item.accounts = [
            f"{c.account.login}@{c.account.server} ({c.state})" for c in dev.connections
        ]
        out.append(item)
    return out
