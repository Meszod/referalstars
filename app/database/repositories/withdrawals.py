from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Withdrawal, WithdrawalStatus


class WithdrawalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int, amount: int) -> Withdrawal:
        w = Withdrawal(user_id=user_id, amount=amount, status=WithdrawalStatus.PENDING.value)
        self.session.add(w)
        await self.session.flush()
        return w

    async def get(self, withdrawal_id: int) -> Withdrawal | None:
        stmt = select(Withdrawal).where(Withdrawal.id == withdrawal_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def claim(self, withdrawal_id: int, new_status: WithdrawalStatus, admin_id: int) -> Withdrawal | None:
        """Faqat 'pending' holatdagi so'rovni o'tkazadi. Double approve/reject mumkin emas."""
        stmt = (
            update(Withdrawal)
            .where(Withdrawal.id == withdrawal_id, Withdrawal.status == WithdrawalStatus.PENDING.value)
            .values(status=WithdrawalStatus(new_status).value, processed_at=func.now(), admin_id=admin_id)
            .returning(Withdrawal.id)
            .execution_options(synchronize_session=False)
        )
        if (await self.session.execute(stmt)).scalar_one_or_none() is None:
            return None
        return await self.get(withdrawal_id)

    async def list_pending(self, limit: int = 10) -> list[Withdrawal]:
        stmt = (
            select(Withdrawal)
            .where(Withdrawal.status == WithdrawalStatus.PENDING.value)
            .order_by(Withdrawal.id)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, status: WithdrawalStatus) -> int:
        stmt = select(func.count(Withdrawal.id)).where(Withdrawal.status == WithdrawalStatus(status).value)
        return int((await self.session.execute(stmt)).scalar_one())
