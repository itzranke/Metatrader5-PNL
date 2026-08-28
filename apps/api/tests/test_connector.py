"""Test Phase 4 — Connector: pairing, device auth, sync idempoten (BLUEPRINT §8, §35).

Gate: pairing flow aman (kode sekali pakai, TTL), sync 10k deal 0 duplikat,
anti-replay nonce, multi-tenant, akun hanya bisa dipair 1 device.
"""
import time
from datetime import UTC

from apps.api.app.core.security import hash_password  # noqa: F401 (import path sanity)
from packages.db import SessionLocal
from packages.db.models import ConnectorDevice, Deal, MT5Connection, Position


def _register_and_account(client, username="userX", email="userx@example.com", login="12345678"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "rahasia123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]
    acc = client.post(
        "/api/v1/accounts",
        json={"name": "Akun", "login": login, "server": "Srv-Demo", "kind": "mt5"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return token, acc


def _pair(client, token, code=None, client_id="cli-test-0001"):
    """Helper: buat kode pairing → pair → kembalikan (device_id, device_key)."""
    if code is None:
        code = client.post("/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"}).json()["code"]
    r = client.post(
        "/api/v1/connector/pair",
        json={"code": code, "client_id": client_id, "device_name": "PC Test", "version": "0.1.0"},
    )
    assert r.status_code == 200, r.text
    return r.json()["device_id"], r.json()["device_key"]


def _hdrs(device_id, device_key, nonce=None):
    return {
        "X-Device-Id": str(device_id),
        "X-Device-Key": device_key,
        "X-Timestamp": str(int(time.time())),
        "X-Nonce": nonce or f"n-{int(time.time() * 1000)}-{id(device_id)}",
    }


def _deal(ticket: int, price: float = 1.1, profit: float = 0.0, **kw) -> dict:
    return {
        "deal_ticket": str(ticket),
        "order_ticket": str(ticket),
        "time": "2025-06-01T10:00:00+00:00",
        "type": 0,
        "symbol": "EURUSD",
        "volume": 0.1,
        "price": price,
        "profit": profit,
        "swap": 0.0,
        "commission": 0.0,
        "comment": "",
        **kw,
    }


def test_pair_request_and_pair_flow(client):
    token, _ = _register_and_account(client)
    r = client.post("/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 201
    code = r.json()["code"]
    assert len(code) == 8 and code.isdigit()

    device_id, device_key = _pair(client, token, code=code)
    assert len(device_key) == 64  # 32 byte hex

    # kode sekali pakai — pair kedua dengan code sama harus gagal
    r2 = client.post(
        "/api/v1/connector/pair",
        json={"code": code, "client_id": "cli-test-0002"},
    )
    assert r2.status_code == 401

    # device tanpa auth → 401
    assert client.post("/api/v1/connector/heartbeat").status_code == 401
    # auth salah → 401
    assert client.post("/api/v1/connector/heartbeat", headers=_hdrs(device_id, "salah" * 16)).status_code == 401


def test_pair_code_ttl_and_replay_nonce(client):
    token, _ = _register_and_account(client)
    code = client.post("/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"}).json()["code"]

    # kedaluwarsa: set pairing_expires_at ke masa lalu
    with SessionLocal() as db:
        dev = db.query(ConnectorDevice).filter_by(state="PAIRING").first()
        from datetime import datetime, timedelta

        dev.pairing_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    r = client.post(
        "/api/v1/connector/pair", json={"code": code, "client_id": "cli-ttl-01"}
    )
    assert r.status_code == 401

    # replay nonce → 409
    device_id, device_key = _pair(client, token)
    h = _hdrs(device_id, device_key, nonce="nonce-replay-1")
    assert client.post("/api/v1/connector/heartbeat", headers=h).status_code == 200
    assert client.post("/api/v1/connector/heartbeat", headers=h).status_code == 409

    # timestamp basi (>120 dtk) → 401
    h2 = _hdrs(device_id, device_key)
    h2["X-Timestamp"] = str(int(time.time()) - 300)
    assert client.post("/api/v1/connector/heartbeat", headers=h2).status_code == 401


def test_heartbeat_updates_last_seen(client):
    token, _ = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    r = client.post("/api/v1/connector/heartbeat", headers=_hdrs(device_id, device_key))
    assert r.status_code == 200
    assert r.json()["ok"] is True
    with SessionLocal() as db:
        dev = db.get(ConnectorDevice, device_id)
        assert dev.last_seen_at is not None
        assert dev.state == "CONNECTED"


def test_sync_ingest_and_idempotent_duplicates(client):
    token, acc = _register_and_account(client)
    device_id, device_key = _pair(client, token)

    payload = {
        "login": acc["login"],
        "server": acc["server"],
        "kind": "full",
        "last_ticket": "105",
        "deals": [_deal(i, profit=10.0) for i in range(100, 106)],
        "positions": [
            {
                "ticket": "9001", "symbol": "EURUSD", "side": "buy", "volume": 0.5,
                "open_price": 1.1000, "open_time": "2025-06-01T08:00:00+00:00",
                "current_price": 1.1010, "floating_pnl": 25.0, "sl": None, "tp": None,
            }
        ],
    }
    r = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 6 and body["duplicates"] == 0
    assert body["last_ticket"] == "105" and body["state"] == "SYNCED"

    # kirim batch SAMA lagi (simulasi retry offline) → 0 accepted, 6 duplikat
    r2 = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))
    assert r2.status_code == 200
    assert r2.json()["accepted"] == 0 and r2.json()["duplicates"] == 6

    # kirim batch campur (3 baru + 3 lama) → hanya yang baru masuk
    payload["deals"] = [_deal(i, profit=1.0) for i in range(103, 109)]
    payload["last_ticket"] = "108"
    r3 = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))
    assert r3.json()["accepted"] == 3 and r3.json()["duplicates"] == 3

    with SessionLocal() as db:
        assert db.query(Deal).filter(Deal.trading_account_id == acc["id"]).count() == 9
        conn = db.query(MT5Connection).filter_by(trading_account_id=acc["id"]).first()
        assert conn is not None and conn.state == "SYNCED"
        assert conn.last_deal_ticket == "108"
        assert db.query(Position).filter(Position.trading_account_id == acc["id"]).count() == 1


