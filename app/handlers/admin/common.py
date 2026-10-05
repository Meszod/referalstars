from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.database.models import User, Withdrawal
from app.utils.helpers import fmt_date, username_or_dash


async def show(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup | None = None) -> None:
    """Callback xabarini tahrirlaydi (iloji bo'lmasa yangi xabar yuboradi)."""
    await callback.answer()
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest:
            await callback.message.answer(text, reply_markup=kb)


def user_card(user: User) -> str:
    status = "🚫 Banned" if user.is_banned else "🟢 Active"
    return (
        "👤 <b>USER</b>\n\n"
        f"ID: <code>{user.telegram_id}</code>\n"
        f"Username: {username_or_dash(user)}\n\n"
        f"Balance: {user.balance} ⭐\n"
        f"Referrals: {user.referral_count}\n"
        f"Earned: {user.total_earned} ⭐\n"
        f"Withdrawn: {user.total_withdrawn} ⭐\n\n"
        f"Status: {status}"
    )


def withdrawal_card(w: Withdrawal, user: User, status_label: str | None = None) -> str:
    label = status_label or w.status.capitalize()
    return (
        "💸 <b>WITHDRAWAL</b>\n\n"
        f"👤 {username_or_dash(user)}\n"
        f"🆔 <code>{user.telegram_id}</code>\n\n"
        f"⭐ Amount: {w.amount}\n"
        f"🕐 Date: {fmt_date(w.created_at)}\n\n"
        f"Status: {label}"
    )
