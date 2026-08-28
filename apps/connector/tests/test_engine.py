"""Integrasi: SyncEngine + FakeMT5 + server nyata (TestClient).

Gate Phase 4: sync end-to-end, idempoten, offline → outbox → resume 0 duplikat.
"""

from connector.client import ApiError, SyncEngine
from connector.mt5 import FakeMT5
from connector.outbox import Outbox

from packages.db import SessionLocal
from packages.db.models import Deal

from .conftest import setup_paired_user


class TestServerClient:
    """ApiClient menunjuk ke TestClient (transaksi HTTP via TestClient)."""

    def __init__(self, client, base="/api/v1/connector"):
        self._client = client
        self.base = base

    def _call(self, path, payload, headers):
        return self._client.post(path, json=payload, headers=headers)

    def pair(self, code, client_id, device_name="", version=""):
        r = self._client.post(f"{self.base}/pair", json={
            "code": code, "client_id": client_id, "device_name": device_name, "version": version,
        })
        return r.json()

    def heartbeat(self, device_id, device_key):
        import time

        r = self._client.post(f"{self.base}/heartbeat", headers={
            "X-Device-Id": str(device_id), "X-Device-Key": device_key,
            "X-Timestamp": str(int(time.time())), "X-Nonce": f"n-{device_id}-{time.time_ns()}",
        })
        assert r.status_code == 200, r.text
        return r.json()

    def sync(self, device_id, device_key, payload):
        import time

        r = self._client.post(f"{self.base}/sync", json=payload, headers={
            "X-Device-Id": str(device_id), "X-Device-Key": device_key,
            "X-Timestamp": str(int(time.time())), "X-Nonce": f"n-{device_id}-{time.time_ns()}",
        })
        if r.status_code >= 400:
            raise ApiError(r.status_code, r.text)
        return r.json()


def _engine(client, device_id, device_key, account, seed=7, tmp_path=None):
    api = TestServerClient(client)
    cfg = {
        "server_url": "http://test",
        "device_id": device_id, "device_key": device_key,
        "mt5_login": account["login"], "mt5_server": account["server"],
    }
    cfg["_path"] = str(tmp_path / "connector.json") if tmp_path else "/tmp/connector-test.json"
    mt5 = FakeMT5(login=account["login"], server=account["server"], seed=seed)
    outbox = Outbox(cfg["_path"])
    return SyncEngine(api, mt5, cfg, outbox=outbox), mt5


def test_engine_sync_end_to_end(client, tmp_path):
    token, device_id, device_key, account = setup_paired_user(client)
    engine, mt5 = _engine(client, device_id, device_key, account, tmp_path=tmp_path)
    mt5.seed_deals(40, days_back=30)
    mt5.seed_positions(2)

    result = engine.sync_once(device_id, device_key)
    assert result["accepted"] == 40
    assert result["duplicates"] == 0
    assert len(engine.outbox.all()) == 0

    with SessionLocal() as db:
        n = db.query(Deal).filter(Deal.trading_account_id == account["id"]).count()
    assert n == 40


def test_engine_sync_idempotent_second_run(client, tmp_path):
    token, device_id, device_key, account = setup_paired_user(client)
    engine, mt5 = _engine(client, device_id, device_key, account, tmp_path=tmp_path)
    mt5.seed_deals(25)
    engine.sync_once(device_id, device_key)

    # run kedua dengan data sama (FakeMT5 deterministik) → 0 accepted, 0 duplikat baru
    result2 = engine.sync_once(device_id, device_key)
    assert result2["duplicates"] == 0  # semua deal sudah masuk run pertama
    with SessionLocal() as db:
        n = db.query(Deal).filter(Deal.trading_account_id == account["id"]).count()
    assert n == 25


def test_offline_goes_to_outbox_then_resume(client, tmp_path, monkeypatch):
    """Server down → payload masuk outbox → server hidup → drain → 0 duplikat."""
    token, device_id, device_key, account = setup_paired_user(client)
    engine, mt5 = _engine(client, device_id, device_key, account, tmp_path=tmp_path)
    mt5.seed_deals(15)

    # simulasikan offline: sync pertama gagal → payload masuk outbox (tidak raise)
    orig_sync = TestServerClient.sync

    def boom(self, *a, **k):
        raise ApiError(503, "server down")

    monkeypatch.setattr(TestServerClient, "sync", boom)
    result = engine.sync_once(device_id, device_key)
    assert result.get("offline") is True
    monkeypatch.setattr(TestServerClient, "sync", orig_sync)

    assert len(engine.outbox.all()) == 1  # 1 batch tersimpan

    # online lagi → drain outbox
    sent, pending = engine.drain_outbox(device_id, device_key)
    assert sent == 1 and pending == 0
    with SessionLocal() as db:
        n = db.query(Deal).filter(Deal.trading_account_id == account["id"]).count()
    assert n == 15
    assert len(engine.outbox.all()) == 0


def test_run_loop_heartbeat_and_sync(client, tmp_path):
    token, device_id, device_key, account = setup_paired_user(client)
    engine, mt5 = _engine(client, device_id, device_key, account, tmp_path=tmp_path)
    mt5.seed_deals(10)
    engine.run(device_id, device_key, once=True)
    assert engine.state == "SYNCED"
