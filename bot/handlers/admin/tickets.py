from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.repository import TicketRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back, admin_ticket_actions, admin_tickets_keyboard
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.callback_query(F.data == "adm_tickets")
async def admin_tickets(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        tickets = await TicketRepo.get_open_tickets(session)

    if not tickets:
        await callback.message.edit_text(
            "🎫 No open tickets.",
            reply_markup=admin_back(),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🎫 <b>Open Tickets</b>",
        reply_markup=admin_tickets_keyboard(tickets),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_ticket_"))
async def admin_ticket_detail(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    ticket_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)

    if not ticket:
        await callback.answer("Not found", show_alert=True)
        return

    msgs = "\n".join(
        f"{'Admin' if m.is_admin else 'User'}: {m.message}" for m in ticket.messages[-10:]
    )
    text = (
        f"🎫 <b>Ticket #{ticket.id}</b>\n"
        f"👤 {ticket.user.telegram_id}\n"
        f"📋 {ticket.subject}\n\n{msgs}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_ticket_actions(ticket_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_treply_"))
async def admin_ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.ticket_reply)
    await state.update_data(admin_ticket_id=ticket_id)
    await callback.message.edit_text("Type your reply:")
    await callback.answer()


@router.message(AdminStates.ticket_reply)
async def admin_ticket_reply(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    ticket_id = data.get("admin_ticket_id")

    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)
        if not ticket:
            await message.answer("Ticket not found")
            await state.clear()
            return

        await TicketRepo.add_message(
            session, ticket, message.from_user.id, message.text.strip(), is_admin=True
        )
        await session.commit()
        user_id = ticket.user.telegram_id

    await state.clear()
    await message.answer("✅ Reply sent.")

    try:
        await bot.send_message(
            user_id,
            f"💬 <b>Support Reply — Ticket #{ticket_id}</b>\n\n{message.text}",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm_tclose_"))
async def admin_ticket_close(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        ticket = await TicketRepo.get_by_id(session, ticket_id)
        if ticket:
            await TicketRepo.close(session, ticket)
            await session.commit()

    await callback.answer("Ticket closed", show_alert=True)
    await admin_tickets(callback)
