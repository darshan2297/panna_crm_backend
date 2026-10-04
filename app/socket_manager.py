"""Realtime event bus (Socket.IO) for live kitchen screen and shop status sync."""

import asyncio
from typing import Any

import socketio

from app.core.logging import logger

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

_main_loop: asyncio.AbstractEventLoop | None = None


def capture_loop() -> None:
    """Capture the running event loop at app startup so sync handlers can emit."""
    global _main_loop
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        _main_loop = None


def emit_event(event: str, data: Any) -> None:
    """Thread-safe fire-and-forget emit usable from sync SQLAlchemy services."""
    global _main_loop
    if _main_loop is None or _main_loop.is_closed():
        try:
            _main_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.debug(f"Socket emit skipped (no loop): {event}")
            return
    try:
        asyncio.run_coroutine_threadsafe(sio.emit(event, data), _main_loop)
    except Exception as e:  # never break the request path
        logger.debug(f"Socket emit failed for {event}: {e}")


@sio.event
async def connect(sid, environ):
    logger.info(f"Socket client connected: {sid}")


@sio.event
async def disconnect(sid):
    logger.info(f"Socket client disconnected: {sid}")
