"""Test Phase 7 — Export CSV (BLUEPRINT §27 versi MVP sinkron)."""
import csv
import io


def _setup(client, username="expuser", email="exp@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "rahasia123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    acc = client.post(
        "/api/v1/accounts", json={"kind": "demo", "name": "Data Contoh"}, headers=h
    ).json()
    return token, h, acc


def test_export_trades_csv(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/export/trades.csv", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    text = r.text
    assert text.startswith("\ufeff")  # BOM UTF-8 untuk Excel
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    rows = list(reader)
    assert len(rows) >= 120  # demo generator 120–220 trades
    first = rows[0]
    assert {"ticket", "symbol", "side", "volume", "net_profit", "close_time"} <= set(first)
    assert first["side"] in ("buy", "sell")


def test_export_journal_csv(client):
    token, h, acc = _setup(client)
    # buat 2 jurnal supaya export bermakna
    for i in range(2):
        client.post(
            "/api/v1/journal",
            json={
                "trading_account_id": acc["id"],
                "entry_date": f"2025-07-0{i+1}T10:00:00+00:00",
                "setup": "Breakout", "notes": f"catatan {i}",
                "tags": ["breakout"],
            },
            headers=h,
        )
    r = client.get(f"/api/v1/accounts/{acc['id']}/export/journal.csv", headers=h)
    assert r.status_code == 200
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("\ufeff"))))
    # 2 jurnal baru + jurnal bawaan demo generator (6–10) + 2 buatan = total ≥ 8
    assert len(rows) >= 8
    assert "notes" in rows[0] and "tags" in rows[0] and "trade_symbol" in rows[0]


def test_export_cross_user_404(client):
    token_a, h_a, acc_a = _setup(client)
    client.post(
        "/api/v1/auth/register",
        json={"username": "expB", "email": "expb@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "expb@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    r = client.get(
        f"/api/v1/accounts/{acc_a['id']}/export/trades.csv",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
