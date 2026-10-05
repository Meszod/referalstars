from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiohttp import web
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.database.database import create_engine, create_session_factory
from app.handlers import register_routers
from app.logging_config import setup_logging
from app.middlewares.db import DbSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.middlewares.user_context import UserContextMiddleware

logger = logging.getLogger(__name__)


async def start_health_server() -> web.AppRunner | None:
    """Render web service uchun kichik HTTP server (faqat PORT berilgan bo'lsa)."""
    port = os.getenv("PORT")
    if not port:
        return None

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(port)).start()
    logger.info("Health server :%s portda ishga tushdi", port)
    return runner


async def main() -> None:
    settings = get_settings()
    setup_logging(settings)
    logger.info("Bot ishga tushmoqda (admins=%d)", len(settings.admin_ids))

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    async with engine.connect() as conn:  # DB ulanishini boshida tekshiramiz
        await conn.execute(text("SELECT 1"))

    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis.ping()
    storage = RedisStorage.from_url(settings.redis_url)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage, settings=settings, redis=redis)

    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.update.outer_middleware(UserContextMiddleware())
    throttling = ThrottlingMiddleware(redis)
    dp.message.outer_middleware(throttling)
    dp.callback_query.outer_middleware(throttling)
    register_routers(dp)

    health_runner = await start_health_server()

    try:
        await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish")])
        me = await bot.get_me()
        logger.info("Bot tayyor: @%s", me.username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Bot to‘xtatilmoqda")
        if health_runner is not None:
            await health_runner.cleanup()
        await bot.session.close()
        await storage.close()
        await redis.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
