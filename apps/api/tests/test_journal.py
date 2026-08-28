"""Test Phase 6 — Jurnal Trading (CRUD, tags, screenshot, tenant)."""
import io

from packages.db import SessionLocal
from packages.db.models import Tag


def _setup(client, username="juser", email="juser@example.com"):
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


def _payload(acc_id, **kw):
    return {
        "trading_account_id": acc_id,
        "entry_date": "2025-07-01T10:00:00+00:00",
        "setup": "Breakout",
        "emotion_before": "calm",
        "emotion_during": "focused",
        "emotion_after": "satisfied",
        "confidence": 4,
        "discipline": 4,
        "notes": "Menunggu konfirmasi candle.",
        "reason_entry": "Breakout level harian",
        "reason_exit": "TP tercapai",
        "lesson": "Disiplin membayar.",
        "tags": ["breakout", "harian"],
        **kw,
    }


def test_create_journal_with_tags(client):
    token, h, acc = _setup(client)
    r = client.post("/api/v1/journal", json=_payload(acc["id"]), headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["setup"] == "breakout"  # dinormalisasi lowercase
    assert set(body["tags"]) == {"breakout", "harian"}
    assert body["confidence"] == 4
    with SessionLocal() as db:
        # tag dari jurnal + tag bawaan demo generator (breakout/harian) ada
        assert db.query(Tag).filter(Tag.user_id == 1, Tag.name.in_(["breakout", "harian"])).count() == 2


def test_journal_linked_to_trade(client):
    token, h, acc = _setup(client)
    trade = client.get(f"/api/v1/accounts/{acc['id']}/trades?limit=1", headers=h).json()["items"][0]
    r = client.post(
        "/api/v1/journal",
        json={**_payload(acc["id"]), "trade_id": trade["id"]},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["trade_id"] == trade["id"]
    assert body["trade_symbol"] == trade["symbol"]
    assert body["trade_net_profit"] is not None


def test_journal_cross_account_trade_404(client):
    """Trade dari akun lain tidak bisa dipakai di jurnal akun ini."""
    token, h, acc = _setup(client)
    # akun kedua (quota demo 1 — pakai akun mt5 kedua)
    acc2 = client.post(
        "/api/v1/accounts",
        json={"name": "A2", "login": "87654321", "server": "Srv2", "kind": "mt5"},
        headers=h,
    ).json()
    trade_a1 = client.get(f"/api/v1/accounts/{acc['id']}/trades?limit=1", headers=h).json()["items"][0]
    r = client.post(
        "/api/v1/journal",
        json={**_payload(acc2["id"]), "trade_id": trade_a1["id"]},
        headers=h,
    )
    assert r.status_code == 404


def test_update_and_delete_journal(client):
    token, h, acc = _setup(client)
    entry = client.post("/api/v1/journal", json=_payload(acc["id"]), headers=h).json()
    r = client.patch(
        f"/api/v1/journal/{entry['id']}",
        json={"notes": "Revisi: exit terlalu cepat.", "tags": ["retest"]},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["notes"] == "Revisi: exit terlalu cepat."
    assert body["tags"] == ["retest"]
    assert client.delete(f"/api/v1/journal/{entry['id']}", headers=h).status_code == 204
    assert client.get(f"/api/v1/journal/{entry['id']}", headers=h).status_code == 404


def test_journal_list_and_filters(client):
    token, h, acc = _setup(client)
    client.post("/api/v1/journal", json=_payload(acc["id"]), headers=h)
    client.post(
        "/api/v1/journal",
        json={**_payload(acc["id"]), "setup": "Retest", "tags": ["retest"]},
        headers=h,
    )
    all_rows = client.get("/api/v1/journal", headers=h).json()
    assert len(all_rows) >= 2
    by_setup = client.get("/api/v1/journal?setup=retest", headers=h).json()
    assert len(by_setup) == 1 and by_setup[0]["setup"] == "retest"
    by_tag = client.get("/api/v1/journal?tag=breakout", headers=h).json()
    assert all("breakout" in e["tags"] for e in by_tag)
    by_month = client.get("/api/v1/journal?month=2025-07", headers=h).json()
    assert len(by_month) >= 2


def test_journal_cross_user_404(client):
    token_a, h_a, acc_a = _setup(client, username="userjA", email="ja@example.com")
    entry = client.post("/api/v1/journal", json=_payload(acc_a["id"]), headers=h_a).json()
    client.post(
        "/api/v1/auth/register",
        json={"username": "userjB", "email": "jb@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "jb@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    h_b = {"Authorization": f"Bearer {token_b}"}
    assert client.get(f"/api/v1/journal/{entry['id']}", headers=h_b).status_code == 404
    assert client.patch(f"/api/v1/journal/{entry['id']}", json={"notes": "x"}, headers=h_b).status_code == 404
    assert client.delete(f"/api/v1/journal/{entry['id']}", headers=h_b).status_code == 404


def test_screenshot_upload(client, tmp_path, monkeypatch):
    token, h, acc = _setup(client)
    entry = client.post("/api/v1/journal", json=_payload(acc["id"]), headers=h).json()
    # arahkan upload_dir ke tmp agar tidak mengotori repo
    monkeypatch.setattr("apps.api.app.routers.journal.get_settings", lambda: type(
        "S", (), {"upload_dir": str(tmp_path)}
    )())
    r = client.post(
        f"/api/v1/journal/{entry['id']}/screenshot",
        files={"file": ("chart.png", io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "image/png")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["screenshot_path"].endswith(".png")
    # file benar-benar tersimpan
    files = list(tmp_path.iterdir())
    assert len(files) == 1
    # format tidak didukung → 422
    r2 = client.post(
        f"/api/v1/journal/{entry['id']}/screenshot",
        files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=h,
    )
    assert r2.status_code == 422


def test_tags_crud(client):
    token, h, acc = _setup(client)
    r = client.post("/api/v1/tags", json={"name": "  News  ", "color": "#ff0000"}, headers=h)
    assert r.status_code == 201
    assert r.json()["name"] == "news"  # lowercase + strip
    # duplikat → update warna, bukan error
    r2 = client.post("/api/v1/tags", json={"name": "news", "color": "#00ff00"}, headers=h)
    assert r2.status_code == 201 and r2.json()["color"] == "#00ff00"
    tags = client.get("/api/v1/tags", headers=h).json()
    news = [t for t in tags if t["name"] == "news"]
    assert len(news) == 1 and news[0]["color"] == "#00ff00"
