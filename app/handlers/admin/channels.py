from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories import ChannelRepository
from app.handlers.admin.common import show
from app.keyboards.admin import AdminCb, back_kb, channels_menu_kb
from app.states.admin import AdminStates
from app.utils.helpers import esc

audit = logging.getLogger("audit")
router = Router(name="admin_channels")

ADD_HELP = (
    "➕ <b>Kanal qo‘shish</b>\n\n"
    "Birinchi qatorda kanal <code>@username</code> yoki ID (<code>-100...</code>) yuboring.\n"
    "Private kanal bo‘lsa, ikkinchi qatorda invite link ham yuboring:\n\n"
    "<code>-1001234567890\nhttps://t.me/+AbCdEf...</code>\n\n"
    "⚠️ Bot kanalda <b>administrator</b> bo‘lishi shart (aks holda obunani tekshira olmaydi).\n"
    "Bekor qilish: /admin"
)


async def _channels_text_and_kb(session: AsyncSession):
    channels = await ChannelRepository(session).list_active()
    if channels:
        lines = [f"{i}. {esc(c.title)} — <code>{c.channel_id}</code>" for i, c in enumerate(channels, 1)]
        text = "📢 <b>Majburiy kanallar</b>\n\n" + "\n".join(lines) + "\n\n➖ o‘chirish uchun kanal tugmasini bosing."
    else:
        text = "📢 <b>Majburiy kanallar</b>\n\nHozircha kanal yo‘q. Obuna tekshiruvi o‘chiq."
    return text, channels_menu_kb(channels)


@router.callback_query(AdminCb.filter(F.action == "channels"))
async def cb_channels(callback: CallbackQuery, session: AsyncSession) -> None:
    text, kb = await _channels_text_and_kb(session)
    await show(callback, text, kb)


@router.callback_query(AdminCb.filter(F.action == "ch_add"))
async def cb_channel_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.channel_add)
    await show(callback, ADD_HELP, back_kb())


@router.message(AdminStates.channel_add, F.text, ~F.text.startswith("/"))
async def got_channel(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    lines = [ln.strip() for ln in (message.text or "").splitlines() if ln.strip()]
    ident_raw = lines[0]
    custom_link = lines[1] if len(lines) > 1 else None
    identifier: int | str = int(ident_raw) if ident_raw.lstrip("-").isdigit() else (
        ident_raw if ident_raw.startswith("@") else f"@{ident_raw}"
    )
    if custom_link and not custom_link.startswith("https://t.me/"):
        await message.answer("❌ Invite link https://t.me/ bilan boshlanishi kerak.")
        return

    try:
        chat = await bot.get_chat(identifier)
        me = await bot.get_chat_member(chat.id, bot.id)
    except TelegramAPIError as exc:
        await message.answer(f"❌ Kanal topilmadi yoki bot kanalda yo‘q: {esc(str(exc))}")
        return
    if str(getattr(me.status, "value", me.status)) not in {"administrator", "creator"}:
        await message.answer("❌ Bot bu kanalda administrator emas. Avval botni admin qiling.")
        return

    link = custom_link or (f"https://t.me/{chat.username}" if chat.username else None)
    if link is None:
        await message.answer("❌ Private kanal uchun ikkinchi qatorda invite link yuboring.")
        return

    repo = ChannelRepository(session)
    if await repo.get_by_channel_id(chat.id) is not None:
        await message.answer("⚠️ Bu kanal allaqachon qo‘shilgan.")
        return
    await repo.add(channel_id=chat.id, username=chat.username, title=chat.title or str(chat.id), invite_link=link)
    await session.commit()
    await state.clear()
    audit.info("admin_channel_added admin=%s channel=%s", message.from_user.id, chat.id)  # type: ignore[union-attr]
    text, kb = await _channels_text_and_kb(session)
    await message.answer("✅ Kanal qo‘shildi.\n\n" + text, reply_markup=kb)


@router.callback_query(AdminCb.filter(F.action == "ch_del"))
async def cb_channel_del(callback: CallbackQuery, callback_data: AdminCb, session: AsyncSession) -> None:
    repo = ChannelRepository(session)
    removed = await repo.remove(callback_data.id)
    await session.commit()
    if removed:
        audit.info("admin_channel_removed admin=%s channel_pk=%s", callback.from_user.id, callback_data.id)
    text, kb = await _channels_text_and_kb(session)
    await show(callback, text, kb)
