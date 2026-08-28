"""Aplikasi FastAPI — factory + middleware.

Phase 0–1: healthz, CORS, structured logging. Router fitur menyusul per fase.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.app.middleware import RequestLoggingMiddleware
from apps.api.app.routers import health
from packages.config import get_settings
from packages.db import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
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
    app.add_middleware(RequestLoggingMiddleware)
    app.include_router(health.router, prefix=settings.api_prefix)
    return app


app = create_app()
