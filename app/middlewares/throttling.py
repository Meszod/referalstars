from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# (kalit, limit, oyna sekundlarda)
RULE_START = ("start", 5, 60)
RULE_CALLBACK = ("cb", 20, 10)
RULE_MESSAGE = ("msg", 10, 10)


class ThrottlingMiddleware(BaseMiddleware):
    """Redis asosidagi sodda rate limit (fixed window). Redis ishlamasa — fail-open."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    @staticmethod
    def _rule(event: TelegramObject) -> tuple[str, int, int]:
        if isinstance(event, CallbackQuery):
            return RULE_CALLBACK
        if isinstance(event, Message) and (event.text or "").startswith("/start"):
            return RULE_START
        return RULE_MESSAGE

    async def __call__(
        self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is None:
            return await handler(event, data)
        kind, limit, window = self._rule(event)
        key = f"rl:{kind}:{tg_user.id}"
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, window)
        except Exception:  # noqa: BLE001
            logger.warning("Redis rate-limit xatosi", exc_info=True)
            return await handler(event, data)

        if count > limit:
            if count == limit + 1:  # faqat bir marta ogohlantiramiz
                if isinstance(event, CallbackQuery):
                    await event.answer("⏳ Iltimos, sekinroq.", show_alert=False)
                elif isinstance(event, Message):
                    await event.answer("⏳ Juda tez-tez so‘rov yuboryapsiz. Birozdan keyin urinib ko‘ring.")
            return None
        return await handler(event, data)
