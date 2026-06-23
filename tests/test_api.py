import pytest
from fastapi.testclient import TestClient

from app.deps import reset_state
from app.main import app


@pytest.fixture(autouse=True)
def fresh_state():
    reset_state()
    yield
    reset_state()


@pytest.fixture
def client():
    # Do not follow redirects so we can assert on the 302 + Location header.
    return TestClient(app, follow_redirects=False)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_shorten_and_redirect_flow(client):
    res = client.post("/api/shorten", json={"url": "https://example.com/hello"})
    assert res.status_code == 201
    code = res.json()["code"]

    redirect = client.get(f"/{code}")
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://example.com/hello"


def test_stats_track_clicks(client):
    code = client.post("/api/shorten", json={"url": "https://example.com/s"}).json()["code"]
    client.get(f"/{code}")
    client.get(f"/{code}")

    stats = client.get(f"/api/stats/{code}")
    assert stats.status_code == 200
    assert stats.json()["clicks"] == 2


def test_invalid_url_returns_422(client):
    res = client.post("/api/shorten", json={"url": "ftp://nope"})
    assert res.status_code == 422


def test_unknown_code_returns_404(client):
    assert client.get("/zzzzzz").status_code == 404
    assert client.get("/api/stats/zzzzzz").status_code == 404


def test_rate_limit_returns_429(monkeypatch):
    # Tighten the limit and rebuild singletons for a deterministic test.
    monkeypatch.setenv("RATE_LIMIT_CAPACITY", "3")
    monkeypatch.setenv("RATE_LIMIT_REFILL_PER_SEC", "0.0001")
    from app.config import get_settings

    get_settings.cache_clear()
    reset_state()

    client = TestClient(app, follow_redirects=False)
    codes = [client.post("/api/shorten", json={"url": f"https://e.com/{i}"}) for i in range(3)]
    assert all(r.status_code == 201 for r in codes)

    blocked = client.post("/api/shorten", json={"url": "https://e.com/x"})
    assert blocked.status_code == 429

    get_settings.cache_clear()
    reset_state()
