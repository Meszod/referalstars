from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

from app.config import Settings
from app.database.repositories import UserRepository

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseMiddleware):
    """`db_user`ni data'ga qo'yadi. Banned (admin bo'lmagan) userlarning update'lari to'xtatiladi."""

    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]
    ) -> Any:
        tg_user = data.get("event_from_user")
        settings: Settings = data["settings"]
        data["db_user"] = None
        if tg_user is not None:
            user = await UserRepository(data["session"]).get_by_telegram_id(tg_user.id)
            data["db_user"] = user
            if user is not None and user.is_banned and not settings.is_admin(tg_user.id):
                inner = getattr(event, "callback_query", None)
                if isinstance(inner, CallbackQuery):
                    await inner.answer("🚫 Siz bloklangansiz.", show_alert=True)
                return None
        return await handler(event, data)
