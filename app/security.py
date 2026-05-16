from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from telegram import Update

from app.config import settings
from app.database import db_session
from app.models import Role
from app.repositories import get_user_role, is_banned

ROLE_RANK = {
    Role.USER.value: 10,
    Role.MODERATOR.value: 50,
    Role.ADMIN.value: 100,
}


@dataclass
class RateLimiter:
    window_seconds: int
    max_actions: int
    hits: dict[int, deque[datetime]] = field(default_factory=lambda: defaultdict(deque))

    def allow(self, user_id: int) -> bool:
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=self.window_seconds)
        bucket = self.hits[user_id]
        while bucket and bucket[0] < window_start:
            bucket.popleft()
        if len(bucket) >= self.max_actions:
            return False
        bucket.append(now)
        return True


rate_limiter = RateLimiter(settings.rate_limit_window_seconds, settings.rate_limit_max_actions)


def user_id_from_update(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


def is_admin_id(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_ids)


def has_role(user_id: int | None, required_role: str) -> bool:
    if user_id is None:
        return False
    if user_id in settings.admin_ids:
        return True
    with db_session() as session:
        role = get_user_role(session, user_id)
    return ROLE_RANK.get(role, 0) >= ROLE_RANK.get(required_role, 100)


def blocked_or_limited(user_id: int | None) -> str | None:
    if user_id is None:
        return "unknown"
    with db_session() as session:
        if is_banned(session, user_id):
            return "banned"
    if user_id not in settings.admin_ids and not rate_limiter.allow(user_id):
        return "limited"
    return None
