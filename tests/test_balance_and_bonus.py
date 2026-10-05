from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.database.models import TransactionType
from app.database.repositories import TransactionRepository, UserRepository
from app.services.balance_service import BalanceService, InsufficientBalance
from app.services.bonus_service import AlreadyClaimed, BonusService
from tests.conftest import make_user


async def test_balance_apply_records_transaction(session):
    user = await make_user(session, 1)
    svc = BalanceService(session)
    assert await svc.apply(user.id, 10, TransactionType.BONUS, "x") == 10
    assert await svc.apply(user.id, -4, TransactionType.ADMIN_ADJUSTMENT, "y") == 6
    await session.commit()
    fresh = await UserRepository(session).get_by_id(user.id)
    assert fresh.balance == 6 and fresh.total_earned == 10  # admin adjustment 'earned'ga kirmaydi
    txs = await TransactionRepository(session).list_for_user(user.id)
    assert [t.amount for t in txs] == [10, -4]


async def test_balance_never_negative(session):
    user = await make_user(session, 1, balance=5)
    uid = user.id
    with pytest.raises(InsufficientBalance):
        await BalanceService(session).apply(uid, -6, TransactionType.ADMIN_ADJUSTMENT)
    await session.rollback()
    assert (await UserRepository(session).get_by_id(uid)).balance == 5


async def test_daily_bonus_once_per_day_and_streak(session, runtime, env):
    user = await make_user(session, 1)
    svc = BonusService(session, runtime, env.timezone)
    d1 = date(2026, 10, 1)
    s1 = await svc.claim_daily(user, today=d1)
    assert s1.streak == 1 and s1.amount == 1
    with pytest.raises(AlreadyClaimed):
        await svc.claim_daily(user, today=d1)
    s2 = await svc.claim_daily(user, today=d1 + timedelta(days=1))
    assert s2.streak == 2
    s3 = await svc.claim_daily(user, today=d1 + timedelta(days=5))  # ketma-ketlik uzildi
    assert s3.streak == 1
    assert (await UserRepository(session).get_by_id(user.id)).balance == 3
