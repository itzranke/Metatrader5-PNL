"""Test Phase 9 — MAE/MFE analytics + sync excursions (BLUEPRINT §14).

Gate: endpoint mae-mfe tenant-safe; excursions dari connector tersimpan ke
positions (live) & mae_mfe_records (trade tertutup) secara idempoten.
"""
import time
from datetime import UTC, datetime, timedelta

from packages.db import SessionLocal
from packages.db.models import MaeMfeRecord, Position, Trade, TradingAccount


def _register_demo(client, username="mm9", email="mm9@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "rahasia123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]
    acc = client.post(
        "/api/v1/accounts", json={"kind": "demo", "name": "Demo MM"}, headers={"Authorization": f"Bearer {token}"}
    ).json()
    return token, acc


def _pair(client, token):
    code = client.post(
        "/api/v1/connector/pair-request", headers={"Authorization": f"Bearer {token}"}
    ).json()["code"]
    r = client.post(
        "/api/v1/connector/pair",
        json={"code": code, "client_id": "cli-mm-1", "device_name": "PC", "version": "0.1.0"},
    )
    assert r.status_code == 200, r.text
    return r.json()["device_id"], r.json()["device_key"]


def _hdrs(device_id, device_key):
    return {
        "X-Device-Id": str(device_id),
        "X-Device-Key": device_key,
        "X-Timestamp": str(int(time.time())),
        "X-Nonce": f"n-{int(time.time() * 1000)}",
    }


def _sync(client, device_id, device_key, acc, payload):
    payload.setdefault("login", acc["login"])
    payload.setdefault("server", acc["server"])
    payload.setdefault("kind", "full")
    payload.setdefault("deals", [])
    payload.setdefault("positions", [])
    payload.setdefault("excursions", [])
    return client.post("/api/v1/connector/sync", json=payload, headers=_hdrs(device_id, device_key))


# ---------------------------------------------------------------- analytics API


