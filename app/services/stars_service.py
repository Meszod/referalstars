"""Telegram Stars bilan bog'liq qism.

MUHIM CHEKLOV: Telegram Bot API'da bot balansidan foydalanuvchiga Stars'ni to'g'ridan-to'g'ri
"o'tkazib beradigan" (payout/transfer) metod yo'q. Mavjud Stars metodlari: sendInvoice /
createInvoiceLink (XTR), answerPreCheckoutQuery, refundStarPayment, getStarTransactions,
getMyStarBalance, shuningdek sovg'alar (getAvailableGifts / sendGift / convertGiftToStars).

Shuning uchun bu loyihada withdrawal MANUAL workflow: bot hisob-kitobni yuritadi, admin esa
Stars'ni Telegram orqali o'zi yuboradi va so'rovni "Approve" qiladi. Yangi imkoniyatlar paydo bo'lsa,
ularni aynan shu servisga qo'shing (README'ga qarang).
"""
from __future__ import annotations

import logging

from aiogram import Bot

from app.database.models import User, Withdrawal
from app.utils.helpers import username_or_dash

logger = logging.getLogger(__name__)


class StarsService:
    @staticmethod
    def manual_payout_instruction(withdrawal: Withdrawal, user: User) -> str:
        return (
            "ℹ️ <b>Qo‘lda to‘lov tartibi</b>\n"
            f"1. Foydalanuvchiga {withdrawal.amount} ⭐ ni Telegram orqali yuboring "
            f"({username_or_dash(user)}, ID: <code>{user.telegram_id}</code>).\n"
            "2. Keyin “✅ Approve” tugmasini bosing (Approve oldidan yuborish tavsiya etiladi).\n"
            "3. Yubora olmasangiz “❌ Reject” — balans foydalanuvchiga qaytariladi."
        )

    @staticmethod
    async def bot_star_balance(bot: Bot) -> int | None:
        """Botning Stars balansi (agar Bot API shuni qaytarsa). Xato bo'lsa None."""
        try:
            result = await bot.get_my_star_balance()
            return int(result.amount)
        except Exception:  # noqa: BLE001 - faqat ma'lumot uchun
            logger.warning("getMyStarBalance ishlamadi", exc_info=True)
            return None
