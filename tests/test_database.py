from types import SimpleNamespace

from app.database import db_session, init_db
from app.models import Role
from app.repositories import count_stats, ensure_default_settings, set_ban_status, set_role, upsert_user


def test_user_lifecycle():
    init_db()
    tg_user = SimpleNamespace(id=2002, username="tester", first_name="Test", last_name="User", language_code="ar")
    with db_session() as session:
        ensure_default_settings(session)
        user = upsert_user(session, tg_user)
        assert user.telegram_id == 2002
        assert user.is_banned is False
        assert set_ban_status(session, 2002, True) is True
        assert set_role(session, 2002, Role.MODERATOR.value) is True

    with db_session() as session:
        stats = count_stats(session)
        assert stats["total_users"] >= 1
        assert stats["banned_users"] >= 1
        assert stats["moderators"] >= 1
