from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database.models import Base, User
from app.database.repositories import UserRepository
from app.services.referral_service import ReferralService
from app.services.settings_service import RuntimeSettings


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
def env() -> Settings:
    return Settings(
        _env_file=None,
        bot_token="1:TEST",
        bot_username="test_bot",
        database_url="sqlite+aiosqlite://",
        ADMIN_IDS="1",
        referral_reward=5,
        min_withdrawal=50,
    )


@pytest_asyncio.fixture
def runtime(session: AsyncSession, env: Settings) -> RuntimeSettings:
    return RuntimeSettings(session, env)


@pytest_asyncio.fixture
def referral_service(session: AsyncSession, runtime: RuntimeSettings) -> ReferralService:
    return ReferralService(session, runtime)


async def make_user(session: AsyncSession, telegram_id: int, balance: int = 0) -> User:
    user, _ = await UserRepository(session).create_if_not_exists(
        telegram_id=telegram_id, username=f"u{telegram_id}", first_name="N", last_name=None
    )
    if balance:
        await UserRepository(session).apply_delta(user.id, balance_delta=balance, earned_delta=balance)
    await session.commit()
    return await UserRepository(session).get_by_id(user.id)  # type: ignore[return-value]
