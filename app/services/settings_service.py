from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.repositories import SettingsRepository

DEFAULT_DAILY_BONUS = 1
# Qo'shimcha (oddiy referral rewarddan tashqari) milestone bonuslari. Admin panel orqali o'zgartiriladi.
DEFAULT_MILESTONE_BONUSES: dict[int, int] = {10: 5, 20: 10, 50: 25, 100: 50}

KEY_REFERRAL_REWARD = "referral_reward"
KEY_MIN_WITHDRAWAL = "min_withdrawal"
KEY_DAILY_BONUS = "daily_bonus"
KEY_MILESTONES = "milestone_bonuses"


class RuntimeSettings:
    """DB'dagi sozlamalar; yo'q bo'lsa .env qiymatlari default bo'ladi."""

    def __init__(self, session: AsyncSession, env: Settings) -> None:
        self.repo = SettingsRepository(session)
        self.env = env

    async def _get_int(self, key: str, default: int) -> int:
        raw = await self.repo.get(key)
        try:
            return int(raw) if raw is not None else default
        except ValueError:
            return default

    async def referral_reward(self) -> int:
        return await self._get_int(KEY_REFERRAL_REWARD, self.env.referral_reward)

    async def min_withdrawal(self) -> int:
        return await self._get_int(KEY_MIN_WITHDRAWAL, self.env.min_withdrawal)

    async def daily_bonus(self) -> int:
        return await self._get_int(KEY_DAILY_BONUS, DEFAULT_DAILY_BONUS)

    async def milestone_bonuses(self) -> dict[int, int]:
        raw = await self.repo.get(KEY_MILESTONES)
        if raw is None:
            return dict(DEFAULT_MILESTONE_BONUSES)
        try:
            return {int(k): int(v) for k, v in json.loads(raw).items()}
        except (ValueError, TypeError, AttributeError):
            return dict(DEFAULT_MILESTONE_BONUSES)

    async def set_int(self, key: str, value: int) -> None:
        await self.repo.set(key, str(value))

    async def set_milestones(self, mapping: dict[int, int]) -> None:
        await self.repo.set(KEY_MILESTONES, json.dumps({str(k): v for k, v in mapping.items()}))
