from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.handlers.admin.common import show
from app.keyboards.admin import AdminCb, back_kb, bonuses_kb, settings_kb
from app.services import settings_service as keys
from app.services.settings_service import RuntimeSettings
from app.states.admin import AdminStates
from app.utils.validators import parse_milestones, parse_positive_int

audit = logging.getLogger("audit")
router = Router(name="admin_settings")

PROMPTS = {
    "set_daily": (keys.KEY_DAILY_BONUS, "🎁 Kunlik bonus miqdorini kiriting (0 — o‘chirish):"),
    "set_milestones": (
        keys.KEY_MILESTONES,
        "🎯 Milestone bonuslarini <code>referral:bonus</code> ko‘rinishida vergul bilan yuboring.\n"
        "Masalan: <code>10:5, 20:10, 50:25</code>\n(o‘chirish uchun: <code>0</code>)",
    ),
    "set_reward": (keys.KEY_REFERRAL_REWARD, "⭐ Har bir referral uchun reward (butun son):"),
    "set_min": (keys.KEY_MIN_WITHDRAWAL, "💸 Minimal withdrawal miqdori (butun son):"),
}


@router.callback_query(AdminCb.filter(F.action == "bonuses"))
async def cb_bonuses(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    rt = RuntimeSettings(session, settings)
    ms = await rt.milestone_bonuses()
    ms_text = ", ".join(f"{k}→+{v}" for k, v in sorted(ms.items())) or "—"
    await show(
        callback,
        "🎁 <b>Bonuses</b>\n\n"
        f"Kunlik bonus: <b>{await rt.daily_bonus()} ⭐</b>\n"
        f"Milestone bonuslari: {ms_text}",
        bonuses_kb(),
    )


@router.callback_query(AdminCb.filter(F.action == "settings"))
async def cb_settings(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    rt = RuntimeSettings(session, settings)
    await show(
        callback,
        "⚙️ <b>Settings</b>\n\n"
        f"Referral reward: <b>{await rt.referral_reward()} ⭐</b>\n"
        f"Minimal withdrawal: <b>{await rt.min_withdrawal()} ⭐</b>",
        settings_kb(),
    )


@router.callback_query(AdminCb.filter(F.action.in_(set(PROMPTS))))
async def cb_edit_setting(callback: CallbackQuery, callback_data: AdminCb, state: FSMContext) -> None:
    key, prompt = PROMPTS[callback_data.action]
    await state.set_state(AdminStates.setting_value)
    await state.update_data(key=key)
    await show(callback, prompt, back_kb())


@router.message(AdminStates.setting_value, F.text, ~F.text.startswith("/"))
async def got_setting_value(message: Message, state: FSMContext, session: AsyncSession, settings: Settings) -> None:
    key = (await state.get_data())["key"]
    rt = RuntimeSettings(session, settings)
    text = (message.text or "").strip()

    if key == keys.KEY_MILESTONES:
        mapping = parse_milestones(text)
        if mapping is None:
            await message.answer("❌ Format noto‘g‘ri. Masalan: <code>10:5, 20:10</code>")
            return
        await rt.set_milestones(mapping)
    else:
        value = 0 if (key == keys.KEY_DAILY_BONUS and text == "0") else parse_positive_int(text)
        if value is None:
            await message.answer("❌ Faqat butun musbat son kiriting.")
            return
        await rt.set_int(key, value)

    await session.commit()
    await state.clear()
    audit.info("admin_setting_changed admin=%s key=%s value=%s", message.from_user.id, key, text)  # type: ignore[union-attr]
    await message.answer("✅ Saqlandi.", reply_markup=back_kb())
