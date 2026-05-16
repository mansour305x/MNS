from __future__ import annotations

import logging
from html import escape

from telegram import InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from app.backup import create_json_backup, create_users_csv
from app.database import db_session
from app.keyboards import admin_panel_keyboard, confirm_keyboard
from app.messages import ADMIN_HELP
from app.models import Role
from app.repositories import (
    add_audit,
    count_stats,
    get_setting,
    latest_errors,
    latest_users,
    set_ban_status,
    set_role,
    set_setting,
)
from app.security import has_role
from app.services import send_broadcast

logger = logging.getLogger(__name__)

BROADCAST_CONTENT, BAN_USER, UNBAN_USER, SET_ROLE, SET_WELCOME = range(5)


def _uid(update: Update) -> int | None:
    return update.effective_user.id if update.effective_user else None


async def _deny(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("غير مصرح لك باستخدام هذه العملية.")


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _uid(update)
    if not has_role(user_id, Role.MODERATOR.value):
        await _deny(update)
        return
    await update.effective_message.reply_text(ADMIN_HELP, parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    query = update.callback_query
    if not query:
        return None
    await query.answer()
    user_id = _uid(update)
    data = query.data or ""

    if data == "common:close":
        await query.message.delete()
        return ConversationHandler.END
    if data == "admin:cancel":
        context.user_data.pop("broadcast_payload", None)
        await query.edit_message_text("تم الإلغاء.")
        return ConversationHandler.END

    if not has_role(user_id, Role.MODERATOR.value):
        await query.edit_message_text("غير مصرح.")
        return ConversationHandler.END

    if data == "admin:stats":
        with db_session() as session:
            stats = count_stats(session)
        text = (
            "📊 <b>إحصائيات البوت</b>\n\n"
            f"المستخدمون: <b>{stats['total_users']}</b>\n"
            f"النشطون: <b>{stats['active_users']}</b>\n"
            f"المحظورون: <b>{stats['banned_users']}</b>\n"
            f"المديرون: <b>{stats['admins']}</b>\n"
            f"المشرفون: <b>{stats['moderators']}</b>\n"
            f"الرسائل الجماعية: <b>{stats['broadcasts']}</b>\n"
            f"الأخطاء المسجلة: <b>{stats['errors']}</b>"
        )
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if data == "admin:users":
        with db_session() as session:
            users = latest_users(session, 10)
        if not users:
            await query.edit_message_text("لا يوجد مستخدمون بعد.", reply_markup=admin_panel_keyboard())
            return ConversationHandler.END
        lines = ["👥 <b>آخر 10 مستخدمين</b>"]
        for user in users:
            name = escape(user.first_name or user.username or "بدون اسم")
            lines.append(f"• <code>{user.telegram_id}</code> - {name} - {user.role} - {'محظور' if user.is_banned else 'نشط'}")
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if data == "admin:broadcast":
        if not has_role(user_id, Role.ADMIN.value):
            await query.edit_message_text("هذه العملية للمدير فقط.")
            return ConversationHandler.END
        await query.edit_message_text(
            "📣 أرسل الآن نص الرسالة الجماعية أو صورة/ملف مع تعليق.\n\nاستخدم /cancel للإلغاء."
        )
        return BROADCAST_CONTENT

    if data == "admin:ban":
        await query.edit_message_text("أرسل Telegram ID للمستخدم المراد حظره.\nاستخدم /cancel للإلغاء.")
        return BAN_USER

    if data == "admin:unban":
        await query.edit_message_text("أرسل Telegram ID للمستخدم المراد فك حظره.\nاستخدم /cancel للإلغاء.")
        return UNBAN_USER

    if data == "admin:role":
        if not has_role(user_id, Role.ADMIN.value):
            await query.edit_message_text("إدارة الصلاحيات للمدير فقط.")
            return ConversationHandler.END
        await query.edit_message_text("أرسل بالشكل التالي:\n<code>TELEGRAM_ID user|moderator|admin</code>", parse_mode=ParseMode.HTML)
        return SET_ROLE

    if data == "admin:welcome":
        if not has_role(user_id, Role.ADMIN.value):
            await query.edit_message_text("تعديل الترحيب للمدير فقط.")
            return ConversationHandler.END
        await query.edit_message_text("أرسل رسالة الترحيب العربية الجديدة. يمكن استخدام HTML بسيط.\nاستخدم /cancel للإلغاء.")
        return SET_WELCOME

    if data == "admin:maintenance":
        if not has_role(user_id, Role.ADMIN.value):
            await query.edit_message_text("وضع الصيانة للمدير فقط.")
            return ConversationHandler.END
        with db_session() as session:
            current = get_setting(session, "maintenance_mode", "false")
            new_value = "false" if current == "true" else "true"
            set_setting(session, "maintenance_mode", new_value)
            add_audit(session, user_id, "toggle_maintenance", metadata={"value": new_value})
        await query.edit_message_text(f"🧰 وضع الصيانة الآن: <b>{new_value}</b>", parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if data == "admin:backup":
        if not has_role(user_id, Role.ADMIN.value):
            await query.edit_message_text("النسخ الاحتياطي للمدير فقط.")
            return ConversationHandler.END
        json_path = create_json_backup()
        csv_path = create_users_csv()
        await query.edit_message_text("📁 تم إنشاء النسخة الاحتياطية، سيتم إرسال الملفات الآن.")
        await context.bot.send_document(chat_id=user_id, document=InputFile(json_path.open("rb"), filename=json_path.name))
        await context.bot.send_document(chat_id=user_id, document=InputFile(csv_path.open("rb"), filename=csv_path.name))
        return ConversationHandler.END

    if data == "admin:logs":
        with db_session() as session:
            errors = latest_errors(session, 5)
        if not errors:
            await query.edit_message_text("لا توجد أخطاء مسجلة ✅", reply_markup=admin_panel_keyboard())
            return ConversationHandler.END
        lines = ["🧾 <b>آخر الأخطاء</b>"]
        for err in errors:
            lines.append(f"• <code>{err.created_at}</code> - {escape(err.message[:250])}")
        await query.edit_message_text("\n".join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())
        return ConversationHandler.END

    if data == "admin:broadcast_confirm":
        payload = context.user_data.get("broadcast_payload")
        if not payload:
            await query.edit_message_text("لا توجد رسالة جاهزة للإرسال.")
            return ConversationHandler.END
        await query.edit_message_text("بدأ الإرسال الجماعي. سيتم إعلامك بالنتيجة عند الانتهاء.")
        result = await send_broadcast(context.bot, user_id or 0, payload)
        context.user_data.pop("broadcast_payload", None)
        await context.bot.send_message(
            chat_id=user_id,
            text=f"📣 انتهى الإرسال.\nالإجمالي: {result['total']}\nتم الإرسال: {result['sent']}\nفشل: {result['failed']}",
        )
        return ConversationHandler.END

    return ConversationHandler.END


async def receive_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = _uid(update)
    if not has_role(user_id, Role.ADMIN.value):
        await _deny(update)
        return ConversationHandler.END
    message = update.effective_message
    if not message:
        return ConversationHandler.END

    payload: dict[str, str] | None = None
    if message.text:
        if len(message.text) > 4096:
            await message.reply_text("النص أطول من حد Telegram للرسائل. اختصره ثم أعد الإرسال.")
            return BROADCAST_CONTENT
        payload = {"content_type": "text", "text": message.text_html}
    elif message.photo:
        payload = {"content_type": "photo", "media_file_id": message.photo[-1].file_id, "caption": message.caption_html or ""}
    elif message.document:
        payload = {"content_type": "document", "media_file_id": message.document.file_id, "caption": message.caption_html or ""}
    else:
        await message.reply_text("نوع الرسالة غير مدعوم في MVP. أرسل نصاً أو صورة أو ملفاً.")
        return BROADCAST_CONTENT

    context.user_data["broadcast_payload"] = payload
    preview = "📣 <b>معاينة الرسالة الجماعية</b>\n\n"
    if payload["content_type"] == "text":
        preview += payload["text"]
    else:
        preview += f"نوع المحتوى: {payload['content_type']}\nالتعليق: {escape(payload.get('caption', ''))}"
    await message.reply_text(preview, parse_mode=ParseMode.HTML, reply_markup=confirm_keyboard("admin:broadcast_confirm"))
    return ConversationHandler.END


async def receive_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = _uid(update)
    if not has_role(user_id, Role.MODERATOR.value):
        await _deny(update)
        return ConversationHandler.END
    raw = (update.effective_message.text or "").strip()
    if not raw.isdigit():
        await update.effective_message.reply_text("أرسل Telegram ID رقمي فقط.")
        return BAN_USER
    target_id = int(raw)
    with db_session() as session:
        ok = set_ban_status(session, target_id, True)
        add_audit(session, user_id, "ban_user", target=str(target_id))
    await update.effective_message.reply_text("تم حظر المستخدم ✅" if ok else "لم يتم العثور على المستخدم.")
    return ConversationHandler.END


async def receive_unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = _uid(update)
    if not has_role(user_id, Role.MODERATOR.value):
        await _deny(update)
        return ConversationHandler.END
    raw = (update.effective_message.text or "").strip()
    if not raw.isdigit():
        await update.effective_message.reply_text("أرسل Telegram ID رقمي فقط.")
        return UNBAN_USER
    target_id = int(raw)
    with db_session() as session:
        ok = set_ban_status(session, target_id, False)
        add_audit(session, user_id, "unban_user", target=str(target_id))
    await update.effective_message.reply_text("تم فك الحظر ✅" if ok else "لم يتم العثور على المستخدم.")
    return ConversationHandler.END


async def receive_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = _uid(update)
    if not has_role(user_id, Role.ADMIN.value):
        await _deny(update)
        return ConversationHandler.END
    parts = (update.effective_message.text or "").strip().split()
    if len(parts) != 2 or not parts[0].isdigit() or parts[1] not in {Role.USER.value, Role.MODERATOR.value, Role.ADMIN.value}:
        await update.effective_message.reply_text("صيغة غير صحيحة. مثال:\n<code>123456789 moderator</code>", parse_mode=ParseMode.HTML)
        return SET_ROLE
    target_id = int(parts[0])
    role = parts[1]
    with db_session() as session:
        ok = set_role(session, target_id, role)
        add_audit(session, user_id, "set_role", target=str(target_id), metadata={"role": role})
    await update.effective_message.reply_text("تم تحديث الصلاحية ✅" if ok else "لم يتم العثور على المستخدم.")
    return ConversationHandler.END


async def role_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _uid(update)
    if not has_role(user_id, Role.ADMIN.value):
        await _deny(update)
        return
    parts = context.args or []
    if len(parts) != 2 or not parts[0].isdigit() or parts[1] not in {Role.USER.value, Role.MODERATOR.value, Role.ADMIN.value}:
        await update.effective_message.reply_text("الاستخدام: /role TELEGRAM_ID user|moderator|admin")
        return
    target_id = int(parts[0])
    role = parts[1]
    with db_session() as session:
        ok = set_role(session, target_id, role)
        add_audit(session, user_id, "set_role_command", target=str(target_id), metadata={"role": role})
    await update.effective_message.reply_text("تم تحديث الصلاحية ✅" if ok else "لم يتم العثور على المستخدم.")


async def receive_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = _uid(update)
    if not has_role(user_id, Role.ADMIN.value):
        await _deny(update)
        return ConversationHandler.END
    text = (update.effective_message.text_html or "").strip()
    if not text or len(text) > 3000:
        await update.effective_message.reply_text("رسالة غير صالحة. يجب ألا تتجاوز 3000 حرف.")
        return SET_WELCOME
    with db_session() as session:
        set_setting(session, "welcome_message_ar", text)
        add_audit(session, user_id, "set_welcome_message")
    await update.effective_message.reply_text("تم تحديث رسالة الترحيب ✅")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("تم إلغاء العملية الحالية.")
    return ConversationHandler.END
