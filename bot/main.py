import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import config
from bot.database.repository import seed_admins, seed_categories
from bot.database.session import async_session, close_db, init_db
from bot.handlers import get_all_routers
from bot.middlewares import AntiFloodMiddleware, BannedUserMiddleware
from bot.utils.logger import setup_logging

logger = logging.getLogger(__name__)


async def on_startup(bot: Bot) -> None:
    config.validate()
    await init_db()

    async with async_session() as session:
        await seed_categories(session)
        await seed_admins(session)
        await session.commit()

    me = await bot.get_me()
    logger.info("Bot started: @%s", me.username)


async def on_shutdown(bot: Bot) -> None:
    await close_db()
    logger.info("Bot stopped")


async def main() -> None:
    setup_logging()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(AntiFloodMiddleware())
    dp.callback_query.middleware(AntiFloodMiddleware())
    dp.message.middleware(BannedUserMiddleware())
    dp.callback_query.middleware(BannedUserMiddleware())

    for router in get_all_routers():
        dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


def run() -> None:
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
