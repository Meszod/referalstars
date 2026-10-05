from __future__ import annotations

import pytest

from app.database.models import WithdrawalStatus
from app.database.repositories import TransactionRepository, UserRepository, WithdrawalRepository
from app.services.balance_service import InsufficientBalance
from app.services.withdrawal_service import AlreadyProcessed, BelowMinimum, WithdrawalService
from tests.conftest import make_user


@pytest.fixture
def svc(session, runtime):
    return WithdrawalService(session, runtime)


async def test_create_reserves_balance(session, svc):
    user = await make_user(session, 1, balance=125)
    w = await svc.create(user, 100)
    assert w.status == "pending" and w.amount == 100
    fresh = await UserRepository(session).get_by_id(user.id)
    assert fresh.balance == 25 and fresh.total_withdrawn == 0
    txs = await TransactionRepository(session).list_for_user(user.id)
    assert [(t.type, t.amount) for t in txs] == [("withdrawal", -100)]


async def test_insufficient_balance(session, svc):
    user = await make_user(session, 1, balance=60)
    uid = user.id
    with pytest.raises(InsufficientBalance):
        await svc.create(user, 100)
    assert (await UserRepository(session).get_by_id(uid)).balance == 60
    assert await WithdrawalRepository(session).count_by_status(WithdrawalStatus.PENDING) == 0


async def test_below_minimum(session, svc):
    user = await make_user(session, 1, balance=100)
    with pytest.raises(BelowMinimum):
        await svc.create(user, 49)


async def test_cannot_overspend_with_multiple_requests(session, svc):
    user = await make_user(session, 1, balance=100)
    uid = user.id
    await svc.create(user, 60)
    user = await UserRepository(session).get_by_id(uid)
    with pytest.raises(InsufficientBalance):
        await svc.create(user, 60)  # ikkinchi so'rov balansdan ortiq
    assert (await UserRepository(session).get_by_id(uid)).balance == 40


async def test_admin_approval(session, svc):
    user = await make_user(session, 1, balance=100)
    w = await svc.create(user, 100)
    approved, u = await svc.approve(w.id, admin_telegram_id=1)
    assert approved.status == "approved" and approved.admin_id == 1 and approved.processed_at is not None
    assert u.total_withdrawn == 100 and u.balance == 0


async def test_admin_rejection_refunds(session, svc):
    user = await make_user(session, 1, balance=100)
    w = await svc.create(user, 80)
    rejected, u = await svc.reject(w.id, admin_telegram_id=1)
    assert rejected.status == "rejected" and u.balance == 100 and u.total_withdrawn == 0
    txs = await TransactionRepository(session).list_for_user(user.id)
    assert [(t.type, t.amount) for t in txs] == [("withdrawal", -80), ("refund", 80)]


async def test_duplicate_processing_is_blocked(session, svc):
    user = await make_user(session, 1, balance=100)
    uid = user.id
    w = await svc.create(user, 100)
    wid = w.id
    await svc.approve(wid, 1)
    with pytest.raises(AlreadyProcessed):
        await svc.approve(wid, 1)
    with pytest.raises(AlreadyProcessed):
        await svc.reject(wid, 1)  # approve'dan keyin reject => refund bo'lmaydi
    fresh = await UserRepository(session).get_by_id(uid)
    assert fresh.balance == 0 and fresh.total_withdrawn == 100


async def test_reject_then_approve_blocked(session, svc):
    user = await make_user(session, 1, balance=100)
    uid = user.id
    w = await svc.create(user, 100)
    wid = w.id
    await svc.reject(wid, 1)
    with pytest.raises(AlreadyProcessed):
        await svc.approve(wid, 1)
    assert (await UserRepository(session).get_by_id(uid)).total_withdrawn == 0
