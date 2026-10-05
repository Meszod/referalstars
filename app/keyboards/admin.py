from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton as Btn
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import Channel, User


class AdminCb(CallbackData, prefix="adm"):
    action: str
    id: int = 0


def _cb(action: str, id: int = 0) -> str:
    return AdminCb(action=action, id=id).pack()


def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    items = [
        ("👥 Users", "users"), ("📊 Statistics", "stats"),
        ("💸 Withdrawals", "withdrawals"), ("📢 Broadcast", "broadcast"),
        ("📢 Channels", "channels"), ("🎁 Bonuses", "bonuses"),
        ("🏆 Leaderboard", "leaderboard"), ("⚙️ Settings", "settings"),
        ("🚫 Banned users", "banned"),
    ]
    for text, action in items:
        kb.add(Btn(text=text, callback_data=_cb(action)))
    kb.adjust(2)
    return kb.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[Btn(text="⬅️ Admin menyu", callback_data=_cb("menu"))]])


def users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [Btn(text="🔎 Qidirish (ID / @username)", callback_data=_cb("user_search"))],
            [Btn(text="⬅️ Admin menyu", callback_data=_cb("menu"))],
        ]
    )


def user_actions_kb(user: User) -> InlineKeyboardMarkup:
    ban_btn = (
        Btn(text="♻️ Unban", callback_data=_cb("unban", user.id))
        if user.is_banned
        else Btn(text="🚫 Ban", callback_data=_cb("ban", user.id))
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                Btn(text="➕ Stars qo‘shish", callback_data=_cb("add_stars", user.id)),
                Btn(text="➖ Stars ayirish", callback_data=_cb("sub_stars", user.id)),
            ],
            [ban_btn],
            [Btn(text="⬅️ Admin menyu", callback_data=_cb("menu"))],
        ]
    )


def withdrawal_kb(withdrawal_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                Btn(text="✅ Approve", callback_data=_cb("w_ok", withdrawal_id)),
                Btn(text="❌ Reject", callback_data=_cb("w_no", withdrawal_id)),
            ]
        ]
    )


def channels_menu_kb(channels: list[Channel]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(Btn(text="➕ Kanal qo‘shish", callback_data=_cb("ch_add")))
    for ch in channels:
        kb.row(Btn(text=f"➖ {ch.title}", callback_data=_cb("ch_del", ch.id)))
    kb.row(Btn(text="⬅️ Admin menyu", callback_data=_cb("menu")))
    return kb.as_markup()


def bonuses_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [Btn(text="✏️ Kunlik bonus miqdori", callback_data=_cb("set_daily"))],
            [Btn(text="✏️ Milestone bonuslari", callback_data=_cb("set_milestones"))],
            [Btn(text="⬅️ Admin menyu", callback_data=_cb("menu"))],
        ]
    )


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [Btn(text="✏️ Referral reward", callback_data=_cb("set_reward"))],
            [Btn(text="✏️ Minimal withdrawal", callback_data=_cb("set_min"))],
            [Btn(text="⬅️ Admin menyu", callback_data=_cb("menu"))],
        ]
    )


def banned_kb(users: list[User]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for u in users:
        label = f"♻️ {u.username or u.first_name or u.telegram_id}"
        kb.row(Btn(text=label[:40], callback_data=_cb("unban", u.id)))
    kb.row(Btn(text="⬅️ Admin menyu", callback_data=_cb("menu")))
    return kb.as_markup()


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                Btn(text="✅ Yuborish", callback_data=_cb("bc_go")),
                Btn(text="❌ Bekor qilish", callback_data=_cb("menu")),
            ]
        ]
    )
