from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database.models import TicketStatus
from bot.database.repository import TicketRepo, UserRepo
from bot.database.session import async_session
from bot.keyboards.user import (
    back_button,
    support_keyboard,
    ticket_detail_keyboard,
    tickets_keyboard,
)
from bot.utils.states import SupportStates

router = Router()


@router.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    text = "🎫 <b>Support Center</b>\n\nHow can we help you?"
    if config.support_username:
        text += f"\n\nDirect: @{config.support_username}"
    await callback.message.edit_text(
        text, reply_markup=support_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "ticket_new")
async def ticket_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_subject)
    await callback.message.edit_text(
        "📝 Enter the subject of your ticket:",
        reply_markup=back_button("support"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(SupportStates.waiting_subject)
async def ticket_subject(message: Message, state: FSMContext):
    subject = message.text.strip()[:255]
    if len(subject) < 3:
        await message.answer("Subject too short. Try again.")
        return

    await state.update_data(ticket_subject=subject)
    await state.set_state(SupportStates.waiting_message)
    await message.answer(
        "💬 Describe your issue in detail:",
        reply_markup=back_button("support"),
    )


@router.message(SupportStates.waiting_message)
async def ticket_message(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    subject = data.get("ticket_subject", "Support Request")
    body = message.text.strip()

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Please /start first")
            await state.clear()
            return

        ticket = await TicketRepo.create(session, user, subject)
        await TicketRepo.add_message(
            session, ticket, message.from_user.id, body, is_admin=False
        )
        await session.commit()
        ticket_id = ticket.id

    await state.clear()

    await message.answer(
        f"✅ <b>Ticket Created!</b>\n\n"
        f"🆔 Ticket ID: <code>#{ticket_id}</code>\n"
        f"📋 Subject: {subject}\n\n"
        "Our team will respond shortly.",
        parse_mode="HTML",
    )

    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"🎫 <b>New Ticket #{ticket_id}</b>\n"
                f"👤 User: {message.from_user.id}\n"
                f"📋 {subject}\n\n{body}",
                parse_mode="HTML",
            )
        except Exception:
            pass


@router.callback_query(F.data == "ticket_list")
async def ticket_list(callback: CallbackQuery):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return
        tickets = await TicketRepo.get_user_tickets(session, user.id)

    if not tickets:
        await callback.message.edit_text(
            "📋 No tickets found.",
            reply_markup=back_button("support"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "📋 <b>Your Tickets</b>",
        reply_markup=tickets_keyboard(tickets),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^ticket_\d+$"))
async def ticket_detail(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)

    if not ticket:
        await callback.answer("Ticket not found", show_alert=True)
        return

    messages_text = ""
    for msg in ticket.messages[-10:]:
        prefix = "👨‍💼 Admin" if msg.is_admin else "👤 You"
        messages_text += f"\n{prefix}: {msg.message}\n"

    is_open = ticket.status == TicketStatus.OPEN
    text = (
        f"🎫 <b>Ticket #{ticket.id}</b>\n"
        f"📋 {ticket.subject}\n"
        f"Status: {'🟢 Open' if is_open else '🔴 Closed'}\n"
        f"{messages_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=ticket_detail_keyboard(ticket_id, is_open),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ticket_reply_"))
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[2])
    await state.set_state(SupportStates.waiting_reply)
    await state.update_data(reply_ticket_id=ticket_id)
    await callback.message.edit_text(
        "💬 Type your reply:",
        reply_markup=back_button(f"ticket_{ticket_id}"),
    )
    await callback.answer()


@router.message(SupportStates.waiting_reply)
async def ticket_reply_message(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")

    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)
        if not ticket:
            await message.answer("Ticket not found")
            await state.clear()
            return

        await TicketRepo.add_message(
            session, ticket, message.from_user.id, message.text.strip(), is_admin=False
        )
        await session.commit()

    await state.clear()
    await message.answer("✅ Reply sent!")

    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                f"💬 Reply on Ticket #{ticket_id}\nFrom: {message.from_user.id}\n\n{message.text}",
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("ticket_close_"))
async def ticket_close(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)
        if ticket:
            await TicketRepo.close(session, ticket)
            await session.commit()

    await callback.answer("Ticket closed", show_alert=True)
    await ticket_list(callback)
