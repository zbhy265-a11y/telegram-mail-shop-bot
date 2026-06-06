from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database.repository import CategoryRepo, ProductRepo
from bot.database.session import async_session
from bot.keyboards.user import (
    back_button,
    categories_keyboard,
    product_detail_keyboard,
    products_keyboard,
)
from bot.services.delivery import DeliveryService
from bot.utils.states import BulkBuyStates

router = Router()


@router.callback_query(F.data == "shop")
async def show_shop(callback: CallbackQuery):
    async with async_session() as session:
        categories = await CategoryRepo.get_all_active(session)

    if not categories:
        await callback.message.edit_text(
            "🛒 <b>Shop</b>\n\nNo categories available yet.",
            reply_markup=back_button(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "🛒 <b>Shop</b>\n\nSelect a category:",
        reply_markup=categories_keyboard(categories),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    category_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        category = await CategoryRepo.get_by_id(session, category_id)
        products = await ProductRepo.get_by_category(session, category_id)

    if not category:
        await callback.answer("Category not found", show_alert=True)
        return

    if not products:
        await callback.message.edit_text(
            f"{category.emoji} <b>{category.name}</b>\n\nNo products available.",
            reply_markup=back_button("shop"),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"{category.emoji} <b>{category.name}</b>\n\nSelect a product:",
        reply_markup=products_keyboard(products, category_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    async with async_session() as session:
        product = await ProductRepo.get_by_id(session, product_id)
        stock = await ProductRepo.get_stock_count(session, product_id)

    if not product:
        await callback.answer("Product not found", show_alert=True)
        return

    text = (
        f"📦 <b>{product.name}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💵 Price: <b>{config.currency}{product.price:.2f}</b>\n"
        f"📊 Stock: <b>{stock}</b> available\n"
        f"🚀 Delivery: <b>{product.delivery_type.title()}</b>\n\n"
        f"📝 <b>Description:</b>\n{product.description or 'Premium quality email account.'}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_detail_keyboard(product_id, product.category_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^buy_1_\d+$"))
async def buy_single(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    coupon = (await state.get_data()).get("active_coupon")
    await _process_purchase(callback, product_id, 1, coupon)
    await state.update_data(active_coupon=None)


@router.callback_query(F.data.startswith("buy_bulk_"))
async def buy_bulk_start(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[2])
    await state.set_state(BulkBuyStates.waiting_quantity)
    await state.update_data(bulk_product_id=product_id)
    await callback.message.edit_text(
        "📦 <b>Bulk Purchase</b>\n\nEnter the quantity you want to buy:",
        reply_markup=back_button(f"prod_{product_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(BulkBuyStates.waiting_quantity)
async def buy_bulk_quantity(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data.get("bulk_product_id")

    try:
        quantity = int(message.text.strip())
        if quantity < 1 or quantity > 100:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Enter a valid number between 1 and 100.")
        return

    await state.clear()
    coupon = data.get("active_coupon")

    async with async_session() as session:
        from bot.database.repository import ProductRepo, UserRepo

        user = await UserRepo.get_by_telegram_id(session, message.from_user.id)
        product = await ProductRepo.get_by_id(session, product_id)
        if not user or not product:
            await message.answer("❌ Error. Please try again.")
            return

        success, result, order_id = await DeliveryService.purchase(
            session, user, product, quantity, coupon
        )
        await session.commit()

    if not success:
        await message.answer(result, parse_mode="HTML")
        return

    text = (
        f"✅ <b>Order Confirmed!</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>\n"
        f"📦 Product: {product.name}\n"
        f"🔢 Quantity: {quantity}\n\n"
        f"📧 <b>Your Accounts:</b>\n<code>{result}</code>"
    )
    await message.answer(text, parse_mode="HTML")


async def _process_purchase(
    callback: CallbackQuery, product_id: int, quantity: int, coupon: str | None
):
    async with async_session() as session:
        from bot.database.repository import ProductRepo, UserRepo

        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        product = await ProductRepo.get_by_id(session, product_id)
        if not user or not product:
            await callback.answer("Error. Please /start", show_alert=True)
            return

        success, result, order_id = await DeliveryService.purchase(
            session, user, product, quantity, coupon
        )
        await session.commit()

    if not success:
        await callback.message.edit_text(result, parse_mode="HTML")
        await callback.answer()
        return

    text = (
        f"✅ <b>Order Confirmed!</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>\n"
        f"📦 Product: {product.name}\n"
        f"🔢 Quantity: {quantity}\n\n"
        f"📧 <b>Your Account:</b>\n<code>{result}</code>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer("✅ Purchase successful!")
