"""Health check: DB (SELECT 1) + Redis (opsional)."""
from fastapi import APIRouter
from sqlalchemy import text

from packages.config import get_settings
from packages.db import engine

router = APIRouter(tags=["system"])


@router.get("/healthz")
def healthz() -> dict:
    settings = get_settings()

    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - path error saja
        db_status = f"error: {exc}"

    redis_status = "disabled"
    if settings.redis_url:
        try:
            import redis  # lazy import agar healthz tetap jalan tanpa redis

            client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1)
            client.ping()
            redis_status = "ok"
        except Exception as exc:  # pragma: no cover
            redis_status = f"error: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "redis": redis_status,
        "app": settings.app_name,
        "environment": settings.environment,
    }
