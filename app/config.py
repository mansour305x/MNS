from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet


def _parse_int_set(value: str) -> FrozenSet[int]:
    ids: set[int] = set()
    for item in value.split(','):
        item = item.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError(f"ADMIN_IDS contains a non-numeric id: {item!r}")
        ids.add(int(item))
    return frozenset(ids)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: FrozenSet[int]
    database_url: str
    app_port: int
    app_host: str
    log_level: str
    rate_limit_window_seconds: int
    rate_limit_max_actions: int
    broadcast_chunk_size: int
    broadcast_delay_seconds: float
    backup_dir: Path
    environment: str

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required. Add it to your .env or hosting environment variables.")

        admin_ids = _parse_int_set(os.getenv("ADMIN_IDS", ""))
        if not admin_ids:
            raise RuntimeError("ADMIN_IDS is required. Add at least one numeric Telegram user id.")

        backup_dir = Path(os.getenv("BACKUP_DIR", "backups"))
        backup_dir.mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            admin_ids=admin_ids,
            database_url=os.getenv("DATABASE_URL", "sqlite:///bot_data.sqlite3").strip(),
            app_port=int(os.getenv("PORT", os.getenv("APP_PORT", "8080"))),
            app_host=os.getenv("APP_HOST", "0.0.0.0"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "5")),
            rate_limit_max_actions=int(os.getenv("RATE_LIMIT_MAX_ACTIONS", "8")),
            broadcast_chunk_size=int(os.getenv("BROADCAST_CHUNK_SIZE", "25")),
            broadcast_delay_seconds=float(os.getenv("BROADCAST_DELAY_SECONDS", "1.0")),
            backup_dir=backup_dir,
            environment=os.getenv("ENVIRONMENT", "development"),
        )


settings = Settings.from_env()
