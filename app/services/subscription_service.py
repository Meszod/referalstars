from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Channel
from app.database.repositories import ChannelRepository

logger = logging.getLogger(__name__)

SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}
CACHE_TTL = 60


class SubscriptionService:
    def __init__(self, session: AsyncSession, bot: Bot, redis: Redis | None = None) -> None:
        self.channels = ChannelRepository(session)
        self.bot = bot
        self.redis = redis

    @staticmethod
    def _cache_key(telegram_id: int) -> str:
        return f"sub_ok:{telegram_id}"

    async def missing_channels(self, telegram_id: int, *, use_cache: bool = False) -> list[Channel]:
        """Foydalanuvchi obuna bo'lmagan kanallar ro'yxati (bo'sh -> hammasiga obuna)."""
        channels = await self.channels.list_active()
        if not channels:
            return []
        if use_cache and self.redis is not None:
            try:
                if await self.redis.get(self._cache_key(telegram_id)):
                    return []
            except Exception:  # noqa: BLE001
                logger.warning("Redis cache o‘qib bo‘lmadi", exc_info=True)

        missing: list[Channel] = []
        for ch in channels:
            try:
                member = await self.bot.get_chat_member(ch.channel_id, telegram_id)
            except TelegramAPIError as exc:
                # Bot kanalda admin emas / kanal topilmadi: userni qamab qo'ymaymiz, adminga log.
                logger.error("getChatMember xatosi channel=%s: %s", ch.channel_id, exc)
                continue
            status = str(getattr(member.status, "value", member.status))
            is_member = status in SUBSCRIBED_STATUSES or (
                status == "restricted" and bool(getattr(member, "is_member", False))
            )
            if not is_member:
                missing.append(ch)

        if not missing and self.redis is not None:
            try:
                await self.redis.set(self._cache_key(telegram_id), "1", ex=CACHE_TTL)
            except Exception:  # noqa: BLE001
                logger.warning("Redis cache yozib bo‘lmadi", exc_info=True)
        return missing
