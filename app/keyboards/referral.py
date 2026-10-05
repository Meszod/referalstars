from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.referral import build_share_url


def referral_kb(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Do‘stlarga yuborish", url=build_share_url(link))],
            [InlineKeyboardButton(text="📋 Linkni nusxalash", copy_text=CopyTextButton(text=link))],
        ]
    )
