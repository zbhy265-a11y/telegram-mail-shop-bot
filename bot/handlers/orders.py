from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database.repository import OrderRepo
from bot.database.session import async_session
from bot.keyboards.user import back_button, orders_keyboard
from bot.utils.helpers import format_datetime

router = Router()

PAGE_SIZE = 10


@router.callback_query(F.data == "orders")
async def show_orders(callback: CallbackQuery):
    await _show_orders_page(callback, 0)


@router.callback_query(F.data.startswith("orders_page_"))
async def orders_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[2])
    await _show_orders_page(callback, page)


async def _show_orders_page(callback: CallbackQuery, page: int):
    async with async_session() as session:
        from bot.database.repository import UserRepo

        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.answer("Please /start first", show_alert=True)
            return

        orders = await OrderRepo.get_user_orders(
            session, user.id, limit=PAGE_SIZE + 1, offset=page * PAGE_SIZE
        )

    has_more = len(orders) > PAGE_SIZE
    orders = orders[:PAGE_SIZE]

    if not orders:
        await callback.message.edit_text(
            "📦 <b>Orders</b>\n\nYou have no orders yet.",
            reply_markup=back_button(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"📦 <b>Your Orders</b> (Page {page + 1})\n\nSelect an order to view details:",
        reply_markup=orders_keyboard(orders, page, has_more),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_"))
async def show_order_detail(callback: CallbackQuery):
    order_id = callback.data.replace("order_", "")
    async with async_session() as session:
        order = await OrderRepo.get_by_order_id(session, order_id)

    if not order:
        await callback.answer("Order not found", show_alert=True)
        return

    product_name = order.product.name if order.product else "Unknown"
    text = (
        f"📦 <b>Order Details</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 Order ID: <code>{order.order_id}</code>\n"
        f"📧 Product: {product_name}\n"
        f"🔢 Quantity: {order.quantity}\n"
        f"💵 Price: {config.currency}{order.total_price:.2f}\n"
        f"📅 Time: {format_datetime(order.created_at)}\n"
        f"✅ Status: {order.status.value.title()}\n\n"
        f"📧 <b>Delivery Data:</b>\n<code>{order.delivery_data}</code>"
    )

    await callback.message.edit_text(
        text, reply_markup=back_button("orders"), parse_mode="HTML"
    )
    await callback.answer()
