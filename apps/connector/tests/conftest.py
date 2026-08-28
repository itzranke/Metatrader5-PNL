"""Fixtures pytest connector — env sqlite + TestClient server nyata."""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))  # repo root → apps.api, packages
sys.path.insert(0, str(ROOT / "apps" / "connector"))  # package `connector`

os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / '.test.db'}")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.app.core.ratelimit import get_limiter  # noqa: E402
from apps.api.app.main import app  # noqa: E402
from packages.db import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    limiter = get_limiter()
    if hasattr(limiter, "reset"):
        limiter.reset()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def setup_paired_user(client, login="12345678", server="Srv-Demo", email="conn@example.com"):
    """Register + akun + pair connector → (token, device_id, device_key, account)."""
    client.post(
        "/api/v1/auth/register",
        json={"username": "connuser", "email": email, "password": "rahasia123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]
    acc = client.post(
        "/api/v1/accounts",
        json={"name": "Akun", "login": login, "server": server, "kind": "mt5"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    code = client.post(
        "/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]
    r = client.post(
        "/api/v1/connector/pair",
        json={"code": code, "client_id": "cli-conn-test-1", "device_name": "PC"},
    )
    assert r.status_code == 200, r.text
    dev = r.json()
    return token, dev["device_id"], dev["device_key"], acc
