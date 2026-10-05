from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from app.keyboards.user import main_menu

router = Router(name="menu")


@router.message(F.text & ~F.text.startswith("/"))
async def fallback(message: Message) -> None:
    """Tanilmagan matn: asosiy menyuni ko'rsatamiz."""
    await message.answer("Quyidagi menyudan foydalaning 👇", reply_markup=main_menu())
