"""Phase 2 — Authentication & session management (BLUEPRINT §11, KEPUTUSAN-FINAL DR-05).

Alur:
- register → kirim email verifikasi (Resend; dev: log link) → verify → login.
- login → access JWT (Bearer, di-memory frontend) + refresh cookie httpOnly (rotasi).
- refresh → rotasi token + extend; reuse token basi → cabut semua sesi user.
- logout/ganti password → session_version++ → SEMUA token mati.
- Rate limit: login 5/mnt/email + 20/mnt/IP; register 3/jam/IP.
- Anti enumerasi: /forgot selalu 200.
"""
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.app.core.deps import get_current_user
from apps.api.app.core.ratelimit import get_limiter
from apps.api.app.core.security import (
    REFRESH_TOKEN_TTL_DAYS,
    RESET_PASSWORD_TTL_MINUTES,
    VERIFY_EMAIL_TTL_HOURS,
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    verify_password,
)
from apps.api.app.schemas.auth import (
    ChangePasswordRequest,
    ForgotRequest,
    LoginRequest,
    RegisterRequest,
    ResetRequest,
    SessionOut,
    TokenResponse,
    UpdateMeRequest,
    UserOut,
    VerifyRequest,
)
from apps.api.app.services.email import send_email
from packages.config import get_settings
from packages.db import get_session
from packages.db.models import AuthToken, User
from packages.db.models import Session as DBSession

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("api.auth")

now = lambda: datetime.now(UTC)  # noqa: E731


