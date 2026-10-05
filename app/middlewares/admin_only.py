from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.config import Settings

logger = logging.getLogger("audit")


class AdminOnlyMiddleware(BaseMiddleware):
    """Admin router'iga faqat ADMIN_IDS kira oladi (message va callback uchun)."""

    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]
    ) -> Any:
        settings: Settings = data["settings"]
        tg_user = data.get("event_from_user")
        if tg_user is None or not settings.is_admin(tg_user.id):
            logger.warning("unauthorized admin access attempt user=%s", getattr(tg_user, "id", None))
            if isinstance(event, CallbackQuery):
                await event.answer("⛔ Ruxsat yo‘q", show_alert=True)
            return None
        return await handler(event, data)
