import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select

from bot.database.models import User
from bot.database.session import async_session

logger = logging.getLogger(__name__)


async def broadcast_message(bot: Bot, text: str, admin_id: int) -> tuple[int, int]:
    sent = 0
    failed = 0

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.is_banned == False)
        )
        users = list(result.scalars().all())

    for user in users:
        try:
            await bot.send_message(user.telegram_id, text, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            failed += 1
            logger.warning("Broadcast failed for %s: %s", user.telegram_id, e)

    try:
        await bot.send_message(
            admin_id,
            f"📢 <b>Broadcast Complete</b>\n\n✅ Sent: {sent}\n❌ Failed: {failed}",
            parse_mode="HTML",
        )
    except Exception:
        pass

    return sent, failed
