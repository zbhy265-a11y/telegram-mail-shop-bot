from aiogram import Router

from bot.handlers import (
    balance,
    coupon,
    orders,
    profile,
    referral,
    reseller,
    shop,
    start,
    statistics,
    support,
)
from bot.handlers.admin import get_admin_router


def get_all_routers() -> list[Router]:
    return [
        start.router,
        shop.router,
        balance.router,
        orders.router,
        profile.router,
        referral.router,
        support.router,
        statistics.router,
        coupon.router,
        reseller.router,
        get_admin_router(),
    ]
