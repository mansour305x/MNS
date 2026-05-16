from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.database import db_session
from app.repositories import count_stats, export_users_payload


def create_json_backup() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = settings.backup_dir / f"backup_{timestamp}.json"
    with db_session() as session:
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stats": count_stats(session),
            "users": export_users_payload(session),
        }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def create_users_csv() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = settings.backup_dir / f"users_{timestamp}.csv"
    with db_session() as session:
        rows = export_users_payload(session)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["telegram_id"])
        writer.writeheader()
        writer.writerows(rows)
    return path
