from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database.models import PaymentStatus
from bot.database.repository import PaymentRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back, admin_payment_actions, admin_payments_keyboard
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.message(Command("payments"))
async def cmd_payments(message: Message):
    if not await _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        payments = await PaymentRepo.get_pending(session)

    if not payments:
        await message.answer("💳 No pending payments.")
        return

    await message.answer(
        f"💳 <b>{len(payments)} Pending Payments</b>\nUse /admin → Payments to manage.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_payments")
async def admin_payments(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        payments = await PaymentRepo.get_pending(session)

    if not payments:
        await callback.message.edit_text(
            "💳 No pending payments.",
            reply_markup=admin_back(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "💳 <b>Pending Payments</b>",
        reply_markup=admin_payments_keyboard(payments),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^adm_pay_\d+$"))
async def admin_payment_detail(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    payment_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        payment = await PaymentRepo.get_by_id(session, payment_id)

    if not payment:
        await callback.answer("Not found", show_alert=True)
        return

    text = (
        f"💳 <b>Payment #{payment.id}</b>\n"
        f"👤 User: {payment.user.telegram_id}\n"
        f"💰 ${payment.amount:.2f}\n"
        f"📋 {payment.method.value}\n"
        f"Status: {payment.status.value}"
    )

    if payment.screenshot_file_id:
        await callback.message.answer_photo(
            payment.screenshot_file_id,
            caption=text,
            reply_markup=admin_payment_actions(payment_id),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=admin_payment_actions(payment_id),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_pay_ok_"))
async def approve_payment(callback: CallbackQuery, bot):
    if not await _is_admin(callback.from_user.id):
        return

    payment_id = int(callback.data.split("_")[3])
    async with async_session() as session:
        payment = await PaymentRepo.get_by_id(session, payment_id)
        if not payment or payment.status != PaymentStatus.PENDING:
            await callback.answer("Already processed", show_alert=True)
            return

        await PaymentRepo.approve(session, payment)
        await session.commit()
        user_id = payment.user.telegram_id
        amount = payment.amount

    await callback.answer("✅ Approved!", show_alert=True)

    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Payment Approved!</b>\n\n"
            f"💰 {config.currency}{amount:.2f} added to your balance.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await callback.message.edit_text(f"✅ Payment #{payment_id} approved.")


@router.callback_query(F.data.startswith("adm_pay_no_"))
async def reject_payment_start(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        return

    payment_id = int(callback.data.split("_")[3])
    await state.set_state(AdminStates.reject_payment_note)
    await state.update_data(reject_payment_id=payment_id)
    await callback.message.edit_text("Enter rejection reason (optional):")


@router.message(AdminStates.reject_payment_note)
async def reject_payment(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    payment_id = data.get("reject_payment_id")
    note = message.text.strip()

    async with async_session() as session:
        payment = await PaymentRepo.get_by_id(session, payment_id)
        if payment and payment.status == PaymentStatus.PENDING:
            await PaymentRepo.reject(session, payment, note)
            await session.commit()
            user_id = payment.user.telegram_id

            try:
                await bot.send_message(
                    user_id,
                    f"❌ <b>Payment Rejected</b>\n\n{note or 'Contact support for details.'}",
                    parse_mode="HTML",
                )
            except Exception:
                pass

    await state.clear()
    await message.answer(f"❌ Payment #{payment_id} rejected.")
