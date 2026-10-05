from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import TransactionType, User
from app.database.repositories import MilestoneRepository, ReferralRepository, UserRepository
from app.services.balance_service import BalanceService
from app.services.settings_service import RuntimeSettings

logger = logging.getLogger(__name__)
audit = logging.getLogger("audit")


@dataclass
class StartResult:
    user: User
    is_new: bool
    referral_created: bool = False


@dataclass
class RewardResult:
    referrer_telegram_id: int
    reward: int
    referral_count: int
    milestones: list[tuple[int, int]] = field(default_factory=list)  # (milestone, bonus)


class ReferralService:
    def __init__(self, session: AsyncSession, settings: RuntimeSettings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.referrals = ReferralRepository(session)
        self.milestones = MilestoneRepository(session)
        self.balance = BalanceService(session)

    async def register_start(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        referrer_telegram_id: int | None = None,
    ) -> StartResult:
        """/start: userni yaratadi va (agar shartlar bajarilsa) PENDING referral yozadi.

        Reward bu yerda BERILMAYDI — referred user kanallarga obuna bo'lgach `credit_pending_referral` beradi.
        """
        user, is_new = await self.users.create_if_not_exists(
            telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name
        )
        referral_created = False

        # Faqat HAQIQIY yangi user referral bo'la oladi (mavjud userlar qayta hisoblanmaydi).
        if is_new and referrer_telegram_id is not None and not user.is_banned:
            referrer = await self.users.get_by_telegram_id(referrer_telegram_id)
            if (
                referrer is not None
                and referrer.id != user.id  # self-referral
                and not referrer.is_banned
                and await self.referrals.get_by_referred(user.id) is None  # duplicate
            ):
                await self.referrals.create(referrer.id, user.id)
                await self.users.set_referred_by(user.id, referrer.id)
                referral_created = True
                audit.info("referral_created referrer=%s referred=%s", referrer.telegram_id, telegram_id)
            else:
                logger.info("referral_rejected referrer=%s referred=%s", referrer_telegram_id, telegram_id)

        await self.session.commit()
        return StartResult(user=user, is_new=is_new, referral_created=referral_created)

    async def credit_pending_referral(self, referred: User) -> RewardResult | None:
        """Referred user obunani tasdiqlagach reward beradi. Idempotent: ikkinchi chaqiruv None qaytaradi."""
        referral = await self.referrals.get_by_referred(referred.id)
        if referral is None or referral.rewarded_at is not None:
            return None

        referrer = await self.users.get_by_id(referral.referrer_id)
        fresh_referred = await self.users.get_by_id(referred.id)
        if referrer is None or referrer.is_banned or fresh_referred is None or fresh_referred.is_banned:
            return None

        reward = await self.settings.referral_reward()
        if not await self.referrals.claim_reward(referral.id, reward):
            return None  # boshqa parallel chaqiruv allaqachon bergan

        await self.balance.apply(
            referrer.id, reward, TransactionType.REFERRAL, f"Referral: user {referred.telegram_id}"
        )
        await self.users.increment_referral_count(referrer.id)
        count = (await self.users.get_by_id(referrer.id)).referral_count  # type: ignore[union-attr]

        earned_milestones: list[tuple[int, int]] = []
        for milestone, bonus in sorted((await self.settings.milestone_bonuses()).items()):
            if bonus > 0 and count >= milestone and await self.milestones.add(referrer.id, milestone):
                await self.balance.apply(referrer.id, bonus, TransactionType.BONUS, f"Milestone: {milestone} referral")
                earned_milestones.append((milestone, bonus))

        await self.session.commit()
        audit.info(
            "referral_rewarded referrer=%s referred=%s reward=%s milestones=%s",
            referrer.telegram_id, referred.telegram_id, reward, earned_milestones,
        )
        return RewardResult(
            referrer_telegram_id=referrer.telegram_id,
            reward=reward,
            referral_count=count,
            milestones=earned_milestones,
        )
