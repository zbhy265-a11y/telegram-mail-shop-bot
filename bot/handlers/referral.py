from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database.repository import ReferralRepo, UserRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button, referral_keyboard

router = Router()


@router.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery, bot):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return
        ref_count = await UserRepo.get_referral_count(session, user.id)

    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.referral_code}"

    text = (
        "🎁 <b>Referral Program</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔗 Your Link:\n<code>{link}</code>\n\n"
        f"💰 Commission: <b>{config.referral_commission}%</b> per purchase\n"
        f"👥 Total Referrals: <b>{ref_count}</b>\n"
        f"💵 Earnings: <b>{config.currency}{user.referral_earnings:.2f}</b>\n\n"
        "Share your link and earn on every purchase!"
    )

    await callback.message.edit_text(
        text, reply_markup=referral_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ref_withdraw")
async def withdraw_referral(callback: CallbackQuery):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return

        amount = await ReferralRepo.withdraw_earnings(session, user)
        await session.commit()

    if amount <= 0:
        await callback.answer("No earnings to withdraw", show_alert=True)
        return

    await callback.answer(f"✅ ${amount:.2f} added to balance!", show_alert=True)
    await show_referral(callback, callback.bot)
