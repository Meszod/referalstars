from __future__ import annotations

from sqlalchemy import func, select

from app.database.models import Referral, TransactionType, UserMilestone
from app.database.repositories import TransactionRepository, UserRepository
from app.services.referral_service import ReferralService
from tests.conftest import make_user


def _start(svc: ReferralService, tg_id: int, ref: int | None = None):
    return svc.register_start(
        telegram_id=tg_id, username=f"u{tg_id}", first_name="N", last_name=None, referrer_telegram_id=ref
    )


async def test_new_user_is_created(referral_service, session):
    res = await _start(referral_service, 100)
    assert res.is_new and not res.referral_created
    assert res.user.balance == 0
    again = await _start(referral_service, 100)
    assert not again.is_new


async def test_valid_referral_pending_then_rewarded(referral_service, session):
    await _start(referral_service, 1)
    res = await _start(referral_service, 2, ref=1)
    assert res.referral_created

    users = UserRepository(session)
    # Obuna tasdiqlanmaguncha reward YO'Q
    assert (await users.get_by_telegram_id(1)).balance == 0

    reward = await referral_service.credit_pending_referral(res.user)
    assert reward is not None and reward.reward == 5 and reward.referral_count == 1
    referrer = await users.get_by_telegram_id(1)
    assert referrer.balance == 5 and referrer.total_earned == 5 and referrer.referral_count == 1
    txs = await TransactionRepository(session).list_for_user(referrer.id)
    assert [(t.type, t.amount) for t in txs] == [("referral", 5)]


async def test_reward_is_idempotent(referral_service, session):
    await _start(referral_service, 1)
    res = await _start(referral_service, 2, ref=1)
    assert await referral_service.credit_pending_referral(res.user) is not None
    assert await referral_service.credit_pending_referral(res.user) is None
    assert (await UserRepository(session).get_by_telegram_id(1)).balance == 5


async def test_self_referral_rejected(referral_service, session):
    res = await _start(referral_service, 7, ref=7)
    assert res.is_new and not res.referral_created
    assert (await session.execute(select(func.count(Referral.id)))).scalar_one() == 0


async def test_unknown_referrer_rejected(referral_service):
    res = await _start(referral_service, 8, ref=999999)
    assert not res.referral_created


async def test_existing_user_not_counted_as_referral(referral_service, session):
    await _start(referral_service, 1)
    await _start(referral_service, 2)  # 2 avval kirgan
    res = await _start(referral_service, 2, ref=1)  # keyin boshqa link orqali
    assert not res.is_new and not res.referral_created
    assert (await session.execute(select(func.count(Referral.id)))).scalar_one() == 0


async def test_duplicate_referral_counted_once(referral_service, session):
    await _start(referral_service, 1)
    await _start(referral_service, 3)
    res = await _start(referral_service, 2, ref=1)
    again = await _start(referral_service, 2, ref=3)  # ikkinchi referrer bilan urinish
    assert res.referral_created and not again.referral_created
    ref = (await session.execute(select(Referral))).scalars().all()
    assert len(ref) == 1 and ref[0].referrer_id == (await UserRepository(session).get_by_telegram_id(1)).id


async def test_banned_referrer_not_counted(referral_service, session):
    await _start(referral_service, 1)
    users = UserRepository(session)
    u1 = await users.get_by_telegram_id(1)
    await users.set_banned(u1.id, True)
    await session.commit()
    res = await _start(referral_service, 2, ref=1)
    assert not res.referral_created


async def test_referrer_banned_after_pending_gets_no_reward(referral_service, session):
    await _start(referral_service, 1)
    res = await _start(referral_service, 2, ref=1)
    users = UserRepository(session)
    await users.set_banned((await users.get_by_telegram_id(1)).id, True)
    await session.commit()
    assert await referral_service.credit_pending_referral(res.user) is None
    assert (await users.get_by_telegram_id(1)).balance == 0


async def test_milestone_bonus_given_once(referral_service, session, runtime):
    await runtime.set_milestones({3: 7})
    await session.commit()
    await _start(referral_service, 1)
    last = None
    for i in range(2, 6):  # 4 ta referral
        res = await _start(referral_service, i, ref=1)
        last = await referral_service.credit_pending_referral(res.user)
    users = UserRepository(session)
    referrer = await users.get_by_telegram_id(1)
    assert referrer.referral_count == 4
    assert referrer.balance == 4 * 5 + 7  # 20 + bitta milestone bonusi
    bonus_sum = await TransactionRepository(session).sum_by_type(referrer.id, TransactionType.BONUS)
    assert bonus_sum == 7
    assert (await session.execute(select(func.count(UserMilestone.id)))).scalar_one() == 1
    assert last is not None and last.milestones == []  # 4-referralda milestone qaytarilmagan
