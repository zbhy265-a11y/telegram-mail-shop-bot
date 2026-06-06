from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.repository import ProductRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.callback_query(F.data == "adm_stock")
async def admin_stock_overview(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        products = await ProductRepo.get_all(session)
        lines = []
        for p in products:
            count = await ProductRepo.get_stock_count(session, p.id)
            lines.append(f"📦 {p.name}: <b>{count}</b> in stock")

    text = "📋 <b>Stock Overview</b>\n\n" + ("\n".join(lines) if lines else "No products.")
    await callback.message.edit_text(
        text, reply_markup=admin_back(), parse_mode="HTML"
    )
    await callback.answer()