def test_mae_mfe_analytics_demo_account(client):
    token, acc = _register_demo(client)
    r = client.get(
        f"/api/v1/accounts/{acc['id']}/analytics/mae-mfe",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    s = body["summary"]
    assert s["covered"] >= 120  # semua trade demo punya record
    assert s["source_counts"]["ticks"] > 0
    assert s["source_counts"]["candles"] > 0
    assert s["source_counts"]["none"] > 0
    assert s["avg_mae_pct"] is not None and s["avg_mfe_pct"] is not None
    assert s["avg_mfe_pct"] > s["avg_mae_pct"]  # MFE rata-rata > MAE (normal)
    assert s["ratio_mae_mfe"] is not None and 0 < s["ratio_mae_mfe"] < 1
    assert s["avg_mae_r"] is not None and s["avg_mfe_r"] is not None
    assert len(s["buckets_mae"]) == 5 and len(s["buckets_mfe"]) == 5
    assert sum(b["count"] for b in s["buckets_mae"]) == s["covered"]
    assert len(body["items"]) >= 120
    item = body["items"][0]
    assert item["path_source"] in ("ticks", "candles", "none")
    assert item["mae_pts"] is not None and item["mfe_pts"] is not None
    assert item["net_profit"] is not None and item["symbol"]


def test_mae_mfe_cross_user_404(client):
    token_a, acc_a = _register_demo(client)
    client.post(
        "/api/v1/auth/register",
        json={"username": "mm9b", "email": "mm9b@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "mm9b@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    r = client.get(
        f"/api/v1/accounts/{acc_a['id']}/analytics/mae-mfe",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------- sync excursions


def test_sync_excursions_live_position(client):
    token, acc = _register_demo(client)
    device_id, device_key = _pair(client, token)
    payload = {
        "last_ticket": "1",
        "positions": [{
            "ticket": "9001", "symbol": "EURUSD", "side": "buy", "volume": 0.5,
            "open_price": 1.1000, "open_time": "2025-06-01T08:00:00+00:00",
            "current_price": 1.1010, "floating_pnl": 25.0, "sl": None, "tp": None,
        }],
        "excursions": [{"ticket": "9001", "mae_pts": 0.0015, "mfe_pts": 0.0040, "samples": 7}],
    }
    r = _sync(client, device_id, device_key, acc, payload)
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        pos = db.query(Position).filter_by(trading_account_id=acc["id"], ticket="9001").first()
        assert pos is not None
        assert float(pos.mae) == 0.0015 and float(pos.mfe) == 0.0040

    # kirim ulang dengan mae lebih besar → akumulasi live di server
    payload["excursions"] = [{"ticket": "9001", "mae_pts": 0.0022, "mfe_pts": 0.0040, "samples": 14}]
    r2 = _sync(client, device_id, device_key, acc, payload)
    assert r2.status_code == 200
    with SessionLocal() as db:
        pos = db.query(Position).filter_by(trading_account_id=acc["id"], ticket="9001").first()
        assert float(pos.mae) == 0.0022 and float(pos.mfe) == 0.0040


def test_sync_excursions_closed_trade_idempotent(client):
    token, acc = _register_demo(client)
    device_id, device_key = _pair(client, token)
    now = datetime.now(UTC)
    with SessionLocal() as db:
        user_id = db.query(TradingAccount).filter_by(id=acc["id"]).first().user_id
        trade = Trade(
            user_id=user_id, trading_account_id=acc["id"], ticket="7777",
            symbol="EURUSD", side="buy", volume=0.1,
            open_price=1.1000, close_price=1.1050,
            open_time=now - timedelta(hours=2), close_time=now,
            net_profit=25.0, gross_profit=25.0, risk_amount=50.0, source="sync",
        )
        db.add(trade)
        db.commit()
        trade_id = trade.id

    ex = {"ticket": "7777", "mae_pts": 0.0008, "mfe_pts": 0.0060,
          "mae_currency": -3.0, "mfe_currency": 22.0, "samples": 12}
    r = _sync(client, device_id, device_key, acc, {"last_ticket": "1", "excursions": [ex]})
    assert r.status_code == 200, r.text
    with SessionLocal() as db:
        rec = db.query(MaeMfeRecord).filter_by(trade_id=trade_id).first()
        assert rec is not None
        assert rec.path_source == "ticks" and rec.samples == 12
        assert float(rec.mae_pts) == 0.0008 and float(rec.mfe_pts) == 0.0060
        assert float(rec.mae_currency) == -3.0 and float(rec.mfe_currency) == 22.0
        # mae_pct = pts/open_price*100; mae_r = currency/risk
        assert abs(float(rec.mae_pct) - 0.0008 / 1.1 * 100) < 1e-6
        assert abs(float(rec.mae_r) - 3.0 / 50.0) < 1e-6
        t = db.query(Trade).filter_by(id=trade_id).first()
        assert float(t.mae) == -3.0 and float(t.mfe) == 22.0
        assert abs(float(t.mae_pct) - 0.0008 / 1.1 * 100) < 1e-6

    # idempoten: kirim ulang → record tetap 1, samples naik ke max
    r2 = _sync(client, device_id, device_key, acc, {"last_ticket": "1", "excursions": [ex]})
    assert r2.status_code == 200
    with SessionLocal() as db:
        assert db.query(MaeMfeRecord).filter_by(trade_id=trade_id).count() == 1
        rec = db.query(MaeMfeRecord).filter_by(trade_id=trade_id).first()
        assert rec.samples == 12
        # excursions ticket tak dikenal → dilewati aman, tidak error
    r3 = _sync(client, device_id, device_key, acc, {
        "last_ticket": "1",
        "excursions": [{"ticket": "99999", "mae_pts": 0.1, "mfe_pts": 0.2, "samples": 1}],
    })
    assert r3.status_code == 200
