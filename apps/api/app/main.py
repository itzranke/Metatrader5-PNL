"""Aplikasi FastAPI — factory + middleware.

Phase 0–1: healthz, CORS, structured logging. Router fitur menyusul per fase.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from apps.api.app.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from apps.api.app.routers import accounts, auth, connector, dashboard, health
from packages.config import get_settings
from packages.db import SessionLocal, engine
from packages.db.models import Broker

settings = get_settings()


def _seed_static_data() -> None:
    """Data statis idempoten: preset broker (dijalankan saat startup)."""
    with SessionLocal() as db:
        if db.scalar(select(Broker).where(Broker.name == "HF Markets")) is None:
            db.add(Broker(name="HF Markets", server="HFMarketsGlobal-Demo", is_demo=True, popularity=10))
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _seed_static_data()
    yield
    engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(auth.router, prefix=settings.api_prefix)
    app.include_router(accounts.router, prefix=settings.api_prefix)
    app.include_router(connector.router, prefix=settings.api_prefix)
    app.include_router(dashboard.router, prefix=settings.api_prefix)
    return app


app = create_app()
