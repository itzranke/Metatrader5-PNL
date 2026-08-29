"""Test Phase 10 — Laporan bulanan PDF + email (BLUEPRINT §25)."""


def _register_demo(client, username="rp10", email="rp10@example.com"):
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "rahasia123"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    ).json()["access_token"]
    acc = client.post(
        "/api/v1/accounts", json={"kind": "demo", "name": "Demo Rp"},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    return token, acc


def test_monthly_pdf_demo_account(client):
    token, acc = _register_demo(client)
    r = client.get(
        f"/api/v1/accounts/{acc['id']}/reports/monthly.pdf?month=2026-08",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text[:200]
    assert r.headers["content-type"].startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 5000  # laporan padat, bukan halaman kosong


def test_monthly_pdf_empty_month_valid(client):
    token, acc = _register_demo(client)
    r = client.get(
        f"/api/v1/accounts/{acc['id']}/reports/monthly.pdf?month=2020-01",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_monthly_pdf_invalid_month(client):
    token, acc = _register_demo(client)
    r = client.get(
        f"/api/v1/accounts/{acc['id']}/reports/monthly.pdf?month=2026-13",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_monthly_pdf_cross_user_404(client):
    token_a, acc_a = _register_demo(client)
    client.post(
        "/api/v1/auth/register",
        json={"username": "rp10b", "email": "rp10b@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "rp10b@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    r = client.get(
        f"/api/v1/accounts/{acc_a['id']}/reports/monthly.pdf?month=2026-08",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


def test_monthly_report_email_dev_log(client, caplog):
    import logging

    token, acc = _register_demo(client)
    with caplog.at_level(logging.INFO, logger="api.email"):
        r = client.post(
            f"/api/v1/accounts/{acc['id']}/reports/monthly/email",
            json={"month": "2026-08", "to": "kirim@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["to"] == "kirim@example.com"
    assert body["filename"].endswith(".pdf")
    # dev fallback menulis ke log dengan attachment
    joined = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "attachment=" in joined and "laporan-agustus-2026.pdf" in joined


def test_monthly_report_email_cross_user_404(client):
    token_a, acc_a = _register_demo(client)
    client.post(
        "/api/v1/auth/register",
        json={"username": "rp10c", "email": "rp10c@example.com", "password": "rahasia123"},
    )
    token_b = client.post(
        "/api/v1/auth/login", json={"email": "rp10c@example.com", "password": "rahasia123"}
    ).json()["access_token"]
    r = client.post(
        f"/api/v1/accounts/{acc_a['id']}/reports/monthly/email",
        json={"month": "2026-08"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
