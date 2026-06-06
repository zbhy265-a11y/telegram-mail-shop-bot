from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database.repository import OrderRepo, UserRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button

router = Router()


@router.callback_query(F.data == "statistics")
async def show_statistics(callback: CallbackQuery):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return

        orders = await OrderRepo.get_user_orders(session, user.id, limit=1000)
        total_spent = sum(o.total_price for o in orders)
        total_items = sum(o.quantity for o in orders)

    text = (
        "📊 <b>Your Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 Total Orders: <b>{user.total_orders}</b>\n"
        f"🛒 Items Purchased: <b>{total_items}</b>\n"
        f"💵 Total Spent: <b>{config.currency}{total_spent:.2f}</b>\n"
        f"💳 Total Deposits: <b>{config.currency}{user.total_deposits:.2f}</b>\n"
        f"💰 Current Balance: <b>{config.currency}{user.balance:.2f}</b>\n"
        f"🎁 Referral Earnings: <b>{config.currency}{user.referral_earnings:.2f}</b>\n"
    )

    await callback.message.edit_text(
        text, reply_markup=back_button(), parse_mode="HTML"
    )
    await callback.answer()
