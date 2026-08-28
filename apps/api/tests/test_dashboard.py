"""Test Phase 5 — Dashboard & analytics API (BLUEPRINT §17, §35)."""


def _setup(client, username="dashuser", email="dash@example.com"):
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


def test_overview_kpis(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/overview", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["account_name"] == "Data Contoh"
    s = body["summary"]
    assert s["total_trades"] >= 120  # demo generator 120–220 trades
    assert s["win_rate"] is not None and 0 <= s["win_rate"] <= 100
    assert s["profit_factor"] is not None
    assert s["net_profit"] != 0
    assert body["currency"] == "USD"
    assert body["open_positions"] >= 1


def test_overview_requires_owner_404(client):
    token_a, h_a, acc_a = _setup(client)
    client.post(
        "/api/v1/auth/register",
        json={"username": "other", "email": "other@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "other@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    r = client.get(
        f"/api/v1/accounts/{acc_a['id']}/overview",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


def test_equity_curve_from_snapshots(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/equity", headers=h)
    assert r.status_code == 200
    points = r.json()
    assert len(points) >= 40  # snapshot harian demo ≥ 40 hari
    assert all(p["equity"] > 0 for p in points)
    # urut naik waktu
    assert points[0]["ts"] < points[-1]["ts"]


def test_calendar_heatmap(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/calendar", headers=h)
    assert r.status_code == 200
    days = r.json()
    assert len(days) >= 40
    assert all("net_profit" in d and "trades" in d for d in days)
    # filter bulan
    month = days[-1]["day"][:7]
    r2 = client.get(f"/api/v1/accounts/{acc['id']}/calendar?month={month}", headers=h)
    assert all(d["day"][:7] == month for d in r2.json())


def test_trades_list_and_filters(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/trades?limit=25", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 120
    assert len(body["items"]) == 25
    t = body["items"][0]
    assert t["symbol"] and t["side"] in ("buy", "sell") and t["net_profit"] is not None

    # filter result=win
    r2 = client.get(f"/api/v1/accounts/{acc['id']}/trades?result=win", headers=h)
    assert all(i["net_profit"] > 0 for i in r2.json()["items"])
    # filter side=sell
    r3 = client.get(f"/api/v1/accounts/{acc['id']}/trades?side=sell", headers=h)
    assert all(i["side"] == "sell" for i in r3.json()["items"])
    # pagination: halaman kedua (offset 25) ≠ halaman pertama
    r4 = client.get(f"/api/v1/accounts/{acc['id']}/trades?limit=25&offset=25", headers=h)
    assert r4.json()["items"][0]["id"] != body["items"][-1]["id"]


def test_monthly_statistics(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/monthly", headers=h)
    assert r.status_code == 200
    months = r.json()
    assert len(months) >= 2  # span 60–90 hari minimal 2 bulan
    m = months[-1]
    assert m["month"] and m["total_trades"] > 0


def test_positions_endpoint(client):
    token, h, acc = _setup(client)
    r = client.get(f"/api/v1/accounts/{acc['id']}/positions", headers=h)
    assert r.status_code == 200
    poss = r.json()
    assert 1 <= len(poss) <= 3
    assert poss[0]["symbol"] and poss[0]["floating_pnl"] is not None


def test_aggregate_overview(client):
    token, h, acc = _setup(client)
    r = client.get("/api/v1/accounts/overview", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["accounts"] == 1
    assert body["open_positions"] >= 1
    assert body["net_profit_total"] is not None
