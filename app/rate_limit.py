"""Token-bucket rate limiter.

Each client (keyed by IP) gets a bucket that holds up to ``capacity`` tokens
and refills at ``refill_rate`` tokens/second. Every request consumes one
token; when the bucket is empty the request is rejected. This smoothly allows
short bursts while bounding the sustained request rate - the standard
algorithm used by API gateways and CDNs.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    last_refill: float


class TokenBucketRateLimiter:
    def __init__(self, capacity: int, refill_rate: float) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be positive")
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None) -> bool:
        """Return True if a request from ``key`` is allowed, consuming a token."""
        now = time.monotonic() if now is None else now
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                # New clients start with a full bucket.
                self._buckets[key] = _Bucket(tokens=self._capacity - 1, last_refill=now)
                return True

            elapsed = max(0.0, now - bucket.last_refill)
            bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill_rate)
            bucket.last_refill = now

            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False

    def tokens_remaining(self, key: str) -> float:
        with self._lock:
            bucket = self._buckets.get(key)
            return self._capacity if bucket is None else bucket.tokens
