from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.repository import CouponRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button
from bot.utils.states import CouponStates

router = Router()


@router.callback_query(F.data == "coupon")
async def coupon_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CouponStates.waiting_code)
    await callback.message.edit_text(
        "🎟 <b>Redeem Coupon</b>\n\nEnter your coupon code:",
        reply_markup=back_button(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CouponStates.waiting_code)
async def redeem_coupon(message: Message, state: FSMContext):
    code = message.text.strip().upper()

    async with async_session() as session:
        from bot.database.repository import UserRepo

        user = await UserRepo.get_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Please /start first")
            await state.clear()
            return

        coupon = await CouponRepo.get_by_code(session, code)
        if not coupon:
            await message.answer("❌ Invalid coupon code.")
            return

        error = await CouponRepo.validate_for_user(session, coupon, user.id)
        if error:
            await message.answer(f"❌ {error}")
            return

    await state.update_data(active_coupon=code)
    await state.set_state(None)

    await message.answer(
        f"✅ <b>Coupon Applied!</b>\n\n"
        f"Code: <code>{code}</code>\n"
        f"Discount: <b>{coupon.discount_percent}%</b>\n\n"
        "Your next purchase will use this discount.",
        parse_mode="HTML",
    )
