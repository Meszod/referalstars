from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TransactionType, User
from app.database.repositories import BonusRepository
from app.services.balance_service import BalanceService
from app.services.settings_service import RuntimeSettings

logger = logging.getLogger(__name__)


class AlreadyClaimed(Exception):
    pass


class BonusDisabled(Exception):
    pass


@dataclass
class BonusStatus:
    amount: int
    streak: int
    claimed_today: bool


class BonusService:
    def __init__(self, session: AsyncSession, settings: RuntimeSettings, timezone: str = "UTC") -> None:
        self.session = session
        self.settings = settings
        self.tz = ZoneInfo(timezone)
        self.repo = BonusRepository(session)
        self.balance = BalanceService(session)

    def today(self) -> date:
        return datetime.now(self.tz).date()

    async def status(self, user: User, today: date | None = None) -> BonusStatus:
        today = today or self.today()
        last = await self.repo.last_claim(user.id)
        streak = 0
        if last and last.claim_date >= today - timedelta(days=1):
            streak = last.streak
        return BonusStatus(
            amount=await self.settings.daily_bonus(),
            streak=streak,
            claimed_today=bool(last and last.claim_date == today),
        )

    async def claim_daily(self, user: User, today: date | None = None) -> BonusStatus:
        today = today or self.today()
        amount = await self.settings.daily_bonus()
        if amount <= 0:
            raise BonusDisabled
        last = await self.repo.last_claim(user.id)
        if last and last.claim_date == today:
            raise AlreadyClaimed
        streak = last.streak + 1 if last and last.claim_date == today - timedelta(days=1) else 1
        # UNIQUE(user_id, claim_date): parallel bosishda ham faqat bittasi o'tadi
        if not await self.repo.add_claim(user.id, today, amount, streak):
            await self.session.rollback()
            raise AlreadyClaimed
        await self.balance.apply(user.id, amount, TransactionType.BONUS, f"Kunlik bonus (streak {streak})")
        await self.session.commit()
        return BonusStatus(amount=amount, streak=streak, claimed_today=True)
