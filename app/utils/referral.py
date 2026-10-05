from __future__ import annotations

from urllib.parse import quote


def build_referral_link(bot_username: str, telegram_id: int) -> str:
    return f"https://t.me/{bot_username.lstrip('@')}?start={telegram_id}"


def build_share_url(link: str, text: str = "🚀 Telegram Stars yig‘ing! Menga qo‘shiling:") -> str:
    return f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(text)}"


def parse_start_arg(args: str | None) -> int | None:
    """`/start 123456789` -> 123456789. Noto'g'ri qiymat -> None."""
    if not args:
        return None
    args = args.strip()
    if args.isdigit() and len(args) <= 15:
        return int(args)
    return None
