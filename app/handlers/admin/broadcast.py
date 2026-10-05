from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.handlers.admin.common import show
from app.keyboards.admin import AdminCb, back_kb, broadcast_confirm_kb
from app.services.broadcast_service import run_broadcast
from app.states.admin import AdminStates

audit = logging.getLogger("audit")
logger = logging.getLogger(__name__)
router = Router(name="admin_broadcast")

_tasks: set[asyncio.Task] = set()  # background task'larga reference (GC'dan saqlash)


@router.callback_query(AdminCb.filter(F.action == "broadcast"))
async def cb_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_message)
    await show(
        callback,
        "📢 <b>Broadcast</b>\n\nYubormoqchi bo‘lgan xabaringizni yuboring (matn, rasm, video...).\nBekor qilish: /admin",
        back_kb(),
    )


@router.message(AdminStates.broadcast_message, ~F.text.startswith("/"))
async def got_broadcast_message(message: Message, state: FSMContext) -> None:
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id)
    await state.set_state(AdminStates.broadcast_confirm)
    await message.reply("Yuqoridagi xabar barcha active userlarga yuborilsinmi?", reply_markup=broadcast_confirm_kb())


@router.callback_query(AdminCb.filter(F.action == "bc_go"), AdminStates.broadcast_confirm)
async def cb_broadcast_go(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = await state.get_data()
    await state.clear()
    admin_id = callback.from_user.id
    chat_id, message_id = int(data["chat_id"]), int(data["message_id"])
    await show(callback, "⏳ Broadcast boshlandi. Tugagach hisobot yuboraman.", back_kb())
    audit.info("broadcast_started admin=%s", admin_id)

    async def _job() -> None:
        try:
            result = await run_broadcast(bot, session_factory, from_chat_id=chat_id, message_id=message_id)
            report = (
                "✅ <b>Broadcast tugadi</b>\n\n"
                f"📨 Yuborildi: {result.sent}\n🚫 Bloklagan: {result.blocked}\n⚠️ Xato: {result.failed}"
            )
        except Exception:  # noqa: BLE001
            logger.exception("Broadcast crashed")
            report = "❌ Broadcast jarayonida xatolik yuz berdi. Loglarni tekshiring."
        try:
            await bot.send_message(admin_id, report)
        except Exception:  # noqa: BLE001
            logger.warning("Broadcast hisobotini yuborib bo‘lmadi")

    task = asyncio.create_task(_job())
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
