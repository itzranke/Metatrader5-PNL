"""Test Phase 2 — Authentication (BLUEPRINT §35 acceptance)."""


def _register(client, username="andi", email="andi@example.com", password="rahasia123"):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert r.status_code == 201, r.text
    return r


def _login(client, email="andi@example.com", password="rahasia123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- register


def test_register_success(client):
    _register(client)


def test_register_duplicate_email_409(client):
    _register(client)
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "orang2", "email": "andi@example.com", "password": "rahasia123"},
    )
    assert r.status_code == 409


def test_register_weak_password_422(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "lemah", "email": "lemah@example.com", "password": "pendek"},
    )
    assert r.status_code == 422


def test_register_invalid_username_422(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"username": "spasi jelek", "email": "x@example.com", "password": "rahasia123"},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------- login & session


def test_login_wrong_password_401(client):
    _register(client)
    r = client.post(
        "/api/v1/auth/login", json={"email": "andi@example.com", "password": "salah12345"}
    )
    assert r.status_code == 401


def test_login_success_sets_http_only_cookie(client):
    _register(client)
    r = _login(client)
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == "andi@example.com"
    assert body["user"]["email_verified"] is False
    set_cookie = r.headers.get("set-cookie", "")
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" not in set_cookie  # dev/test: non-secure


def test_me_with_bearer(client):
    _register(client)
    token = _login(client).json()["access_token"]
    r = client.get("/api/v1/auth/me", headers=_headers(token))
    assert r.status_code == 200
    assert r.json()["username"] == "andi"


def test_me_without_token_401(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_invalid_token_401(client):
    assert client.get("/api/v1/auth/me", headers=_headers("bogus")).status_code == 401


def test_logout_revokes_all_sessions(client):
    """Acceptance: logout → token lama TIDAK berlaku lagi (session versioning)."""
    _register(client)
    token = _login(client).json()["access_token"]
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 200
    r = client.post("/api/v1/auth/logout", headers=_headers(token))
    assert r.status_code == 200
    # access token lama mati (sv mismatch) + refresh cookie tidak lagi dipakai
    assert client.get("/api/v1/auth/me", headers=_headers(token)).status_code == 401
    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 401


def test_refresh_rotation(client):
    _register(client)
    _login(client)
    r1 = client.post("/api/v1/auth/refresh")
    assert r1.status_code == 200
    new_cookie = r1.headers.get("set-cookie", "")
    # refresh kedua dengan cookie baru → masih jalan
    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 200
    # cookie lama (r1) sudah dirotasi → reuse terdeteksi, sesi dicabut
    client.cookies.set("refresh_token", new_cookie.split("refresh_token=")[1].split(";")[0], path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_brute_force_login_429(client):
    _register(client, username="target", email="target@example.com")
    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": "target@example.com", "password": "salah12345"})
    r = client.post("/api/v1/auth/login", json={"email": "target@example.com", "password": "salah12345"})
    assert r.status_code == 429


def test_session_list_and_revoke(client):
    _register(client)
    token = _login(client).json()["access_token"]
    _login(client)  # sesi kedua
    h = _headers(token)
    r = client.get("/api/v1/auth/sessions", headers=h)
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) == 2
    assert sum(1 for s in sessions if s["is_current"]) == 1
    # revoke sesi lain
    other = next(s for s in sessions if not s["is_current"])
    r = client.delete(f"/api/v1/auth/sessions/{other['id']}", headers=h)
    assert r.status_code == 204
    assert len(client.get("/api/v1/auth/sessions", headers=h).json()) == 1


def test_cross_user_session_revoke_404(client):
    """Multi-tenant: user B tidak bisa revoke sesi milik user A."""
    _register(client, username="userA", email="a@example.com")
    token_a = _login(client, email="a@example.com").json()["access_token"]
    sessions_a = client.get("/api/v1/auth/sessions", headers=_headers(token_a)).json()

    client.post("/api/v1/auth/logout")
    _register(client, username="userB", email="b@example.com")
    token_b = _login(client, email="b@example.com").json()["access_token"]

    r = client.delete(f"/api/v1/auth/sessions/{sessions_a[0]['id']}", headers=_headers(token_b))
    assert r.status_code == 404  # bukan 403/200 — hindari enumerasi


# ---------------------------------------------------------------- verify / forgot / reset


def test_verify_email_flow(client, monkeypatch):
    """Simulasikan email terkirim: tangkap link, ekstrak token, verifikasi."""
    captured: dict = {}

    def fake_send(to, subject, html, text=""):
        captured["html"] = html
        return True

    monkeypatch.setattr("apps.api.app.routers.auth.send_email", fake_send)
    _register(client)
    assert "token=" in captured["html"]
    token = captured["html"].split("token=")[1].split('"')[0]

    r = client.post("/api/v1/auth/verify", json={"token": token})
    assert r.status_code == 200
    me = client.get("/api/v1/auth/me", headers=_headers(_login(client).json()["access_token"])).json()
    assert me["email_verified"] is True

    # token sekali pakai
    assert client.post("/api/v1/auth/verify", json={"token": token}).status_code == 400


def test_forgot_reset_flow(client, monkeypatch):
    captured: dict = {}

    def fake_send(to, subject, html, text=""):
        captured["html"] = html
        return True

    monkeypatch.setattr("apps.api.app.routers.auth.send_email", fake_send)
    _register(client)

    r = client.post("/api/v1/auth/forgot", json={"email": "andi@example.com"})
    assert r.status_code == 200
    token = captured["html"].split("token=")[1].split('"')[0]

    r = client.post("/api/v1/auth/reset", json={"token": token, "password": "baru123456"})
    assert r.status_code == 200

    # password lama gagal, baru sukses
    assert client.post("/api/v1/auth/login", json={"email": "andi@example.com", "password": "rahasia123"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "andi@example.com", "password": "baru123456"}).status_code == 200


def test_forgot_anti_enumeration(client):
    """Email tidak terdaftar → tetap 200."""
    r = client.post("/api/v1/auth/forgot", json={"email": "tidakada@example.com"})
    assert r.status_code == 200


def test_reset_invalid_token_400(client):
    r = client.post("/api/v1/auth/reset", json={"token": "bogus", "password": "baru123456"})
    assert r.status_code == 400


# ---------------------------------------------------------------- profile


def test_update_me_and_change_password(client):
    _register(client)
    token = _login(client).json()["access_token"]
    h = _headers(token)

    r = client.patch("/api/v1/auth/me", json={"base_currency": "idr"}, headers=h)
    assert r.status_code == 200
    assert r.json()["base_currency"] == "IDR"

    # ganti password: salah lama → 400; benar → semua sesi mati
    assert client.post("/api/v1/auth/me/password", json={"old_password": "salah", "new_password": "ganti123456"}, headers=h).status_code == 400
    assert client.post("/api/v1/auth/me/password", json={"old_password": "rahasia123", "new_password": "ganti123456"}, headers=h).status_code == 200
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401  # access token lama mati
    assert client.post("/api/v1/auth/refresh").status_code == 401  # refresh juga
    # login dengan password baru
    assert client.post("/api/v1/auth/login", json={"email": "andi@example.com", "password": "ganti123456"}).status_code == 200
