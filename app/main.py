from __future__ import annotations

import logging

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.config import settings
from app.database import db_session, init_db
from app.handlers.admin import (
    BAN_USER,
    BROADCAST_CONTENT,
    SET_ROLE,
    SET_WELCOME,
    UNBAN_USER,
    admin_callback,
    admin_command,
    cancel,
    receive_ban_user,
    receive_broadcast_content,
    receive_role,
    receive_unban_user,
    receive_welcome,
    role_command,
)
from app.handlers.errors import error_handler
from app.handlers.user import help_command, notifications_command, settings_command, start, status_command, text_router, user_callback
from app.health import start_health_server
from app.repositories import ensure_default_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "بدء البوت"),
            BotCommand("help", "المساعدة"),
            BotCommand("settings", "الإعدادات"),
            BotCommand("admin", "لوحة الإدارة"),
            BotCommand("cancel", "إلغاء العملية الحالية"),
        ]
    )


def build_application() -> Application:
    application = Application.builder().token(settings.bot_token).post_init(post_init).build()

    admin_conversation = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback, pattern=r"^(admin:|common:)")],
        states={
            BROADCAST_CONTENT: [MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, receive_broadcast_content)],
            BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ban_user)],
            UNBAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unban_user)],
            SET_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_role)],
            SET_WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_welcome)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(admin_callback, pattern=r"^admin:cancel$")],
        allow_reentry=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("role", role_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(admin_conversation)
    application.add_handler(CallbackQueryHandler(user_callback, pattern=r"^(user:|common:close)"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    configure_logging()
    init_db()
    with db_session() as session:
        ensure_default_settings(session)
    start_health_server()
    logging.getLogger(__name__).info("Starting Telegram bot in %s mode", settings.environment)
    application = build_application()
    # Polling is chosen intentionally for free hosting because it does not require a public HTTPS webhook URL.
    application.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=False)


if __name__ == "__main__":
    main()
