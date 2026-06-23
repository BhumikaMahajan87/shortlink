import pytest

from app.service import InvalidURL, ShortenerService
from app.storage import MemoryStorage, SqliteStorage


@pytest.fixture(params=["memory", "sqlite"])
def service(request, tmp_path):
    if request.param == "memory":
        storage = MemoryStorage(id_start=100_000)
    else:
        storage = SqliteStorage(str(tmp_path / "test.db"), id_start=100_000)
    return ShortenerService(storage, base_url="http://sho.rt", cache_size=8)


def test_shorten_creates_code_and_short_url(service):
    result = service.shorten("https://example.com/a/b/c")
    assert result.created is True
    assert result.code
    assert result.short_url == f"http://sho.rt/{result.code}"


def test_shorten_is_idempotent_for_same_url(service):
    first = service.shorten("https://example.com/page")
    second = service.shorten("https://example.com/page")
    assert first.code == second.code
    assert second.created is False


def test_resolve_returns_long_url_and_counts_clicks(service):
    code = service.shorten("https://example.com/x").code
    assert service.resolve(code) == "https://example.com/x"
    assert service.resolve(code) == "https://example.com/x"
    stats = service.stats(code)
    assert stats["clicks"] == 2
    assert len(stats["recent_clicks"]) == 2


def test_resolve_unknown_code_returns_none(service):
    assert service.resolve("doesnotexist") is None


def test_invalid_urls_rejected(service):
    for bad in ["", "ftp://x.com", "not-a-url", "http://"]:
        with pytest.raises(InvalidURL):
            service.shorten(bad)


def test_different_urls_get_different_codes(service):
    a = service.shorten("https://example.com/1").code
    b = service.shorten("https://example.com/2").code
    assert a != b
