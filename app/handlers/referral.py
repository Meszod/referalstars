from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import User
from app.keyboards.referral import referral_kb
from app.keyboards.user import BTN_REFERRAL
from app.services.settings_service import RuntimeSettings
from app.utils.referral import build_referral_link

router = Router(name="referral")

MILESTONES_SHOWN = (1, 3, 5, 10, 20, 50, 100)


@router.message(F.text == BTN_REFERRAL)
async def show_referral(message: Message, db_user: User, session: AsyncSession, settings: Settings) -> None:
    runtime = RuntimeSettings(session, settings)
    reward = await runtime.referral_reward()
    bonuses = await runtime.milestone_bonuses()
    link = build_referral_link(settings.bot_username, db_user.telegram_id)

    lines = []
    for m in MILESTONES_SHOWN:
        extra = f" + 🎁 {bonuses[m]} ⭐ bonus" if m in bonuses else ""
        mark = "✅" if db_user.referral_count >= m else "👥"
        lines.append(f"{mark} {m} referral → {m * reward} ⭐{extra}")

    await message.answer(
        "🔗 <b>SIZNING REFERAL LINKINGIZ</b>\n\n"
        "Do‘stlaringizni taklif qiling va Stars yig‘ing!\n\n"
        f"👥 Taklif qilinganlar: {db_user.referral_count}\n"
        f"⭐ Jami ishlab topilgan: {db_user.total_earned} Stars\n\n"
        f"🔗 Sizning linkingiz:\n{link}\n\n"
        "🎯 <b>Milestone’lar:</b>\n" + "\n".join(lines) + "\n\n"
        "<i>Referral do‘stingiz majburiy kanallarga obuna bo‘lgach hisoblanadi.</i>",
        reply_markup=referral_kb(link),
        disable_web_page_preview=True,
    )
