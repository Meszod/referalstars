from aiogram import Router

from app.handlers import bonus, errors, leaderboard, menu, profile, referral, start, withdraw
from app.handlers.admin import build_admin_router
from app.middlewares.subscription import SubscriptionMiddleware


def build_user_router() -> Router:
    router = Router(name="user")
    router.message.middleware(SubscriptionMiddleware())
    router.callback_query.middleware(SubscriptionMiddleware())
    # withdraw birinchi: FSM state handler menyu tugmalaridan oldin ishlashi kerak
    router.include_routers(
        withdraw.router, profile.router, referral.router, bonus.router, leaderboard.router, menu.router
    )
    return router


def register_routers(dp) -> None:
    dp.include_router(errors.router)
    dp.include_router(start.router)
    dp.include_router(build_admin_router())
    dp.include_router(build_user_router())
