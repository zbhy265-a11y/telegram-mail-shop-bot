from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database.models import PaymentMethod
from bot.database.repository import PaymentRepo, UserRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button, deposit_confirm_keyboard, payment_methods_keyboard
from bot.utils.states import DepositStates

router = Router()

PAYMENT_DETAILS = {
    PaymentMethod.BINANCE: ("💳 Binance Pay", "binance_pay_id"),
    PaymentMethod.USDT_TRC20: ("💵 USDT TRC20", "usdt_trc20"),
    PaymentMethod.USDT_BEP20: ("💵 USDT BEP20", "usdt_bep20"),
    PaymentMethod.BKASH: ("🇧🇩 bKash", "bkash_number"),
    PaymentMethod.NAGAD: ("🇧🇩 Nagad", "nagad_number"),
    PaymentMethod.ROCKET: ("🇧🇩 Rocket", "rocket_number"),
}


@router.callback_query(F.data == "deposit")
async def show_deposit(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 <b>Add Balance</b>\n\nSelect your payment method:",
        reply_markup=payment_methods_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay_"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    method_str = callback.data.replace("pay_", "")
    try:
        method = PaymentMethod(method_str)
    except ValueError:
        await callback.answer("Invalid method", show_alert=True)
        return

    label, config_key = PAYMENT_DETAILS[method]
    address = getattr(config, config_key, "")

    await state.set_state(DepositStates.waiting_amount)
    await state.update_data(payment_method=method_str)

    text = (
        f"{label}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 Send payment to:\n<code>{address or 'Contact admin'}</code>\n\n"
        f"Minimum deposit: {config.currency}{config.min_deposit:.2f}\n\n"
        "Enter the amount you deposited:"
    )
    await callback.message.edit_text(
        text, reply_markup=back_button("deposit"), parse_mode="HTML"
    )
    await callback.answer()


@router.message(DepositStates.waiting_amount)
async def deposit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace("$", ""))
        if amount < config.min_deposit:
            raise ValueError()
    except ValueError:
        await message.answer(
            f"❌ Enter a valid amount (min {config.currency}{config.min_deposit:.2f})"
        )
        return

    data = await state.get_data()
    method_str = data.get("payment_method")
    await state.update_data(deposit_amount=amount)
    await state.set_state(DepositStates.waiting_screenshot)

    await message.answer(
        f"💰 Amount: <b>{config.currency}{amount:.2f}</b>\n\n"
        "📸 Now send a screenshot of your payment.\n"
        "You can also include a transaction reference in the caption.",
        reply_markup=deposit_confirm_keyboard(method_str),
        parse_mode="HTML",
    )


@router.message(DepositStates.waiting_screenshot, F.photo)
async def deposit_screenshot(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    amount = data.get("deposit_amount")
    method_str = data.get("payment_method")
    ref = message.caption or ""

    if not amount or not method_str:
        await message.answer("❌ Session expired. Please start again.")
        await state.clear()
        return

    method = PaymentMethod(method_str)
    file_id = message.photo[-1].file_id

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Please /start first")
            await state.clear()
            return

        payment = await PaymentRepo.create(
            session, user, amount, method, file_id, ref or None
        )
        await session.commit()
        payment_id = payment.id

    await state.clear()

    await message.answer(
        f"✅ <b>Payment Submitted!</b>\n\n"
        f"🆔 Payment ID: <code>#{payment_id}</code>\n"
        f"💰 Amount: {config.currency}{amount:.2f}\n"
        f"⏳ Status: Pending review\n\n"
        "You will be notified once approved.",
        parse_mode="HTML",
    )

    for admin_id in config.admin_ids:
        try:
            await bot.send_photo(
                admin_id,
                file_id,
                caption=(
                    f"💳 <b>New Payment #{payment_id}</b>\n\n"
                    f"👤 User: {message.from_user.id}\n"
                    f"💰 Amount: {config.currency}{amount:.2f}\n"
                    f"📋 Method: {method.value}\n"
                    f"📝 Ref: {ref or 'N/A'}"
                ),
                parse_mode="HTML",
                reply_markup=_admin_payment_kb(payment_id),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("deposit_confirm_"))
async def deposit_confirm_no_photo(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        "Please send a screenshot of your payment as a photo.", show_alert=True
    )


def _admin_payment_kb(payment_id: int):
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Approve", callback_data=f"adm_pay_ok_{payment_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Reject", callback_data=f"adm_pay_no_{payment_id}"
                ),
            ]
        ]
    )
