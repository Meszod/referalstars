from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User


class UserRepository:
    """Faqat DB bilan ishlaydi. Commit qilmaydi (service qatlami commit qiladi)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id).execution_options(populate_existing=True)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        stmt = (
            select(User)
            .where(func.lower(User.username) == username.lstrip("@").lower())
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def create_if_not_exists(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[User, bool]:
        """(user, created). Race-safe: UNIQUE(telegram_id) + IntegrityError fallback."""
        existing = await self.get_by_telegram_id(telegram_id)
        if existing is not None:
            existing.username = username
            existing.first_name = first_name
            existing.last_name = last_name
            existing.is_active = True
            return existing, False

        user = User(telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name)
        try:
            async with self.session.begin_nested():
                self.session.add(user)
                await self.session.flush()
        except IntegrityError:
            existing = await self.get_by_telegram_id(telegram_id)
            if existing is None:  # pragma: no cover
                raise
            return existing, False
        return user, True

    async def apply_delta(
        self,
        user_id: int,
        *,
        balance_delta: int = 0,
        earned_delta: int = 0,
        withdrawn_delta: int = 0,
    ) -> int | None:
        """Atomik UPDATE. Balans manfiyga tushadigan bo'lsa None qaytaradi (hech narsa o'zgarmaydi)."""
        stmt = (
            update(User)
            .where(User.id == user_id, User.balance + balance_delta >= 0)
            .values(
                balance=User.balance + balance_delta,
                total_earned=User.total_earned + earned_delta,
                total_withdrawn=User.total_withdrawn + withdrawn_delta,
            )
            .returning(User.balance)
            .execution_options(synchronize_session=False)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def increment_referral_count(self, user_id: int) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(referral_count=User.referral_count + 1)
            .execution_options(synchronize_session=False)
        )

    async def set_referred_by(self, user_id: int, referrer_id: int) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id, User.referred_by.is_(None))
            .values(referred_by=referrer_id)
            .execution_options(synchronize_session=False)
        )

    async def set_banned(self, user_id: int, banned: bool) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_banned=banned).execution_options(synchronize_session=False)
        )

    async def set_active(self, telegram_id: int, active: bool) -> None:
        await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(is_active=active)
            .execution_options(synchronize_session=False)
        )

    async def counts(self) -> dict[str, int]:
        total = (await self.session.execute(select(func.count(User.id)))).scalar_one()
        banned = (await self.session.execute(select(func.count(User.id)).where(User.is_banned.is_(True)))).scalar_one()
        active = (
            await self.session.execute(
                select(func.count(User.id)).where(User.is_banned.is_(False), User.is_active.is_(True))
            )
        ).scalar_one()
        return {"total": total, "banned": banned, "active": active}

    async def totals(self) -> dict[str, int]:
        row = (
            await self.session.execute(
                select(
                    func.coalesce(func.sum(User.balance), 0),
                    func.coalesce(func.sum(User.total_earned), 0),
                    func.coalesce(func.sum(User.total_withdrawn), 0),
                    func.coalesce(func.sum(User.referral_count), 0),
                )
            )
        ).one()
        return {"balance": row[0], "earned": row[1], "withdrawn": row[2], "referrals": row[3]}

    async def top_by_referrals(self, limit: int) -> list[User]:
        stmt = (
            select(User)
            .where(User.is_banned.is_(False), User.referral_count > 0)
            .order_by(User.referral_count.desc(), User.id.asc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def rank_of(self, user: User) -> int:
        higher = (
            await self.session.execute(
                select(func.count(User.id)).where(User.is_banned.is_(False), User.referral_count > user.referral_count)
            )
        ).scalar_one()
        return higher + 1

    async def list_banned(self, limit: int = 30) -> list[User]:
        stmt = select(User).where(User.is_banned.is_(True)).order_by(User.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def iter_broadcast_ids(self, batch_size: int = 500) -> AsyncIterator[list[int]]:
        """Active va banned bo'lmagan userlarning telegram_id'lari (keyset pagination)."""
        last_id = 0
        while True:
            stmt = (
                select(User.id, User.telegram_id)
                .where(User.id > last_id, User.is_active.is_(True), User.is_banned.is_(False))
                .order_by(User.id)
                .limit(batch_size)
            )
            rows = (await self.session.execute(stmt)).all()
            if not rows:
                return
            last_id = rows[-1][0]
            yield [r[1] for r in rows]
