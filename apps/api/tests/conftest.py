"""Fixtures pytest — env test (sqlite) di-set SEBELUM import app."""
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{ROOT / '.test.db'}")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from apps.api.app.main import app  # noqa: E402
from packages.db import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(engine)  # DB test selalu fresh tiap run
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
