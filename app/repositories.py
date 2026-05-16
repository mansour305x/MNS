from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from telegram import User as TelegramUser

from app.config import settings
from app.models import AuditLog, BotSetting, Broadcast, BroadcastLog, ErrorLog, Notification, Role, User, utcnow

DEFAULT_SETTINGS = {
    "welcome_message_ar": "أهلاً بك 👋\nهذا بوت احترافي جاهز لإدارة المستخدمين والإشعارات. استخدم القائمة بالأسفل.",
    "welcome_message_en": "Welcome 👋\nThis professional bot is ready for users, notifications, and admin control.",
    "maintenance_mode": "false",
    "support_text": "للمساعدة، تواصل مع إدارة البوت أو استخدم الأزرار المتاحة.",
}


def ensure_default_settings(session: Session) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        existing = session.scalar(select(BotSetting).where(BotSetting.key == key))
        if not existing:
            session.add(BotSetting(key=key, value=value))


def get_setting(session: Session, key: str, default: str = "") -> str:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    return row.value if row else default


def set_setting(session: Session, key: str, value: str) -> None:
    row = session.scalar(select(BotSetting).where(BotSetting.key == key))
    if row:
        row.value = value
    else:
        session.add(BotSetting(key=key, value=value))


def upsert_user(session: Session, tg_user: TelegramUser | None) -> User | None:
    if tg_user is None:
        return None
    user = session.scalar(select(User).where(User.telegram_id == tg_user.id))
    role = Role.ADMIN.value if tg_user.id in settings.admin_ids else Role.USER.value
    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            language_code=tg_user.language_code,
            preferred_language="ar" if (tg_user.language_code or "ar").startswith("ar") else "en",
            role=role,
        )
        session.add(user)
        session.flush()
    else:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        user.language_code = tg_user.language_code
        if tg_user.id in settings.admin_ids:
            user.role = Role.ADMIN.value
        user.last_seen_at = utcnow()
        user.action_count += 1
    return user


def increment_message_count(session: Session, telegram_id: int) -> None:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user:
        user.message_count += 1
        user.last_seen_at = utcnow()


def is_banned(session: Session, telegram_id: int) -> bool:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    return bool(user and user.is_banned)


def set_ban_status(session: Session, telegram_id: int, banned: bool) -> bool:
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        return False
    user.is_banned = banned
    return True


def set_role(session: Session, telegram_id: int, role: str) -> bool:
    if role not in {Role.USER.value, Role.MODERATOR.value, Role.ADMIN.value}:
        return False
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    if not user:
        return False
    user.role = role
    return True


def get_user_role(session: Session, telegram_id: int) -> str:
    if telegram_id in settings.admin_ids:
        return Role.ADMIN.value
    user = session.scalar(select(User).where(User.telegram_id == telegram_id))
    return user.role if user else Role.USER.value


def count_stats(session: Session) -> dict[str, int]:
    total = session.scalar(select(func.count(User.id))) or 0
    banned = session.scalar(select(func.count(User.id)).where(User.is_banned.is_(True))) or 0
    admins = session.scalar(select(func.count(User.id)).where(User.role == Role.ADMIN.value)) or 0
    moderators = session.scalar(select(func.count(User.id)).where(User.role == Role.MODERATOR.value)) or 0
    broadcasts = session.scalar(select(func.count(Broadcast.id))) or 0
    errors = session.scalar(select(func.count(ErrorLog.id))) or 0
    return {
        "total_users": int(total),
        "active_users": int(total - banned),
        "banned_users": int(banned),
        "admins": int(admins),
        "moderators": int(moderators),
        "broadcasts": int(broadcasts),
        "errors": int(errors),
    }


def latest_users(session: Session, limit: int = 10) -> list[User]:
    return list(session.scalars(select(User).order_by(desc(User.created_at)).limit(limit)))


def get_active_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).where(User.is_banned.is_(False)).order_by(User.id)))


def create_broadcast(session: Session, admin_id: int, payload: dict[str, Any], total: int) -> Broadcast:
    broadcast = Broadcast(
        admin_telegram_id=admin_id,
        content_type=payload["content_type"],
        text=payload.get("text"),
        media_file_id=payload.get("media_file_id"),
        caption=payload.get("caption"),
        total_count=total,
        status="running",
    )
    session.add(broadcast)
    session.flush()
    return broadcast


def mark_broadcast_result(session: Session, broadcast_id: int, user_id: int, ok: bool, error: str | None = None) -> None:
    status = "sent" if ok else "failed"
    log = BroadcastLog(
        broadcast_id=broadcast_id,
        user_id=user_id,
        status=status,
        error_message=error,
        sent_at=utcnow() if ok else None,
    )
    session.add(log)
    broadcast = session.get(Broadcast, broadcast_id)
    if broadcast:
        if ok:
            broadcast.sent_count += 1
        else:
            broadcast.failed_count += 1


def finish_broadcast(session: Session, broadcast_id: int) -> None:
    broadcast = session.get(Broadcast, broadcast_id)
    if broadcast:
        broadcast.status = "finished"
        broadcast.finished_at = utcnow()


def add_error_log(session: Session, message: str, traceback_text: str | None = None, user_id: int | None = None, source: str = "bot") -> None:
    session.add(ErrorLog(message=message[:4000], traceback=traceback_text, user_telegram_id=user_id, source=source))


def latest_errors(session: Session, limit: int = 5) -> list[ErrorLog]:
    return list(session.scalars(select(ErrorLog).order_by(desc(ErrorLog.created_at)).limit(limit)))


def add_audit(session: Session, actor_id: int | None, action: str, target: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    session.add(AuditLog(actor_telegram_id=actor_id, action=action, target=target, metadata_json=json.dumps(metadata or {}, ensure_ascii=False)))


def add_notification(session: Session, user_telegram_id: int, title: str, body: str) -> None:
    session.add(Notification(user_telegram_id=user_telegram_id, title=title, body=body))


def get_unread_notifications(session: Session, user_telegram_id: int, limit: int = 5) -> list[Notification]:
    return list(
        session.scalars(
            select(Notification)
            .where(Notification.user_telegram_id == user_telegram_id, Notification.is_read.is_(False))
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
    )


def mark_notifications_read(session: Session, user_telegram_id: int) -> int:
    notes = get_unread_notifications(session, user_telegram_id, limit=100)
    for item in notes:
        item.is_read = True
    return len(notes)


def export_users_payload(session: Session) -> list[dict[str, Any]]:
    rows = session.scalars(select(User).order_by(User.id)).all()
    return [
        {
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "preferred_language": user.preferred_language,
            "role": user.role,
            "is_banned": user.is_banned,
            "message_count": user.message_count,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
        }
        for user in rows
    ]
