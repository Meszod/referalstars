from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import User
from app.keyboards.admin import withdrawal_kb
from app.keyboards.user import (
    BTN_WITHDRAW,
    CB_CANCEL_WITHDRAW,
    MENU_BUTTONS,
    cancel_withdraw_kb,
    main_menu,
)
from app.services.balance_service import InsufficientBalance
from app.services.settings_service import RuntimeSettings
from app.services.withdrawal_service import BelowMinimum, WithdrawalService
from app.states.withdraw import WithdrawStates
from app.utils.helpers import fmt_date, username_or_dash
from app.utils.validators import parse_positive_int

logger = logging.getLogger(__name__)
router = Router(name="withdraw")


@router.message(F.text == BTN_WITHDRAW)
async def start_withdraw(
    message: Message, db_user: User, state: FSMContext, session: AsyncSession, settings: Settings
) -> None:
    minimum = await RuntimeSettings(session, settings).min_withdrawal()
    head = f"⭐ Sizning balansingiz: <b>{db_user.balance} Stars</b>\n\nMinimal yechish: {minimum} Stars\n\n"
    if db_user.balance < minimum:
        await state.clear()
        await message.answer(head + f"❌ Yechish uchun kamida {minimum} Stars kerak.")
        return
    await state.set_state(WithdrawStates.amount)
    await message.answer(
        head + f"💸 <b>Qancha Stars yechmoqchisiz?</b>\n\nMinimal: {minimum}\nMaksimal: {db_user.balance}",
        reply_markup=cancel_withdraw_kb(),
    )


@router.callback_query(F.data == CB_CANCEL_WITHDRAW)
async def cancel_cb(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Bekor qilindi")
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text("❌ Withdrawal bekor qilindi.")
        except TelegramAPIError:
            pass


@router.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=main_menu())


@router.message(WithdrawStates.amount, F.text)
async def receive_amount(
    message: Message,
    db_user: User,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    bot: Bot,
) -> None:
    text = message.text or ""
    if text in MENU_BUTTONS or text.startswith("/"):
        await state.clear()
        await message.answer("❌ Withdrawal bekor qilindi. Kerakli bo‘limni qayta tanlang.", reply_markup=main_menu())
        return

    runtime = RuntimeSettings(session, settings)
    minimum = await runtime.min_withdrawal()
    amount = parse_positive_int(text)
    if amount is None:
        await message.answer("❌ Iltimos, faqat butun musbat son kiriting (masalan: 100).")
        return
    if amount < minimum:
        await message.answer(f"❌ Minimal miqdor: {minimum} Stars.")
        return
    if amount > db_user.balance:
        await message.answer(f"❌ Balansingiz yetarli emas. Maksimal: {db_user.balance} Stars.")
        return

    try:
        withdrawal = await WithdrawalService(session, runtime).create(db_user, amount)
    except InsufficientBalance:
        await message.answer("❌ Balansingiz yetarli emas.")
        return
    except BelowMinimum as exc:
        await message.answer(f"❌ Minimal miqdor: {exc.minimum} Stars.")
        return

    await state.clear()
    await message.answer(
        "✅ <b>Withdrawal so‘rovingiz qabul qilindi.</b>\n\n"
        f"⭐ Miqdor: {amount} Stars\n"
        "🕐 Status: Kutilmoqda",
        reply_markup=main_menu(),
    )

    card = (
        "💸 <b>YANGI WITHDRAWAL</b>\n\n"
        f"👤 {username_or_dash(db_user)}\n🆔 <code>{db_user.telegram_id}</code>\n\n"
        f"⭐ Amount: {amount}\n🕐 Date: {fmt_date(withdrawal.created_at)}\n\nStatus: Pending"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, card, reply_markup=withdrawal_kb(withdrawal.id))
        except TelegramAPIError:
            logger.warning("Adminga withdrawal xabari yuborilmadi: %s", admin_id)
