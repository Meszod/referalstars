from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import User
from app.database.repositories import UserRepository
from app.keyboards.user import CB_CHECK_SUB, main_menu, subscription_kb
from app.services.referral_service import ReferralService, RewardResult
from app.services.settings_service import RuntimeSettings
from app.services.subscription_service import SubscriptionService
from app.texts import ALL_READY, NEED_START, NOT_SUBSCRIBED, SUBSCRIBE_PROMPT, WELCOME
from app.utils.referral import parse_start_arg

logger = logging.getLogger(__name__)
router = Router(name="start")


async def notify_referrer(bot: Bot, result: RewardResult) -> None:
    text = f"🎉 <b>Yangi referral!</b>\n⭐ +{result.reward} Stars\n👥 Jami: {result.referral_count}"
    for milestone, bonus in result.milestones:
        text += f"\n🎁 {milestone} referral bonusi: +{bonus} ⭐"
    try:
        await bot.send_message(result.referrer_telegram_id, text)
    except TelegramAPIError:
        logger.info("Referrerga xabar yuborib bo‘lmadi: %s", result.referrer_telegram_id)


async def onboard(bot: Bot, session: AsyncSession, settings: Settings, user: User, target: Message) -> None:
    """Obuna tasdiqlangach: kutilayotgan referral reward'ni berish + asosiy menyu."""
    runtime = RuntimeSettings(session, settings)
    reward = await ReferralService(session, runtime).credit_pending_referral(user)
    if reward is not None:
        await notify_referrer(bot, reward)
    await target.answer(WELCOME.format(reward=await runtime.referral_reward()), reply_markup=main_menu())


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    redis: Redis,
    settings: Settings,
) -> None:
    await state.clear()
    tg = message.from_user
    if tg is None:
        return
    runtime = RuntimeSettings(session, settings)
    result = await ReferralService(session, runtime).register_start(
        telegram_id=tg.id,
        username=tg.username,
        first_name=tg.first_name,
        last_name=tg.last_name,
        referrer_telegram_id=parse_start_arg(command.args),
    )
    user = result.user
    if user.is_banned and not settings.is_admin(tg.id):
        await message.answer("🚫 Siz bloklangansiz.")
        return

    missing = await SubscriptionService(session, bot, redis).missing_channels(tg.id)
    if missing:
        await message.answer(SUBSCRIBE_PROMPT, reply_markup=subscription_kb(missing))
        return
    await onboard(bot, session, settings, user, message)


@router.callback_query(F.data == CB_CHECK_SUB)
async def cb_check_subscription(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
    redis: Redis,
    settings: Settings,
) -> None:
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return
    missing = await SubscriptionService(session, bot, redis).missing_channels(callback.from_user.id)
    if missing:
        await callback.answer(NOT_SUBSCRIBED, show_alert=True)
        return
    await callback.answer()
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(ALL_READY)
        except TelegramAPIError:
            pass
        await onboard(bot, session, settings, user, callback.message)
