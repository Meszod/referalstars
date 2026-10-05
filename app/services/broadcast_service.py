from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.repositories import UserRepository

logger = logging.getLogger(__name__)
audit = logging.getLogger("audit")

SEND_DELAY = 1 / 25  # Telegram: ~30 msg/s umumiy limit; xavfsiz 25/s


@dataclass
class BroadcastResult:
    sent: int = 0
    failed: int = 0
    blocked: int = 0


async def run_broadcast(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    from_chat_id: int,
    message_id: int,
) -> BroadcastResult:
    result = BroadcastResult()
    async with session_factory() as session:
        repo = UserRepository(session)
        async for batch in repo.iter_broadcast_ids():
            for telegram_id in batch:
                before = result.blocked
                await _send_one(bot, telegram_id, from_chat_id, message_id, result)
                if result.blocked > before:  # botni bloklagan -> keyingi broadcast'larda o'tkazib yuboramiz
                    await repo.set_active(telegram_id, False)
                await asyncio.sleep(SEND_DELAY)
            await session.commit()
    audit.info("broadcast_finished sent=%s failed=%s blocked=%s", result.sent, result.failed, result.blocked)
    return result


async def _send_one(bot: Bot, telegram_id: int, from_chat_id: int, message_id: int, result: BroadcastResult) -> bool:
    for attempt in range(2):
        try:
            await bot.copy_message(chat_id=telegram_id, from_chat_id=from_chat_id, message_id=message_id)
            result.sent += 1
            return True
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after + 1)
            continue
        except TelegramForbiddenError:
            result.blocked += 1
            logger.info("broadcast: user %s botni bloklagan", telegram_id)
            return False
        except TelegramAPIError as exc:
            result.failed += 1
            logger.warning("broadcast failed user=%s: %s", telegram_id, exc)
            return False
        except Exception:  # noqa: BLE001 - broadcast hech qachon crash bo'lmasin
            result.failed += 1
            logger.exception("broadcast unexpected error user=%s", telegram_id)
            return False
    result.failed += 1
    return False
