"""Keamanan: hashing password (argon2id), JWT access token, token acak.

Keputusan (KEPUTUSAN-FINAL DR-05):
- Access token: JWT HS256 15 mnt, disimpan IN-MEMORY di frontend, dikirim via
  header `Authorization: Bearer` (bukan cookie) → aman dari CSRF & XSS localStorage.
- Refresh token: opaque random 48-byte, HANYA di cookie httpOnly (path /api/v1/auth),
  dirotasi tiap refresh, disimpan hash SHA-256 di tabel sessions.
- Session versioning: users.session_version — naik saat logout/ganti password →
  semua token (access + refresh) lama mati.
"""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from packages.config import get_settings

ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 30
VERIFY_EMAIL_TTL_HOURS = 24
RESET_PASSWORD_TTL_MINUTES = 15

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(user_id: int, session_version: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sv": session_version,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.session_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.session_secret, algorithms=["HS256"])


def new_refresh_token() -> str:
    """Token opaque url-safe (dipakai refresh token & auth token email)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
