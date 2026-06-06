from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.database.repository import AdminRepo, OrderRepo, UserRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button

router = Router()


@router.message(Command("reseller"))
async def cmd_reseller(message: Message):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, message.from_user.id)
        level = await AdminRepo.get_level(session, message.from_user.id)
        if not user:
            await message.answer("Please /start first.")
            return
        if not user.is_reseller and level is None:
            await message.answer("⛔ Reseller access only.")
            return

        orders = await OrderRepo.get_user_orders(session, user.id, limit=5)

    text = (
        "🏪 <b>Reseller Panel</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Balance: ${user.balance:.2f}\n"
        f"📦 Total Orders: {user.total_orders}\n\n"
        "Recent orders:\n"
    )
    for o in orders:
        text += f"• {o.order_id} — ${o.total_price:.2f}\n"

    await message.answer(text, parse_mode="HTML")
