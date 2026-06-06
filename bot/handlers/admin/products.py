from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.models import Category, Product
from bot.database.repository import CategoryRepo, ProductRepo, StockRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back, admin_product_actions, admin_products_keyboard
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.message(Command("addproduct"))
async def cmd_addproduct(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.add_product_name)
    await message.answer("Enter product name:")


@router.message(Command("addstock"))
async def cmd_addstock(message: Message, state: FSMContext):
    if not await _is_admin(message.from_user.id):
        return
    await state.set_state(AdminStates.add_stock_product)
    async with async_session() as session:
        products = await ProductRepo.get_all(session)
    if not products:
        await message.answer("No products. Create one first with /addproduct")
        return
    lines = "\n".join(f"{p.id}. {p.name}" for p in products)
    await message.answer(f"Reply with product ID:\n{lines}")


@router.message(AdminStates.add_stock_product)
async def add_stock_select_product(message: Message, state: FSMContext):
    try:
        product_id = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid product ID")
        return
    await state.set_state(AdminStates.add_stock_data)
    await state.update_data(stock_product_id=product_id)
    await message.answer(
        "Send stock lines (email|password) one per line, or upload a .txt file:"
    )


@router.callback_query(F.data == "adm_products")
async def admin_products(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        await callback.answer("Access denied", show_alert=True)
        return

    async with async_session() as session:
        products = await ProductRepo.get_all(session)

    await callback.message.edit_text(
        "📦 <b>Product Management</b>",
        reply_markup=admin_products_keyboard(products),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_prod_"))
async def admin_product_detail(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    product_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        product = await ProductRepo.get_by_id(session, product_id)
        stock = await ProductRepo.get_stock_count(session, product_id)

    if not product:
        await callback.answer("Not found", show_alert=True)
        return

    text = (
        f"📦 <b>{product.name}</b>\n"
        f"💵 ${product.price:.2f} | 📊 Stock: {stock}\n"
        f"📝 {product.description[:200]}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=admin_product_actions(product_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.add_product_name)
    await callback.message.edit_text(
        "Enter product name:",
        reply_markup=admin_back("adm_products"),
    )
    await callback.answer()


@router.message(AdminStates.add_product_name)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(product_name=message.text.strip())
    await state.set_state(AdminStates.add_product_price)
    await message.answer("Enter price (e.g. 2.50):")


@router.message(AdminStates.add_product_price)
async def add_product_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip())
    except ValueError:
        await message.answer("Invalid price.")
        return

    await state.update_data(product_price=price)

    async with async_session() as session:
        categories = await CategoryRepo.get_all_active(session)

    if not categories:
        await message.answer("No categories. Seed data missing.")
        await state.clear()
        return

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(text=c.name, callback_data=f"adm_newprod_cat_{c.id}")]
        for c in categories
    ]
    await state.set_state(AdminStates.add_product_category)
    await message.answer(
        "Select category:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("adm_newprod_cat_"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    category_id = int(callback.data.split("_")[3])
    data = await state.get_data()

    async with async_session() as session:
        product = Product(
            category_id=category_id,
            name=data["product_name"],
            price=data["product_price"],
            description="Premium email account",
        )
        session.add(product)
        await session.commit()

    await state.clear()
    await callback.message.edit_text(f"✅ Product '{data['product_name']}' created!")
    await callback.answer()


@router.callback_query(F.data.startswith("adm_del_prod_"))
async def delete_product(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    product_id = int(callback.data.split("_")[3])
    async with async_session() as session:
        product = await ProductRepo.get_by_id(session, product_id)
        if product:
            product.is_active = False
            await session.commit()

    await callback.answer("Product deactivated", show_alert=True)
    await admin_products(callback)


@router.callback_query(F.data.startswith("adm_addstock_"))
async def add_stock_start(callback: CallbackQuery, state: FSMContext):
    if not await _is_admin(callback.from_user.id):
        return

    product_id = int(callback.data.split("_")[2])
    await state.set_state(AdminStates.add_stock_data)
    await state.update_data(stock_product_id=product_id)
    await callback.message.edit_text(
        "📥 Send stock lines (one per line):\n<code>email@example.com|password</code>\n\n"
        "Or send a .txt file with stock data.",
        reply_markup=admin_back(f"adm_prod_{product_id}"),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.add_stock_data)
async def add_stock_data(message: Message, state: FSMContext):
    data = await state.get_data()
    product_id = data.get("stock_product_id")

    lines = []
    if message.document:
        file = await message.bot.download(message.document)
        content = file.read().decode("utf-8", errors="ignore")
        lines = content.strip().split("\n")
    elif message.text:
        lines = message.text.strip().split("\n")

    if not lines:
        await message.answer("No stock data provided.")
        return

    async with async_session() as session:
        count = await StockRepo.add_bulk(session, product_id, lines)
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Added {count} stock items.")


@router.callback_query(F.data.startswith("adm_stockcount_"))
async def stock_count(callback: CallbackQuery):
    product_id = int(callback.data.split("_")[2])
    async with async_session() as session:
        count = await ProductRepo.get_stock_count(session, product_id)

    await callback.answer(f"Stock: {count} items", show_alert=True)
