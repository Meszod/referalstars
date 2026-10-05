from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ErrorEvent

from app.texts import GENERIC_ERROR

logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent) -> bool:
    # traceback errors.log fayliga tushadi (token redact filter orqali tozalanadi)
    logger.error("Unhandled exception: %s", event.exception, exc_info=event.exception)
    update = event.update
    try:
        if update.message:
            await update.message.answer(GENERIC_ERROR)
        elif update.callback_query:
            await update.callback_query.answer(GENERIC_ERROR, show_alert=True)
    except TelegramAPIError:
        pass
    return True
