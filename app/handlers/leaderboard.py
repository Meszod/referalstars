from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.database.repositories import UserRepository
from app.keyboards.user import BTN_LEADERBOARD
from app.utils.helpers import display_name

router = Router(name="leaderboard")

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


def build_leaderboard_text(top: list[User], my_rank: int | None = None) -> str:
    lines = ["🏆 <b>TOP REFERRAL</b>\n"]
    if not top:
        lines.append("Hozircha reyting bo‘sh.")
    for i, u in enumerate(top, start=1):
        if i in MEDALS:
            lines.append(f"{MEDALS[i]} {i}. {display_name(u)} — {u.referral_count} referrals")
        else:
            lines.append(f"{i}. {display_name(u)} — {u.referral_count}")
    if my_rank is not None:
        lines.append(f"\n📍 Sizning o‘rningiz: <b>#{my_rank}</b>")
    return "\n".join(lines)


@router.message(F.text == BTN_LEADERBOARD)
async def show_leaderboard(message: Message, db_user: User, session: AsyncSession) -> None:
    repo = UserRepository(session)
    top = await repo.top_by_referrals(10)
    rank = await repo.rank_of(db_user)
    await message.answer(build_leaderboard_text(top, rank))
