from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import WithdrawalStatus
from app.database.repositories import UserRepository, WithdrawalRepository
from app.handlers.admin.common import show, withdrawal_card
from app.keyboards.admin import AdminCb, back_kb, withdrawal_kb
from app.services.settings_service import RuntimeSettings
from app.services.stars_service import StarsService
from app.services.withdrawal_service import AlreadyProcessed, WithdrawalService

logger = logging.getLogger(__name__)
router = Router(name="admin_withdrawals")


@router.callback_query(AdminCb.filter(F.action == "withdrawals"))
async def cb_withdrawals(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    repo = WithdrawalRepository(session)
    users = UserRepository(session)
    pending_count = await repo.count_by_status(WithdrawalStatus.PENDING)
    pending = await repo.list_pending(10)
    bot_balance = await StarsService.bot_star_balance(bot)
    text = f"💸 <b>Withdrawals</b>\n\n🆕 Pending: {pending_count}"
    if bot_balance is not None:
        text += f"\n⭐ Botning Stars balansi: {bot_balance}"
    if pending_count > len(pending):
        text += f"\n\n<i>Eng eskirgan {len(pending)} ta ko‘rsatilmoqda.</i>"
    await show(callback, text, back_kb())
    if isinstance(callback.message, Message):
        for w in pending:
            user = await users.get_by_id(w.user_id)
            if user is not None:
                await callback.message.answer(withdrawal_card(w, user), reply_markup=withdrawal_kb(w.id))


@router.callback_query(AdminCb.filter(F.action.in_({"w_ok", "w_no"})))
async def cb_process(
    callback: CallbackQuery, callback_data: AdminCb, session: AsyncSession, bot: Bot, settings: Settings
) -> None:
    svc = WithdrawalService(session, RuntimeSettings(session, settings))
    approving = callback_data.action == "w_ok"
    admin_id = callback.from_user.id
    try:
        if approving:
            w, user = await svc.approve(callback_data.id, admin_id)
        else:
            w, user = await svc.reject(callback_data.id, admin_id)
    except AlreadyProcessed:
        await callback.answer("⚠️ Bu so‘rov allaqachon ko‘rib chiqilgan.", show_alert=True)
        if isinstance(callback.message, Message):
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramAPIError:
                pass
        return

    label = f"✅ Approved ({admin_id})" if approving else f"❌ Rejected ({admin_id})"
    text = withdrawal_card(w, user, label)
    if approving:
        text += "\n\n" + StarsService.manual_payout_instruction(w, user)
    await callback.answer("Bajarildi")
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=None)
        except TelegramAPIError:
            pass

    user_text = (
        f"✅ <b>Withdrawal so‘rovingiz tasdiqlandi.</b>\n\n⭐ Miqdor: {w.amount} Stars"
        if approving
        else f"❌ <b>Withdrawal so‘rovingiz rad etildi.</b>\n\n⭐ {w.amount} Stars balansingizga qaytarildi."
    )
    try:
        await bot.send_message(user.telegram_id, user_text)
    except TelegramAPIError:
        logger.info("Userga withdrawal notification yuborilmadi: %s", user.telegram_id)
