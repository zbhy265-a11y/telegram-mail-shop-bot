from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.repository import CouponRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back, admin_coupons_keyboard
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.callback_query(F.data == "adm_coupons")
async def admin_coupons(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "🎟 <b>Coupon Management</b>",
        reply_markup=admin_coupons_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_new_coupon")
async def new_coupon_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.create_coupon_code)
    await callback.message.edit_text(
        "Enter coupon code:",
        reply_markup=admin_back("adm_coupons"),
    )
    await callback.answer()


@router.message(AdminStates.create_coupon_code)
async def new_coupon_code(message: Message, state: FSMContext):
    await state.update_data(coupon_code=message.text.strip().upper())
    await state.set_state(AdminStates.create_coupon_discount)
    await message.answer("Enter discount percentage (e.g. 10):")


@router.message(AdminStates.create_coupon_discount)
async def new_coupon_discount(message: Message, state: FSMContext):
    try:
        discount = float(message.text.strip())
    except ValueError:
        await message.answer("Invalid number")
        return
    await state.update_data(coupon_discount=discount)
    await state.set_state(AdminStates.create_coupon_expiry)
    await message.answer("Enter expiry date (YYYY-MM-DD) or 'none':")


@router.message(AdminStates.create_coupon_expiry)
async def new_coupon_expiry(message: Message, state: FSMContext):
    text = message.text.strip().lower()
    expiry = None
    if text != "none":
        try:
            expiry = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            await message.answer("Invalid date format")
            return

    await state.update_data(coupon_expiry=expiry)
    await state.set_state(AdminStates.create_coupon_limit)
    await message.answer("Enter usage limit (0 = unlimited):")


@router.message(AdminStates.create_coupon_limit)
async def new_coupon_limit(message: Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid number")
        return

    data = await state.get_data()

    async with async_session() as session:
        coupon = await CouponRepo.create(
            session,
            code=data["coupon_code"],
            discount_percent=data["coupon_discount"],
            expiry_date=data.get("coupon_expiry"),
            usage_limit=limit,
        )
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Coupon <code>{coupon.code}</code> created ({coupon.discount_percent}% off)",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_list_coupons")
async def list_coupons(callback: CallbackQuery):
    async with async_session() as session:
        coupons = await CouponRepo.get_all(session)

    if not coupons:
        await callback.answer("No coupons", show_alert=True)
        return

    lines = []
    for c in coupons[:20]:
        status = "✅" if c.is_active else "❌"
        lines.append(
            f"{status} <code>{c.code}</code> — {c.discount_percent}% "
            f"({c.used_count}/{c.usage_limit or '∞'})"
        )

    await callback.message.edit_text(
        "🎟 <b>Coupons</b>\n\n" + "\n".join(lines),
        reply_markup=admin_back("adm_coupons"),
        parse_mode="HTML",
    )
    await callback.answer()
