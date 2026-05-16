from __future__ import annotations

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from app.config import settings
from app.database import db_session
from app.keyboards import BTN_HELP, BTN_NOTIFICATIONS, BTN_SETTINGS, BTN_STATUS, main_menu, settings_keyboard
from app.messages import BANNED_MESSAGE, HELP_AR, HELP_EN, RATE_LIMIT_MESSAGE, UNKNOWN_MESSAGE
from app.repositories import (
    get_setting,
    get_unread_notifications,
    increment_message_count,
    mark_notifications_read,
    set_setting,
    upsert_user,
)
from app.security import blocked_or_limited, is_admin_id

logger = logging.getLogger(__name__)


async def _register_and_guard(update: Update) -> bool:
    tg_user = update.effective_user
    with db_session() as session:
        user = upsert_user(session, tg_user)
        if user and update.message:
            increment_message_count(session, user.telegram_id)

    user_id = tg_user.id if tg_user else None
    status = blocked_or_limited(user_id)
    if status == "banned":
        if update.effective_message:
            await update.effective_message.reply_text(BANNED_MESSAGE)
        return False
    if status == "limited":
        if update.effective_message:
            await update.effective_message.reply_text(RATE_LIMIT_MESSAGE)
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    user = update.effective_user
    is_admin = is_admin_id(user.id if user else None)
    with db_session() as session:
        language = "ar"
        if user:
            db_user = upsert_user(session, user)
            language = db_user.preferred_language if db_user else "ar"
        key = "welcome_message_ar" if language == "ar" else "welcome_message_en"
        welcome = get_setting(session, key)
    await update.effective_message.reply_text(
        welcome,
        reply_markup=main_menu(is_admin=is_admin),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    language = "ar"
    user = update.effective_user
    with db_session() as session:
        if user:
            db_user = upsert_user(session, user)
            language = db_user.preferred_language if db_user else "ar"
    await update.effective_message.reply_text(HELP_AR if language == "ar" else HELP_EN, parse_mode=ParseMode.HTML)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    await update.effective_message.reply_text("⚙️ اختر إعداداتك:", reply_markup=settings_keyboard())


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    user = update.effective_user
    if not user:
        return
    with db_session() as session:
        db_user = upsert_user(session, user)
        unread = len(get_unread_notifications(session, user.id))
        text = (
            "📊 <b>حالتك</b>\n\n"
            f"المعرف: <code>{user.id}</code>\n"
            f"الدور: <b>{db_user.role}</b>\n"
            f"محظور: {'نعم' if db_user.is_banned else 'لا'}\n"
            f"عدد رسائلك: {db_user.message_count}\n"
            f"الإشعارات غير المقروءة: {unread}"
        )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    user = update.effective_user
    if not user:
        return
    with db_session() as session:
        notes = get_unread_notifications(session, user.id)
    if not notes:
        await update.effective_message.reply_text("🔔 لا توجد إشعارات جديدة.")
        return
    lines = ["🔔 <b>إشعاراتك</b>"]
    for item in notes:
        lines.append(f"\n<b>{item.title}</b>\n{item.body}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=settings_keyboard())


async def user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user = update.effective_user
    if not user:
        return

    data = query.data or ""
    if data == "common:close":
        await query.message.delete()
        return

    status = blocked_or_limited(user.id)
    if status == "banned":
        await query.edit_message_text(BANNED_MESSAGE)
        return
    if status == "limited":
        await query.answer(RATE_LIMIT_MESSAGE, show_alert=True)
        return

    if data.startswith("user:lang:"):
        lang = data.rsplit(":", 1)[-1]
        if lang not in {"ar", "en"}:
            await query.answer("لغة غير صالحة", show_alert=True)
            return
        with db_session() as session:
            db_user = upsert_user(session, user)
            if db_user:
                db_user.preferred_language = lang
        await query.edit_message_text("تم تحديث اللغة ✅" if lang == "ar" else "Language updated ✅")
        return

    if data == "user:read_notifications":
        with db_session() as session:
            count = mark_notifications_read(session, user.id)
        await query.edit_message_text(f"تم تعليم {count} إشعار كمقروء ✅")
        return


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _register_and_guard(update):
        return
    text = (update.effective_message.text or "").strip()
    if text == BTN_HELP:
        await help_command(update, context)
    elif text == BTN_SETTINGS:
        await settings_command(update, context)
    elif text == BTN_NOTIFICATIONS:
        await notifications_command(update, context)
    elif text == BTN_STATUS:
        await status_command(update, context)
    elif text == "🛠 لوحة الإدارة":
        from app.handlers.admin import admin_command

        await admin_command(update, context)
    else:
        await update.effective_message.reply_text(UNKNOWN_MESSAGE)
