"""Dependencies FastAPI: current user dari Bearer JWT (tenant-scoped)."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.api.app.core.security import decode_access_token
from packages.db import get_session
from packages.db.models import User

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Belum masuk", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid atau kedaluwarsa") from None
    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token tidak valid")
    user = db.get(User, int(payload["sub"]))
    if user is None or user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User tidak ditemukan")
    if payload.get("sv") != user.session_version:
        # sesi sudah di-revoke (logout / ganti password / session_version dinaikkan)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesi tidak berlaku lagi")
    return user
