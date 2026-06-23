import pytest

from app.rate_limit import TokenBucketRateLimiter


def test_allows_up_to_capacity_then_blocks():
    limiter = TokenBucketRateLimiter(capacity=3, refill_rate=1.0)
    # With a fixed timestamp no refill happens between calls.
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=0.0) is False


def test_refills_over_time():
    limiter = TokenBucketRateLimiter(capacity=2, refill_rate=1.0)
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=0.0) is True
    assert limiter.allow("ip", now=0.0) is False
    # One second later, one token has refilled.
    assert limiter.allow("ip", now=1.0) is True
    assert limiter.allow("ip", now=1.0) is False


def test_separate_clients_have_separate_buckets():
    limiter = TokenBucketRateLimiter(capacity=1, refill_rate=1.0)
    assert limiter.allow("a", now=0.0) is True
    assert limiter.allow("a", now=0.0) is False
    assert limiter.allow("b", now=0.0) is True


def test_invalid_config_raises():
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=0, refill_rate=1.0)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(capacity=1, refill_rate=0)
