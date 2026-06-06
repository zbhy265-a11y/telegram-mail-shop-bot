from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import config
from bot.database.repository import AdminRepo, StatsRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_menu
from bot.services.backup import export_database
from bot.services.broadcast import broadcast_message
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await _is_admin(message.from_user.id):
        await message.answer("⛔ Access denied.")
        return

    await message.answer(
        "🔐 <b>Admin Panel</b>\n\nSelect an action:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        "🔐 <b>Admin Panel</b>\n\nSelect an action:",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_close")
async def admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "adm_stats")
async def admin_stats(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    async with async_session() as session:
        stats = await StatsRepo.get_dashboard(session)

    from bot.keyboards.admin import admin_back

    text = (
        "📊 <b>Dashboard Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Users: <b>{stats['users']}</b>\n"
        f"📦 Orders: <b>{stats['orders']}</b>\n"
        f"💰 Revenue: <b>${stats['revenue']:.2f}</b>\n"
        f"💳 Pending Payments: <b>{stats['pending_payments']}</b>\n"
        f"🎫 Open Tickets: <b>{stats['open_tickets']}</b>\n"
    )

    await callback.message.edit_text(
        text, reply_markup=admin_back(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    if not await _is_admin(message.from_user.id):
        return

    from bot.database.repository import OrderRepo

    async with async_session() as session:
        from sqlalchemy import select
        from bot.database.models import Order

        result = await session.execute(
            select(Order).order_by(Order.created_at.desc()).limit(10)
        )
        orders = list(result.scalars().all())

    if not orders:
        await message.answer("No orders yet.")
        return

    lines = [
        f"#{o.order_id} — ${o.total_price:.2f} — {o.status.value}"
        for o in orders
    ]
    await message.answer("📦 <b>Recent Orders</b>\n\n" + "\n".join(lines), parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if not await _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        stats = await StatsRepo.get_dashboard(session)

    await message.answer(
        f"📊 Users: {stats['users']} | Orders: {stats['orders']} | "
        f"Revenue: ${stats['revenue']:.2f} | Pending: {stats['pending_payments']}",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_export")
async def admin_export(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    await callback.answer("Generating export...")
    data = await export_database()
    file = BufferedInputFile(data.encode(), filename="database_export.json")
    await callback.message.answer_document(
        file, caption="📥 Database export"
    )


@router.callback_query(F.data == "adm_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    from bot.keyboards.admin import admin_back

    await state.set_state(AdminStates.broadcast_message)
    await callback.message.edit_text(
        "📢 Send the broadcast message (HTML supported):",
        reply_markup=admin_back(),
    )
    await callback.answer()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return

    await state.set_state(AdminStates.broadcast_message)
    await message.answer("📢 Send the broadcast message:")


@router.message(AdminStates.broadcast_message)
async def process_broadcast(message: Message, state: FSMContext, bot):
    text = message.text or message.caption or ""
    await state.clear()
    await message.answer("📢 Broadcasting... This may take a while.")
    sent, failed = await broadcast_message(bot, text, message.from_user.id)
    await message.answer(f"✅ Done! Sent: {sent}, Failed: {failed}")
