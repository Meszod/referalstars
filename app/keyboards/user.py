from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Channel

BTN_PROFILE = "👤 Profilim"
BTN_REFERRAL = "🔗 Referal"
BTN_BONUS = "🎁 Bonuslar"
BTN_LEADERBOARD = "🏆 Reyting"
BTN_WITHDRAW = "💸 Stars yechish"
BTN_STATS = "📊 Statistika"

MENU_BUTTONS = {BTN_PROFILE, BTN_REFERRAL, BTN_BONUS, BTN_LEADERBOARD, BTN_WITHDRAW, BTN_STATS}

CB_CHECK_SUB = "check_sub"
CB_CLAIM_BONUS = "bonus_claim"
CB_CANCEL_WITHDRAW = "withdraw_cancel"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_REFERRAL)],
            [KeyboardButton(text=BTN_BONUS), KeyboardButton(text=BTN_LEADERBOARD)],
            [KeyboardButton(text=BTN_WITHDRAW), KeyboardButton(text=BTN_STATS)],
        ],
        resize_keyboard=True,
    )


def channel_url(ch: Channel) -> str | None:
    if ch.invite_link:
        return ch.invite_link
    if ch.username:
        return f"https://t.me/{ch.username.lstrip('@')}"
    return None


def subscription_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        url = channel_url(ch)
        if url:
            kb.row(InlineKeyboardButton(text=f"📢 {ch.title}", url=url))
    kb.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data=CB_CHECK_SUB))
    return kb.as_markup()


def claim_bonus_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🎁 Bonusni olish", callback_data=CB_CLAIM_BONUS)]]
    )


def cancel_withdraw_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Bekor qilish", callback_data=CB_CANCEL_WITHDRAW)]]
    )
