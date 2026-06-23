"""Core URL-shortening service: encoding, dedup, caching and analytics."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from app import base62
from app.storage import ClickEvent, Link, Storage


class InvalidURL(ValueError):
    """Raised when a URL fails validation."""


@dataclass
class ShortenResult:
    code: str
    short_url: str
    long_url: str
    created: bool  # False if an existing code was reused (idempotent shorten)


class _LRUCache:
    """A tiny thread-unsafe LRU cache for the hot read path (code -> url)."""

    def __init__(self, capacity: int) -> None:
        self._capacity = max(1, capacity)
        self._data: "OrderedDict[str, str]" = OrderedDict()

    def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def put(self, key: str, value: str) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self._capacity:
            self._data.popitem(last=False)


def _validate_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise InvalidURL("URL must not be empty")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise InvalidURL("URL must start with http:// or https://")
    if not parsed.netloc:
        raise InvalidURL("URL must include a host")
    return url


class ShortenerService:
    def __init__(self, storage: Storage, base_url: str, cache_size: int = 1024) -> None:
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache = _LRUCache(cache_size)

    def shorten(self, long_url: str) -> ShortenResult:
        long_url = _validate_url(long_url)

        # Idempotency: return the same code for a URL we've already shortened.
        existing = self._storage.find_by_url(long_url)
        if existing is not None:
            return ShortenResult(
                code=existing.code,
                short_url=self._short_url(existing.code),
                long_url=long_url,
                created=False,
            )

        new_id = self._storage.next_id()
        code = base62.encode(new_id)
        link = Link(code=code, long_url=long_url, created_at=datetime.now(timezone.utc).isoformat())
        self._storage.save_link(link)
        self._cache.put(code, long_url)
        return ShortenResult(
            code=code, short_url=self._short_url(code), long_url=long_url, created=True
        )

    def resolve(
        self,
        code: str,
        *,
        referer: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        """Resolve a code to its long URL and record a click. Returns None if unknown."""
        long_url = self._cache.get(code)
        if long_url is None:
            link = self._storage.get_link(code)
            if link is None:
                return None
            long_url = link.long_url
            self._cache.put(code, long_url)

        self._storage.record_click(
            ClickEvent(
                code=code,
                timestamp=datetime.now(timezone.utc).isoformat(),
                referer=referer,
                user_agent=user_agent,
            )
        )
        return long_url

    def stats(self, code: str) -> dict | None:
        link = self._storage.get_link(code)
        if link is None:
            return None
        recent = self._storage.recent_clicks(code, limit=20)
        return {
            "code": link.code,
            "short_url": self._short_url(link.code),
            "long_url": link.long_url,
            "created_at": link.created_at,
            "clicks": link.clicks,
            "recent_clicks": [
                {"timestamp": c.timestamp, "referer": c.referer, "user_agent": c.user_agent}
                for c in recent
            ],
        }

    def total_links(self) -> int:
        return self._storage.total_links()

    def _short_url(self, code: str) -> str:
        return f"{self._base_url}/{code}"
