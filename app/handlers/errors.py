from __future__ import annotations

import logging
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from app.config import settings
from app.database import db_session
from app.repositories import add_error_log

logger = logging.getLogger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    tb = "".join(traceback.format_exception(None, context.error, context.error.__traceback__)) if context.error else ""
    user_id = None
    if isinstance(update, Update) and update.effective_user:
        user_id = update.effective_user.id
    logger.error("Unhandled error: %s", context.error, exc_info=context.error)
    with db_session() as session:
        add_error_log(session, message=str(context.error), traceback_text=tb, user_id=user_id)
    for admin_id in settings.admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=f"⚠️ خطأ غير متوقع:\n<code>{str(context.error)[:1500]}</code>", parse_mode="HTML")
        except Exception:
            logger.exception("Failed to notify admin about error")
