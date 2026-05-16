from __future__ import annotations

import asyncio
import logging
from threading import Thread

import uvicorn
from fastapi import FastAPI

from app.config import settings

logger = logging.getLogger(__name__)
health_app = FastAPI(title="Telegram Pro Bot Health")


@health_app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-pro-bot"}


@health_app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


def _run_server() -> None:
    config = uvicorn.Config(health_app, host=settings.app_host, port=settings.app_port, log_level="warning")
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def start_health_server() -> None:
    thread = Thread(target=_run_server, daemon=True, name="health-server")
    thread.start()
    logger.info("Health server started on %s:%s", settings.app_host, settings.app_port)
