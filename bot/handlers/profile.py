from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database.repository import UserRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button
from bot.utils.helpers import format_datetime

router = Router()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return
        ref_count = await UserRepo.get_referral_count(session, user.id)

    username = f"@{user.username}" if user.username else "N/A"

    text = (
        "👤 <b>Your Profile</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 User ID: <code>{user.telegram_id}</code>\n"
        f"👤 Username: {username}\n"
        f"📅 Join Date: {format_datetime(user.created_at)}\n"
        f"💰 Balance: <b>{config.currency}{user.balance:.2f}</b>\n"
        f"💳 Total Deposits: {config.currency}{user.total_deposits:.2f}\n"
        f"🛒 Total Purchases: {config.currency}{user.total_purchases:.2f}\n"
        f"📦 Total Orders: {user.total_orders}\n"
        f"🎁 Referral Earnings: {config.currency}{user.referral_earnings:.2f}\n"
        f"👥 Referrals: {ref_count}\n"
    )

    await callback.message.edit_text(
        text, reply_markup=back_button(), parse_mode="HTML"
    )
    await callback.answer()
