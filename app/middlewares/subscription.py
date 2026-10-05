from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import Settings
from app.keyboards.user import subscription_kb
from app.services.subscription_service import SubscriptionService
from app.texts import NEED_START, SUBSCRIBE_PROMPT


class SubscriptionMiddleware(BaseMiddleware):
    """Foydalanuvchi menyularidan oldin: ro'yxatdan o'tganmi va majburiy kanallarga obunami."""

    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]
    ) -> Any:
        settings: Settings = data["settings"]
        tg_user = data.get("event_from_user")
        user = data.get("db_user")
        message = event if isinstance(event, Message) else getattr(event, "message", None)

        if user is None:
            if isinstance(event, CallbackQuery):
                await event.answer(NEED_START, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(NEED_START)
            return None

        if tg_user is not None and not settings.is_admin(tg_user.id):
            svc = SubscriptionService(data["session"], data["bot"], data.get("redis"))
            missing = await svc.missing_channels(tg_user.id, use_cache=True)
            if missing:
                if isinstance(event, CallbackQuery):
                    await event.answer()
                if isinstance(message, Message):
                    await message.answer(SUBSCRIBE_PROMPT, reply_markup=subscription_kb(missing))
                return None
        return await handler(event, data)
