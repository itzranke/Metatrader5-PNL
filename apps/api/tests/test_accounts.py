"""Test Phase 3 — Trading Accounts & demo generator (BLUEPRINT §35)."""
import time

from packages.db import SessionLocal
from packages.db.models import (
    BalanceSnapshot,
    DailyStatistic,
    EquitySnapshot,
    JournalEntry,
    Position,
    Tag,
    Trade,
)


def _register(client, username="akun", email="akun@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "rahasia123"},
    )
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def test_accounts_empty_list(client):
    token = _register(client)
    r = client.get("/api/v1/accounts", headers=_h(token))
    assert r.status_code == 200
    assert r.json() == []


def test_create_mt5_account(client):
    token = _register(client)
    r = client.post(
        "/api/v1/accounts",
        json={"name": "Akun Utama", "login": "12345678", "server": "HFMarketsGlobal-Demo", "kind": "mt5"},
        headers=_h(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "mt5"
    assert body["login"] == "12345678"
    assert body["connection_state"] is None


def test_create_account_missing_login_422(client):
    token = _register(client)
    r = client.post("/api/v1/accounts", json={"kind": "mt5"}, headers=_h(token))
    assert r.status_code == 422


def test_duplicate_login_server_409(client):
    token = _register(client)
    payload = {"login": "777", "server": "Srv", "kind": "mt5"}
    assert client.post("/api/v1/accounts", json=payload, headers=_h(token)).status_code == 201
    assert client.post("/api/v1/accounts", json=payload, headers=_h(token)).status_code == 409


def test_quota_2_accounts_409(client):
    token = _register(client)
    for i in range(2):
        r = client.post(
            "/api/v1/accounts",
            json={"login": f"100{i}", "server": "Srv", "kind": "mt5"},
            headers=_h(token),
        )
        assert r.status_code == 201
    r = client.post(
        "/api/v1/accounts", json={"login": "999", "server": "Srv", "kind": "mt5"}, headers=_h(token)
    )
    assert r.status_code == 409


def test_demo_account_generates_data_fast(client):
    """Acceptance Phase 3: akun demo 60–90 hari data, dibuat <5 detik."""
    token = _register(client)
    t0 = time.perf_counter()
    r = client.post(
        "/api/v1/accounts", json={"kind": "demo", "name": "Data Contoh"}, headers=_h(token)
    )
    elapsed = time.perf_counter() - t0
    assert r.status_code == 201, r.text
    assert elapsed < 5.0
    acc = r.json()
    assert acc["kind"] == "demo"
    assert acc["server"] == "Synthetic"

    with SessionLocal() as db:
        n_trades = db.query(Trade).filter(Trade.trading_account_id == acc["id"]).count()
        n_equity = db.query(EquitySnapshot).filter(EquitySnapshot.trading_account_id == acc["id"]).count()
        n_balance = db.query(BalanceSnapshot).filter(BalanceSnapshot.trading_account_id == acc["id"]).count()
        n_stats = db.query(DailyStatistic).filter(DailyStatistic.trading_account_id == acc["id"]).count()
        n_journal = db.query(JournalEntry).filter(JournalEntry.trading_account_id == acc["id"]).count()
        n_tags = db.query(Tag).filter(Tag.user_id == 1).count()
        n_positions = db.query(Position).filter(Position.trading_account_id == acc["id"]).count()

    assert 120 <= n_trades <= 220, f"trades={n_trades}"
    # 60–90 hari kalender → ~43–64 hari trading (weekend tanpa snapshot)
    assert n_equity >= 40 and n_balance >= 40
    assert n_stats >= 40
    assert n_journal >= 6
    assert n_tags >= 3
    assert 1 <= n_positions <= 3


def test_demo_account_single_per_user(client):
    token = _register(client)
    assert client.post("/api/v1/accounts", json={"kind": "demo"}, headers=_h(token)).status_code == 201
    r = client.post("/api/v1/accounts", json={"kind": "demo"}, headers=_h(token))
    assert r.status_code == 409


def test_demo_does_not_count_against_quota(client):
    """Quota 2 akun MT5; akun demo terpisah."""
    token = _register(client)
    assert client.post("/api/v1/accounts", json={"kind": "demo"}, headers=_h(token)).status_code == 201
    for i in range(2):
        r = client.post(
            "/api/v1/accounts",
            json={"login": f"200{i}", "server": "Srv", "kind": "mt5"},
            headers=_h(token),
        )
        assert r.status_code == 201


def test_patch_and_delete_account(client):
    token = _register(client)
    acc = client.post(
        "/api/v1/accounts", json={"login": "555", "server": "Srv", "kind": "mt5"}, headers=_h(token)
    ).json()
    r = client.patch(f"/api/v1/accounts/{acc['id']}", json={"name": "Ganti Nama"}, headers=_h(token))
    assert r.status_code == 200
    assert r.json()["name"] == "Ganti Nama"
    assert client.delete(f"/api/v1/accounts/{acc['id']}", headers=_h(token)).status_code == 204
    assert client.get("/api/v1/accounts", headers=_h(token)).json() == []


def test_cross_user_account_404(client):
    """Multi-tenant: user B tidak bisa PATCH/DELETE akun user A."""
    token_a = _register(client, username="userA", email="aa@example.com")
    acc_a = client.post(
        "/api/v1/accounts", json={"login": "111", "server": "Srv", "kind": "mt5"}, headers=_h(token_a)
    ).json()

    token_b = _register(client, username="userB", email="bb@example.com")
    assert client.patch(f"/api/v1/accounts/{acc_a['id']}", json={"name": "Hack"}, headers=_h(token_b)).status_code == 404
    assert client.delete(f"/api/v1/accounts/{acc_a['id']}", headers=_h(token_b)).status_code == 404
    # list B tidak menampilkan akun A
    assert client.get("/api/v1/accounts", headers=_h(token_b)).json() == []


def test_broker_presets_hf(client):
    token = _register(client)
    r = client.get("/api/v1/meta/broker-presets", headers=_h(token))
    assert r.status_code == 200
    hf = next(p for p in r.json() if p["name"] == "HF Markets Demo")
    assert hf["login"] == "49155931"
    assert hf["server"] == "HFMarketsGlobal-Demo"
