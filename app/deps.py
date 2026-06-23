"""Application-wide singletons (service + rate limiter)."""

from __future__ import annotations

from app.config import get_settings
from app.rate_limit import TokenBucketRateLimiter
from app.service import ShortenerService
from app.storage import build_storage

_service: ShortenerService | None = None
_limiter: TokenBucketRateLimiter | None = None


def get_service() -> ShortenerService:
    global _service
    if _service is None:
        s = get_settings()
        storage = build_storage(s.storage_backend, s.sqlite_path, s.id_start)
        _service = ShortenerService(storage, s.base_url, s.cache_size)
    return _service


def get_rate_limiter() -> TokenBucketRateLimiter:
    global _limiter
    if _limiter is None:
        s = get_settings()
        _limiter = TokenBucketRateLimiter(s.rate_limit_capacity, s.rate_limit_refill_per_sec)
    return _limiter


def reset_state() -> None:
    """Reset singletons (used by tests for isolation)."""
    global _service, _limiter
    _service = None
    _limiter = None
