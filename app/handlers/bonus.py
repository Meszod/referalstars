from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import User
from app.keyboards.user import BTN_BONUS, CB_CLAIM_BONUS, claim_bonus_kb
from app.services.bonus_service import AlreadyClaimed, BonusDisabled, BonusService, BonusStatus
from app.services.settings_service import RuntimeSettings

router = Router(name="bonus")


def _text(status: BonusStatus, note: str = "") -> str:
    return (
        "🎁 <b>Kunlik bonus</b>\n\n"
        f"Bugungi bonus:\n<b>+{status.amount} ⭐</b>\n\n"
        f"🔥 Ketma-ket kunlar: {status.streak}\n\n"
        + (note or ("✅ Bugungi bonus olingan. Ertaga qaytib keling!" if status.claimed_today else "Bonusni olish uchun tugmani bosing 👇"))
    )


def _service(session: AsyncSession, settings: Settings) -> BonusService:
    return BonusService(session, RuntimeSettings(session, settings), settings.timezone)


@router.message(F.text == BTN_BONUS)
async def show_bonus(message: Message, db_user: User, session: AsyncSession, settings: Settings) -> None:
    status = await _service(session, settings).status(db_user)
    kb = None if status.claimed_today or status.amount <= 0 else claim_bonus_kb()
    await message.answer(_text(status), reply_markup=kb)


@router.callback_query(F.data == CB_CLAIM_BONUS)
async def claim_bonus(callback: CallbackQuery, db_user: User, session: AsyncSession, settings: Settings) -> None:
    svc = _service(session, settings)
    try:
        status = await svc.claim_daily(db_user)
    except AlreadyClaimed:
        await callback.answer("Bugungi bonus allaqachon olingan.", show_alert=True)
        return
    except BonusDisabled:
        await callback.answer("Kunlik bonus hozircha o‘chirilgan.", show_alert=True)
        return
    await callback.answer(f"+{status.amount} ⭐")
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(_text(status, f"✅ Siz +{status.amount} ⭐ oldingiz!"))
        except TelegramAPIError:
            pass
