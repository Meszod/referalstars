from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TransactionType, User, WithdrawalStatus
from app.database.repositories import TransactionRepository, UserRepository, WithdrawalRepository


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.tx = TransactionRepository(session)
        self.withdrawals = WithdrawalRepository(session)

    async def user_stats(self, user: User) -> dict[str, int]:
        referral_income = await self.tx.sum_by_type(user.id, TransactionType.REFERRAL)
        bonus_income = await self.tx.sum_by_type(user.id, TransactionType.BONUS)
        return {
            "referrals": user.referral_count,
            "referral_income": referral_income,
            "bonus_income": bonus_income,
            "earned": user.total_earned,
            "withdrawn": user.total_withdrawn,
            "balance": user.balance,
        }

    async def admin_overview(self) -> dict[str, int]:
        counts = await self.users.counts()
        totals = await self.users.totals()
        return {
            **counts,
            "stars_balance": totals["balance"],
            "stars_earned": totals["earned"],
            "stars_withdrawn": totals["withdrawn"],
            "referrals": totals["referrals"],
            "pending": await self.withdrawals.count_by_status(WithdrawalStatus.PENDING),
            "approved": await self.withdrawals.count_by_status(WithdrawalStatus.APPROVED),
            "rejected": await self.withdrawals.count_by_status(WithdrawalStatus.REJECTED),
        }
