from __future__ import annotations

from datetime import datetime
from html import escape

from app.database.models import User


def esc(value: str | None) -> str:
    return escape(value or "", quote=False)


def display_name(user: User) -> str:
    """Leaderboard/ro'yxatlar uchun: @username yoki first_name."""
    if user.username:
        return f"@{esc(user.username)}"
    return esc(user.first_name) or f"ID {user.telegram_id}"


def username_or_dash(user: User) -> str:
    return f"@{esc(user.username)}" if user.username else "—"


def fmt_date(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y") if dt else "—"
