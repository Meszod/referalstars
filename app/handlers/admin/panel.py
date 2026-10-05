from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import TransactionType
from app.database.repositories import UserRepository
from app.handlers.admin.common import show, user_card
from app.handlers.leaderboard import build_leaderboard_text
from app.keyboards.admin import (
    AdminCb,
    admin_menu,
    back_kb,
    banned_kb,
    user_actions_kb,
    users_menu_kb,
)
from app.services.balance_service import BalanceService, InsufficientBalance
from app.services.stats_service import StatsService
from app.states.admin import AdminStates
from app.utils.validators import parse_positive_int

audit = logging.getLogger("audit")
router = Router(name="admin_panel")

MENU_TEXT = "⚙️ <b>Admin panel</b>"


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(MENU_TEXT, reply_markup=admin_menu())


@router.callback_query(AdminCb.filter(F.action == "menu"))
async def cb_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await show(callback, MENU_TEXT, admin_menu())


# ---------------------------------------------------------------- users
@router.callback_query(AdminCb.filter(F.action == "users"))
async def cb_users(callback: CallbackQuery, session: AsyncSession) -> None:
    c = await UserRepository(session).counts()
    await show(
        callback,
        f"👥 <b>Users: {c['total']:,}</b>\n\n🟢 Active: {c['active']:,}\n🚫 Banned: {c['banned']:,}",
        users_menu_kb(),
    )


@router.callback_query(AdminCb.filter(F.action == "user_search"))
async def cb_user_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.search_user)
    await show(callback, "🔎 Telegram ID yoki @username yuboring:", back_kb())


@router.message(AdminStates.search_user, F.text, ~F.text.startswith("/"))
async def got_user_query(message: Message, state: FSMContext, session: AsyncSession) -> None:
    query = (message.text or "").strip()
    repo = UserRepository(session)
    user = await (repo.get_by_telegram_id(int(query)) if query.isdigit() else repo.get_by_username(query))
    if user is None:
        await message.answer("❌ User topilmadi. Qayta urinib ko‘ring yoki /admin.")
        return
    await state.clear()
    await message.answer(user_card(user), reply_markup=user_actions_kb(user))


@router.callback_query(AdminCb.filter(F.action.in_({"ban", "unban"})))
async def cb_ban(
    callback: CallbackQuery, callback_data: AdminCb, session: AsyncSession, settings: Settings
) -> None:
    repo = UserRepository(session)
    user = await repo.get_by_id(callback_data.id)
    if user is None:
        await callback.answer("User topilmadi", show_alert=True)
        return
    banning = callback_data.action == "ban"
    if banning and settings.is_admin(user.telegram_id):
        await callback.answer("Adminni ban qilib bo‘lmaydi", show_alert=True)
        return
    await repo.set_banned(user.id, banning)
    await session.commit()
    audit.info("admin_%s admin=%s user=%s", callback_data.action, callback.from_user.id, user.telegram_id)
    user = await repo.get_by_id(user.id)
    await show(callback, user_card(user), user_actions_kb(user))  # type: ignore[arg-type]


@router.callback_query(AdminCb.filter(F.action.in_({"add_stars", "sub_stars"})))
async def cb_adjust(callback: CallbackQuery, callback_data: AdminCb, state: FSMContext) -> None:
    sign = 1 if callback_data.action == "add_stars" else -1
    await state.set_state(AdminStates.adjust_amount)
    await state.update_data(user_id=callback_data.id, sign=sign)
    verb = "qo‘shish" if sign > 0 else "ayirish"
    await show(callback, f"⭐ Necha Stars {verb}? Butun son yuboring:", back_kb())


@router.message(AdminStates.adjust_amount, F.text, ~F.text.startswith("/"))
async def got_adjust_amount(message: Message, state: FSMContext, session: AsyncSession) -> None:
    amount = parse_positive_int(message.text)
    if amount is None:
        await message.answer("❌ Faqat butun musbat son kiriting.")
        return
    data = await state.get_data()
    user_id, sign = int(data["user_id"]), int(data["sign"])
    admin_id = message.from_user.id  # type: ignore[union-attr]
    try:
        await BalanceService(session).apply(
            user_id, sign * amount, TransactionType.ADMIN_ADJUSTMENT, f"Admin {admin_id} tomonidan"
        )
        await session.commit()
    except InsufficientBalance:
        await session.rollback()
        await message.answer("❌ Userning balansi yetarli emas.")
        return
    await state.clear()
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    audit.info("admin_adjustment admin=%s user=%s amount=%s", admin_id, user.telegram_id, sign * amount)  # type: ignore[union-attr]
    await message.answer("✅ Bajarildi.\n\n" + user_card(user), reply_markup=user_actions_kb(user))  # type: ignore[arg-type]


# ---------------------------------------------------------------- stats / leaderboard / banned
@router.callback_query(AdminCb.filter(F.action == "stats"))
async def cb_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    s = await StatsService(session).admin_overview()
    await show(
        callback,
        "📊 <b>STATISTICS</b>\n\n"
        f"👥 Users: {s['total']:,} (🟢 {s['active']:,} / 🚫 {s['banned']:,})\n"
        f"🔗 Referrals: {s['referrals']:,}\n\n"
        f"⭐ Userlar balansi (jami): {s['stars_balance']:,}\n"
        f"💰 Jami ishlab topilgan: {s['stars_earned']:,}\n"
        f"💸 Jami yechilgan: {s['stars_withdrawn']:,}\n\n"
        f"🆕 Pending: {s['pending']}  ✅ Approved: {s['approved']}  ❌ Rejected: {s['rejected']}",
        back_kb(),
    )


@router.callback_query(AdminCb.filter(F.action == "leaderboard"))
async def cb_leaderboard(callback: CallbackQuery, session: AsyncSession) -> None:
    top = await UserRepository(session).top_by_referrals(20)
    await show(callback, build_leaderboard_text(top), back_kb())


@router.callback_query(AdminCb.filter(F.action == "banned"))
async def cb_banned(callback: CallbackQuery, session: AsyncSession) -> None:
    users = await UserRepository(session).list_banned(30)
    text = "🚫 <b>Banned users</b>\n\n" + ("Bloklangan userlar yo‘q." if not users else "Unban qilish uchun tanlang:")
    await show(callback, text, banned_kb(users))
