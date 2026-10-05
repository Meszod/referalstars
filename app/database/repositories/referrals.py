from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Referral


class ReferralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_referred(self, referred_user_id: int) -> Referral | None:
        stmt = (
            select(Referral)
            .where(Referral.referred_user_id == referred_user_id)
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, referrer_id: int, referred_user_id: int) -> Referral:
        ref = Referral(referrer_id=referrer_id, referred_user_id=referred_user_id, reward=0)
        self.session.add(ref)
        await self.session.flush()
        return ref

    async def claim_reward(self, referral_id: int, reward: int) -> bool:
        """Idempotent: rewarded_at faqat bir marta yoziladi. True -> aynan shu chaqiruv reward'ni 'oldi'."""
        stmt = (
            update(Referral)
            .where(Referral.id == referral_id, Referral.rewarded_at.is_(None))
            .values(rewarded_at=func.now(), reward=reward)
            .returning(Referral.id)
            .execution_options(synchronize_session=False)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def count_pending(self, referrer_id: int) -> int:
        stmt = select(func.count(Referral.id)).where(
            Referral.referrer_id == referrer_id, Referral.rewarded_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())