def test_sync_10k_deals_zero_duplicate(client):
    """Gate Phase 4: 10.000 deal tersinkron, 0 duplikat, dalam batch 500."""
    token, acc = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    t0 = time.perf_counter()
    for batch in range(20):
        start = 100000 + batch * 500
        payload = {
            "login": acc["login"],
            "server": acc["server"],
            "kind": "full",
            "last_ticket": str(start + 499),
            "deals": [_deal(i, profit=float(i % 7)) for i in range(start, start + 500)],
            "positions": [],
        }
        r = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))
        assert r.status_code == 200, r.text
        assert r.json()["duplicates"] == 0
    elapsed = time.perf_counter() - t0
    with SessionLocal() as db:
        total = db.query(Deal).filter(Deal.trading_account_id == acc["id"]).count()
    assert total == 10000, f"total={total}"
    # 20 batch × 500 deal harusnya selesai dalam waktu wajar
    assert elapsed < 60, f"10k deals terlalu lambat: {elapsed:.1f}s"


def test_sync_requires_registered_account_404(client):
    token, _ = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    payload = {"login": "99999999", "server": "TidakAda", "kind": "full", "deals": [], "positions": []}
    r = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))
    assert r.status_code == 404


def test_sync_wrong_device_auth_401(client):
    token, _ = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    r = client.post(
        "/api/v1/connector/sync",
        json={"login": "1", "server": "Srv", "kind": "full", "deals": [], "positions": []},
        headers=_hdrs(device_id, "0" * 64),
    )
    assert r.status_code == 401


def test_position_close_diff(client):
    """Posisi yang hilang dari snapshot = ditutup otomatis."""
    token, acc = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    pos = {
        "ticket": "777", "symbol": "GBPUSD", "side": "sell", "volume": 0.2,
        "open_price": 1.2500, "open_time": "2025-06-01T08:00:00+00:00",
        "current_price": 1.2490, "floating_pnl": 20.0, "sl": None, "tp": None,
    }
    r = client.post(
        "/api/v1/connector/sync",
        json={"login": acc["login"], "server": acc["server"], "kind": "full", "deals": [], "positions": [pos]},
        headers=_hdrs(device_id, device_key),
    )
    assert r.json()["closed_positions"] == 0
    # snapshot berikutnya tanpa posisi itu → ditutup
    r2 = client.post(
        "/api/v1/connector/sync",
        json={"login": acc["login"], "server": acc["server"], "kind": "full", "deals": [], "positions": []},
        headers=_hdrs(device_id, device_key),
    )
    assert r2.json()["closed_positions"] == 1
    with SessionLocal() as db:
        assert db.query(Position).filter(Position.trading_account_id == acc["id"]).count() == 0


def test_account_cannot_be_claimed_by_second_device(client):
    """Conflict §8.5: dua device tidak boleh klaim akun sama."""
    token, acc = _register_and_account(client)
    device_a = _pair(client, token)
    # pair device kedua (kode baru)
    code = client.post("/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"}).json()["code"]
    r = client.post(
        "/api/v1/connector/pair",
        json={"code": code, "client_id": "cli-test-0002", "device_name": "PC Kedua"},
    )
    device_b = (r.json()["device_id"], r.json()["device_key"])

    payload = {"login": acc["login"], "server": acc["server"], "kind": "full", "deals": [], "positions": []}
    assert client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(*device_a)).status_code == 200
    r2 = client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(*device_b))
    assert r2.status_code == 409


def test_sync_cross_user_account_404(client):
    """Multi-tenant: device user A tidak bisa sync ke akun user B."""
    token_a, acc_a = _register_and_account(client, username="userA2", email="a2@example.com")
    token_b, _ = _register_and_account(client, username="userB2", email="b2@example.com", login="87654321")
    device_id, device_key = _pair(client, token_b)
    r = client.post(
        "/api/v1/connector/sync",
        json={"login": acc_a["login"], "server": acc_a["server"], "kind": "full", "deals": [], "positions": []},
        headers=_hdrs(device_id, device_key),
    )
    assert r.status_code == 404


def test_devices_list_web(client):
    token, _ = _register_and_account(client)
    device_id, device_key = _pair(client, token)
    client.post("/api/v1/connector/heartbeat", headers=_hdrs(device_id, device_key))
    r = client.get("/api/v1/connector/devices", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["state"] == "CONNECTED"
