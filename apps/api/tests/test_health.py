def test_healthz_ok(client):
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["redis"] == "disabled"


def test_healthz_has_request_id(client):
    r = client.get("/api/v1/healthz")
    assert "X-Request-Id" in r.headers
    assert r.headers["X-Request-Id"]
