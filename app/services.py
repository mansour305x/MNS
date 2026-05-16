from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut

from app.config import settings
from app.database import db_session
from app.models import utcnow
from app.repositories import create_broadcast, finish_broadcast, get_active_users, mark_broadcast_result

logger = logging.getLogger(__name__)


async def send_broadcast(bot: Bot, admin_id: int, payload: dict[str, Any]) -> dict[str, int]:
    with db_session() as session:
        users = get_active_users(session)
        broadcast = create_broadcast(session, admin_id, payload, len(users))
        broadcast_id = broadcast.id

    sent = 0
    failed = 0

    for index, user in enumerate(users, start=1):
        ok = False
        error: str | None = None
        try:
            if payload["content_type"] == "text":
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=payload["text"],
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=False,
                )
            elif payload["content_type"] == "photo":
                await bot.send_photo(chat_id=user.telegram_id, photo=payload["media_file_id"], caption=payload.get("caption"))
            elif payload["content_type"] == "document":
                await bot.send_document(chat_id=user.telegram_id, document=payload["media_file_id"], caption=payload.get("caption"))
            else:
                await bot.send_message(chat_id=user.telegram_id, text=payload.get("text") or "")
            ok = True
            sent += 1
        except RetryAfter as exc:
            await asyncio.sleep(float(exc.retry_after) + 1)
            try:
                await bot.send_message(chat_id=user.telegram_id, text=payload.get("text") or "")
                ok = True
                sent += 1
            except TelegramError as retry_exc:
                error = str(retry_exc)
                failed += 1
        except (Forbidden, BadRequest, TimedOut, NetworkError, TelegramError) as exc:
            error = str(exc)
            failed += 1
        except Exception as exc:  # defensive safety net
            error = f"Unexpected broadcast error: {exc}"
            failed += 1
            logger.exception("Unexpected broadcast error")

        with db_session() as session:
            mark_broadcast_result(session, broadcast_id, user.id, ok, error)

        if index % settings.broadcast_chunk_size == 0:
            await asyncio.sleep(settings.broadcast_delay_seconds)

    with db_session() as session:
        finish_broadcast(session, broadcast_id)

    return {"sent": sent, "failed": failed, "total": len(users)}
