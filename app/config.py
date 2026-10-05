"""Ilova sozlamalari (.env / environment orqali). Tokenlar kodga yozilmaydi."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    bot_token: str
    bot_username: str
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")

    referral_reward: int = 5
    min_withdrawal: int = 50

    timezone: str = "Asia/Tashkent"
    log_level: str = "INFO"
    log_dir: str = "logs"

    @field_validator("bot_username")
    @classmethod
    def _strip_at(cls, v: str) -> str:
        return v.strip().lstrip("@")

    @property
    def admin_ids(self) -> frozenset[int]:
        ids: set[int] = set()
        for part in self.admin_ids_raw.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                ids.add(int(part))
        return frozenset(ids)

    def is_admin(self, telegram_id: int | None) -> bool:
        return telegram_id is not None and telegram_id in self.admin_ids


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
