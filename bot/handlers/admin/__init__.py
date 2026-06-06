from aiogram import Router

from bot.handlers.admin import coupons, panel, payments, products, stock, tickets, users


def get_admin_router() -> Router:
    router = Router()
    router.include_router(panel.router)
    router.include_router(products.router)
    router.include_router(payments.router)
    router.include_router(users.router)
    router.include_router(tickets.router)
    router.include_router(coupons.router)
    router.include_router(stock.router)
    return router
