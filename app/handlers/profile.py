from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.keyboards.user import BTN_PROFILE, BTN_STATS
from app.services.stats_service import StatsService
from app.utils.helpers import fmt_date, username_or_dash

router = Router(name="profile")


@router.message(F.text == BTN_PROFILE)
async def show_profile(message: Message, db_user: User) -> None:
    await message.answer(
        "👤 <b>PROFIL</b>\n\n"
        f"🆔 ID: <code>{db_user.telegram_id}</code>\n"
        f"👤 Username: {username_or_dash(db_user)}\n\n"
        f"👥 Referallar: {db_user.referral_count}\n"
        f"⭐ Balans: {db_user.balance}\n"
        f"💰 Jami ishlab topilgan: {db_user.total_earned}\n"
        f"💸 Yechilgan: {db_user.total_withdrawn}\n\n"
        f"📅 Ro‘yxatdan o‘tgan: {fmt_date(db_user.created_at)}"
    )


@router.message(F.text == BTN_STATS)
async def show_stats(message: Message, db_user: User, session: AsyncSession) -> None:
    s = await StatsService(session).user_stats(db_user)
    await message.answer(
        "📊 <b>STATISTIKA</b>\n\n"
        f"👥 Siz taklif qilganlar: {s['referrals']}\n"
        f"⭐ Referral orqali: {s['referral_income']} Stars\n"
        f"🎁 Bonuslar: {s['bonus_income']} Stars\n\n"
        f"💰 Jami daromad: {s['earned']} Stars\n"
        f"💸 Yechilgan: {s['withdrawn']} Stars\n"
        f"⭐ Hozirgi balans: {s['balance']} Stars"
    )
