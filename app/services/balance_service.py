from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TransactionType
from app.database.repositories import TransactionRepository, UserRepository

logger = logging.getLogger(__name__)


class InsufficientBalance(Exception):
    pass


class BalanceService:
    """Balansni o'zgartirishning YAGONA yo'li.

    Atomik `UPDATE ... WHERE balance + delta >= 0` + transactions yozuvi.
    Commit qilmaydi: chaqiruvchi service bitta DB tranzaksiyada commit qiladi.
    """

    EARNING_TYPES = {TransactionType.REFERRAL, TransactionType.BONUS}

    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.transactions = TransactionRepository(session)

    async def apply(
        self,
        user_id: int,
        amount: int,
        tx_type: TransactionType,
        description: str = "",
        *,
        withdrawn_delta: int = 0,
    ) -> int:
        if amount == 0:
            raise ValueError("amount 0 bo‘lishi mumkin emas")
        tx_type = TransactionType(tx_type)
        earned = amount if (tx_type in self.EARNING_TYPES and amount > 0) else 0
        new_balance = await self.users.apply_delta(
            user_id, balance_delta=amount, earned_delta=earned, withdrawn_delta=withdrawn_delta
        )
        if new_balance is None:
            raise InsufficientBalance(f"user={user_id} amount={amount}")
        await self.transactions.add(user_id, amount, tx_type, description)
        return new_balance
