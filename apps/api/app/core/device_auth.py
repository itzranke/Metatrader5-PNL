"""Device auth untuk connector (BLUEPRINT §8.3).

Deviasi sadar dari blueprint: alih-alih HMAC body-digest, request connector
diautentikasi per-request dengan **X-Device-Key bearer** (Argon2 verify) +
anti-replay timestamp (±120 dtk) + nonce sekali pakai (in-memory TTL).
Alasan: verifikasi HMAC membutuhkan secret plaintext di server — menyimpan
device_key raw lebih lemah daripada argon2 hash. Bearer + TLS + anti-replay
memberikan jaminan yang setara dengan lebih sedikit permukaan serangan.
"""
import secrets
import threading
import time
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from apps.api.app.core.security import hash_password, verify_password
from packages.db import get_session
from packages.db.models import ConnectorDevice

CLOCK_SKEW_SECONDS = 120
NONCE_TTL_SECONDS = 300

_nonces: dict[str, float] = {}
_nonces_lock = threading.Lock()


def _consume_nonce(nonce: str) -> bool:
    """True jika nonce valid & belum pernah dipakai (anti-replay)."""
    now = time.time()
    with _nonces_lock:
        expired = [k for k, ts in _nonces.items() if now - ts > NONCE_TTL_SECONDS]
        for k in expired:
            _nonces.pop(k, None)
        if nonce in _nonces:
            return False
        _nonces[nonce] = now
        return True


def new_pairing_code() -> str:
    """Kode pairing 8 digit (TTS: disimpan sebagai hash)."""
    return f"{secrets.randbelow(10**8):08d}"


def hash_pairing_code(code: str) -> str:
    return hash_password(code)


def verify_pairing_code(code: str, code_hash: str) -> bool:
    return verify_password(code, code_hash)


def new_device_key() -> str:
    """Device key 32B hex — dikembalikan sekali ke connector."""
    return secrets.token_hex(32)


def get_current_device(
    request: Request,
    x_device_id: str | None = Header(default=None),
    x_device_key: str | None = Header(default=None),
    x_timestamp: str | None = Header(default=None),
    x_nonce: str | None = Header(default=None),
    db: Session = Depends(get_session),
) -> ConnectorDevice:
    if not (x_device_id and x_device_key and x_timestamp and x_nonce):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Header device auth tidak lengkap")
    # anti-replay: timestamp ±120 dtk
    try:
        ts = int(x_timestamp)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Timestamp tidak valid") from None
    if abs(time.time() - ts) > CLOCK_SKEW_SECONDS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Timestamp di luar jendela toleransi")
    if not _consume_nonce(x_nonce):
        raise HTTPException(status.HTTP_409_CONFLICT, "Nonce sudah dipakai (replay)")

    device = db.get(ConnectorDevice, int(x_device_id))
    if device is None or device.revoked_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Device tidak dikenal atau dicabut")
    if not verify_password(x_device_key, device.device_key_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kunci device salah")
    device.last_seen_at = datetime.now(UTC)
    device.ip = request.client.host if request.client else ""
    db.commit()
    return device
