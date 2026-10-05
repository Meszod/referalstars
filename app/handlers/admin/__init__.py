from aiogram import Router

from app.handlers.admin import broadcast, channels, panel, settings, withdrawals
from app.middlewares.admin_only import AdminOnlyMiddleware


def build_admin_router() -> Router:
    router = Router(name="admin")
    router.message.middleware(AdminOnlyMiddleware())
    router.callback_query.middleware(AdminOnlyMiddleware())
    router.include_routers(
        panel.router, withdrawals.router, broadcast.router, channels.router, settings.router
    )
    return router