def _as_aware(dt: datetime) -> datetime:
    """SQLite mengembalikan datetime naive (tanpa tz) → anggap UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")


def _user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        "refresh_token",
        token,
        max_age=REFRESH_TOKEN_TTL_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=settings.environment in ("staging", "production"),
        path="/api/v1/auth",  # refresh hanya dikirim ke endpoint auth
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/api/v1/auth")


# ---------------------------------------------------------------- register & verify


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    limiter = get_limiter()
    if not limiter.allow(f"register-ip:{_client_ip(request)}", 3, 3600):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Terlalu banyak percobaan daftar. Coba lagi nanti.")
    exists = db.scalar(
        select(User).where((User.email == body.email) | (User.username == body.username))
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email atau username sudah terdaftar")

    user = User(username=body.username, email=body.email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()

    token = new_refresh_token()
    db.add(
        AuthToken(
            user_id=user.id,
            kind="verify_email",
            token_hash=hash_token(token),
            expires_at=now() + timedelta(hours=VERIFY_EMAIL_TTL_HOURS),
        )
    )
    db.commit()

    settings = get_settings()
    link = f"{settings.frontend_url}/verify-email?token={token}"
    send_email(
        body.email,
        "Verifikasi email — MT5 Journal",
        f"<p>Halo {body.username},</p><p>Klik link berikut untuk verifikasi email (berlaku 24 jam):</p>"
        f'<p><a href="{link}">{link}</a></p>',
    )
    return {"ok": True}


@router.post("/verify")
def verify_email(body: VerifyRequest, db: Session = Depends(get_session)) -> dict:
    t = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_token(body.token), AuthToken.kind == "verify_email"
        )
    )
    if t is None or t.used_at is not None or _as_aware(t.expires_at) < now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token verifikasi tidak valid atau kedaluwarsa")
    t.user.email_verified_at = now()
    t.used_at = now()
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- login / refresh / logout


@router.post("/login")
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_session),
) -> TokenResponse:
    limiter = get_limiter()
    ip = _client_ip(request)
    if not limiter.allow(f"login:{body.email}", 5, 60) or not limiter.allow(f"login-ip:{ip}", 20, 60):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Terlalu banyak percobaan. Coba lagi 1 menit lagi.")

    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or user.deleted_at is not None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email atau password salah")

    refresh = new_refresh_token()
    ua = (request.headers.get("user-agent") or "")[:255]
    db.add(
        DBSession(
            user_id=user.id,
            refresh_token_hash=hash_token(refresh),
            device_name=ua.split("(")[0].strip()[:100] or "Perangkat tidak dikenal",
            ip=ip,
            user_agent=ua,
            expires_at=now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        )
    )
    db.commit()

    access = create_access_token(user.id, user.session_version)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(access_token=access, user=_user_out(user))


@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_session)) -> TokenResponse:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Tidak ada refresh token")
    session = db.scalar(select(DBSession).where(DBSession.refresh_token_hash == hash_token(token)))
    if session is None or session.revoked_at is not None or _as_aware(session.expires_at) < now():
        if session is not None and session.revoked_at is None:
            # reuse token basi → ancaman: cabut semua sesi user
            session.user.session_version += 1
            logger.warning("refresh token reuse terdeteksi — semua sesi user %s dicabut", session.user_id)
        db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesi kedaluwarsa, silakan masuk lagi")

    user = session.user
    if user.deleted_at is not None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User tidak ditemukan")

    # rotasi refresh token
    new_refresh = new_refresh_token()
    session.refresh_token_hash = hash_token(new_refresh)
    session.last_seen_at = now()
    db.commit()

    access = create_access_token(user.id, user.session_version)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access, user=_user_out(user))


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    token = request.cookies.get("refresh_token")
    if token:
        session = db.scalar(select(DBSession).where(DBSession.refresh_token_hash == hash_token(token)))
        if session is not None:
            session.revoked_at = now()
    user.session_version += 1  # semua access token & refresh token lama mati
    db.commit()
    _clear_refresh_cookie(response)
    return {"ok": True}


# ---------------------------------------------------------------- forgot / reset


@router.post("/forgot")
def forgot_password(body: ForgotRequest, db: Session = Depends(get_session)) -> dict:
    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.deleted_at is None:
        token = new_refresh_token()
        db.add(
            AuthToken(
                user_id=user.id,
                kind="reset_password",
                token_hash=hash_token(token),
                expires_at=now() + timedelta(minutes=RESET_PASSWORD_TTL_MINUTES),
            )
        )
        db.commit()
        settings = get_settings()
        link = f"{settings.frontend_url}/reset-password?token={token}"
        send_email(
            body.email,
            "Reset password — MT5 Journal",
            f'<p>Klik link berikut untuk reset password (berlaku 15 menit):</p><p><a href="{link}">{link}</a></p>',
        )
    return {"ok": True}  # selalu 200 — anti enumerasi email


@router.post("/reset")
def reset_password(body: ResetRequest, db: Session = Depends(get_session)) -> dict:
    t = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_token(body.token), AuthToken.kind == "reset_password"
        )
    )
    if t is None or t.used_at is not None or _as_aware(t.expires_at) < now():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token reset tidak valid atau kedaluwarsa")
    user = t.user
    user.password_hash = hash_password(body.password)
    user.session_version += 1
    for s in user.sessions:
        s.revoked_at = now()
    t.used_at = now()
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------- session management


@router.get("/sessions")
def list_sessions(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> list[SessionOut]:
    rows = db.scalars(
        select(DBSession)
        .where(DBSession.user_id == user.id, DBSession.revoked_at.is_(None))
        .order_by(DBSession.last_seen_at.desc().nulls_last(), DBSession.created_at.desc())
    ).all()
    current_hash = hash_token(request.cookies.get("refresh_token") or "")
    out = []
    for s in rows:
        item = SessionOut.model_validate(s)
        item.is_current = s.refresh_token_hash == current_hash
        out.append(item)
    return out


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> None:
    session = db.get(DBSession, session_id)
    if session is None or session.user_id != user.id:  # tenant-scoping → 404
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sesi tidak ditemukan")
    session.revoked_at = now()
    db.commit()


# ---------------------------------------------------------------- profile


@router.get("/me")
def get_me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.patch("/me")
def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> UserOut:
    if body.username and body.username != user.username:
        exists = db.scalar(select(User).where(User.username == body.username, User.id != user.id))
        if exists:
            raise HTTPException(status.HTTP_409_CONFLICT, "Username sudah dipakai")
        user.username = body.username
    if body.locale:
        user.locale = body.locale
    if body.base_currency:
        user.base_currency = body.base_currency.upper()
    db.commit()
    return _user_out(user)


@router.post("/me/password")
def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> dict:
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password lama salah")
    user.password_hash = hash_password(body.new_password)
    user.session_version += 1
    for s in user.sessions:
        s.revoked_at = now()
    db.commit()
    return {"ok": True}
