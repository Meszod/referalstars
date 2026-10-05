from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, TransactionType


class TransactionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, user_id: int, amount: int, tx_type: TransactionType, description: str | None = None) -> Transaction:
        tx = Transaction(user_id=user_id, amount=amount, type=TransactionType(tx_type).value, description=description)
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def sum_by_type(self, user_id: int, tx_type: TransactionType) -> int:
        stmt = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id, Transaction.type == TransactionType(tx_type).value
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_for_user(self, user_id: int) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.id)
        return list((await self.session.execute(stmt)).scalars().all())
