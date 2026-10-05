from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TransactionType, User, Withdrawal, WithdrawalStatus
from app.database.repositories import UserRepository, WithdrawalRepository
from app.services.balance_service import BalanceService, InsufficientBalance
from app.services.settings_service import RuntimeSettings

logger = logging.getLogger(__name__)
audit = logging.getLogger("audit")


class BelowMinimum(Exception):
    def __init__(self, minimum: int) -> None:
        super().__init__(f"minimum={minimum}")
        self.minimum = minimum


class AlreadyProcessed(Exception):
    pass


class WithdrawalService:
    """Balans so'rov yaratilganda ZAXIRALANADI (yechiladi). Reject bo'lsa refund qilinadi.

    Shu sababli bir vaqtda ko'p so'rov yuborib balansdan ortiq so'rash mumkin emas.
    """

    def __init__(self, session: AsyncSession, settings: RuntimeSettings) -> None:
        self.session = session
        self.settings = settings
        self.repo = WithdrawalRepository(session)
        self.users = UserRepository(session)
        self.balance = BalanceService(session)

    async def create(self, user: User, amount: int) -> Withdrawal:
        minimum = await self.settings.min_withdrawal()
        if amount <= 0 or amount < minimum:
            raise BelowMinimum(minimum)
        user_id, telegram_id = user.id, user.telegram_id  # rollback'dan keyin obyekt expire bo'ladi
        withdrawal = await self.repo.create(user_id, amount)
        try:
            await self.balance.apply(
                user_id, -amount, TransactionType.WITHDRAWAL, f"Withdrawal #{withdrawal.id} (zaxiralandi)"
            )
        except InsufficientBalance:
            await self.session.rollback()
            raise
        await self.session.commit()
        audit.info("withdrawal_created id=%s user=%s amount=%s", withdrawal.id, telegram_id, amount)
        return withdrawal

    async def approve(self, withdrawal_id: int, admin_telegram_id: int) -> tuple[Withdrawal, User]:
        w = await self.repo.claim(withdrawal_id, WithdrawalStatus.APPROVED, admin_telegram_id)
        if w is None:
            await self.session.rollback()
            raise AlreadyProcessed(f"withdrawal={withdrawal_id}")
        # Balans so'rov yaratilganda allaqachon yechilgan; bu yerda faqat total_withdrawn oshadi.
        await self.users.apply_delta(w.user_id, withdrawn_delta=w.amount)
        user = await self.users.get_by_id(w.user_id)
        await self.session.commit()
        audit.info("withdrawal_approved id=%s admin=%s amount=%s", w.id, admin_telegram_id, w.amount)
        return w, user  # type: ignore[return-value]

    async def reject(self, withdrawal_id: int, admin_telegram_id: int) -> tuple[Withdrawal, User]:
        w = await self.repo.claim(withdrawal_id, WithdrawalStatus.REJECTED, admin_telegram_id)
        if w is None:
            await self.session.rollback()
            raise AlreadyProcessed(f"withdrawal={withdrawal_id}")
        await self.balance.apply(w.user_id, w.amount, TransactionType.REFUND, f"Withdrawal #{w.id} rad etildi")
        user = await self.users.get_by_id(w.user_id)
        await self.session.commit()
        audit.info("withdrawal_rejected id=%s admin=%s amount=%s", w.id, admin_telegram_id, w.amount)
        return w, user  # type: ignore[return-value]
