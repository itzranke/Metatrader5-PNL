"""Kriptografi & header auth device (HMAC/bearer + anti-replay)."""
import hashlib
import hmac
import secrets
import time
import uuid


def new_client_id() -> str:
    return f"cli-{uuid.uuid4().hex}"


def new_nonce() -> str:
    return f"{int(time.time() * 1000)}-{secrets.token_hex(8)}"


def auth_headers(device_id: int, device_key: str) -> dict:
    return {
        "X-Device-Id": str(device_id),
        "X-Device-Key": device_key,
        "X-Timestamp": str(int(time.time())),
        "X-Nonce": new_nonce(),
    }


def sign(device_key: str, body: bytes, timestamp: str, nonce: str) -> str:
    """HMAC-SHA256 digest untuk integritas payload (opsional di server)."""
    message = f"{timestamp}.{nonce}.".encode() + body
    return hmac.new(device_key.encode(), message, hashlib.sha256).hexdigest()
