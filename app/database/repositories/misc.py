from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import DailyBonusClaim, Setting, UserMilestone


class MilestoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, milestone: int) -> bool:
        """True -> milestone shu chaqiruvda birinchi marta yozildi (UNIQUE constraint himoyasi)."""
        exists = await self.session.execute(
            select(UserMilestone.id).where(UserMilestone.user_id == user_id, UserMilestone.milestone == milestone)
        )
        if exists.scalar_one_or_none() is not None:
            return False
        try:
            async with self.session.begin_nested():
                self.session.add(UserMilestone(user_id=user_id, milestone=milestone))
                await self.session.flush()
        except IntegrityError:
            return False
        return True


class BonusRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def last_claim(self, user_id: int) -> DailyBonusClaim | None:
        stmt = (
            select(DailyBonusClaim)
            .where(DailyBonusClaim.user_id == user_id)
            .order_by(DailyBonusClaim.claim_date.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def add_claim(self, user_id: int, claim_date: date, amount: int, streak: int) -> bool:
        try:
            async with self.session.begin_nested():
                self.session.add(DailyBonusClaim(user_id=user_id, claim_date=claim_date, amount=amount, streak=streak))
                await self.session.flush()
        except IntegrityError:
            return False
        return True


class SettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> str | None:
        row = await self.session.get(Setting, key)
        return row.value if row else None

    async def set(self, key: str, value: str) -> None:
        row = await self.session.get(Setting, key)
        if row is None:
            self.session.add(Setting(key=key, value=value))
        else:
            row.value = value
        await self.session.flush()
