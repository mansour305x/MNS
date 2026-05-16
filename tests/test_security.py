from datetime import datetime, timedelta, timezone

from app.security import RateLimiter


def test_rate_limiter_blocks_after_max_actions():
    limiter = RateLimiter(window_seconds=10, max_actions=2)
    assert limiter.allow(1) is True
    assert limiter.allow(1) is True
    assert limiter.allow(1) is False


def test_rate_limiter_allows_after_window():
    limiter = RateLimiter(window_seconds=1, max_actions=1)
    assert limiter.allow(1) is True
    limiter.hits[1][0] = datetime.now(timezone.utc) - timedelta(seconds=2)
    assert limiter.allow(1) is True
