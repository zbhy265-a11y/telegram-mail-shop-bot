from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.repository import UserRepo
from bot.database.session import async_session
from bot.keyboards.admin import admin_back, admin_balance_keyboard, admin_ban_keyboard
from bot.utils.states import AdminStates

router = Router()


async def _is_admin(telegram_id: int) -> bool:
    from bot.database.repository import AdminRepo

    async with async_session() as session:
        return await AdminRepo.is_admin(session, telegram_id)


@router.message(Command("users"))
async def cmd_users(message: Message):
    if not await _is_admin(message.from_user.id):
        return

    async with async_session() as session:
        count = await UserRepo.count_all(session)

    await message.answer(f"👥 Total users: <b>{count}</b>", parse_mode="HTML")


@router.callback_query(F.data == "adm_users")
async def admin_users(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    async with async_session() as session:
        count = await UserRepo.count_all(session)

    await callback.message.edit_text(
        f"👥 <b>Users</b>\n\nTotal registered: <b>{count}</b>\n\n"
        "Use commands:\n"
        "/addbalance <user_id> <amount>\n"
        "/removebalance <user_id> <amount>\n"
        "/ban <user_id>\n"
        "/unban <user_id>",
        reply_markup=admin_back(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_balance")
async def admin_balance_menu(callback: CallbackQuery):
    if not await _is_admin(callback.from_user.id):
        return

    await callback.message.edit_text(
        "💰 <b>Balance Management</b>",
        reply_markup=admin_balance_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_add_bal")
async def add_balance_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.add_balance_user)
    await callback.message.edit_text("Enter user Telegram ID:")
    await callback.answer()


@router.message(AdminStates.add_balance_user)
async def add_balance_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID")
        return
    await state.update_data(balance_user_id=uid)
    await state.set_state(AdminStates.add_balance_amount)
    await message.answer("Enter amount to add:")


@router.message(AdminStates.add_balance_amount)
async def add_balance_amount(message: Message, state: FSMContext, bot):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("Invalid amount")
        return

    data = await state.get_data()
    uid = data["balance_user_id"]

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if not user:
            await message.answer("User not found")
            await state.clear()
            return
        await UserRepo.add_balance(session, user, amount, "Admin credit")
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Added ${amount:.2f} to user {uid}")

    try:
        await bot.send_message(uid, f"💰 ${amount:.2f} has been added to your balance!")
    except Exception:
        pass


@router.callback_query(F.data == "adm_rem_bal")
async def remove_balance_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.remove_balance_user)
    await callback.message.edit_text("Enter user Telegram ID:")
    await callback.answer()


@router.message(AdminStates.remove_balance_user)
async def remove_balance_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID")
        return
    await state.update_data(balance_user_id=uid)
    await state.set_state(AdminStates.remove_balance_amount)
    await message.answer("Enter amount to remove:")


@router.message(AdminStates.remove_balance_amount)
async def remove_balance_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
    except ValueError:
        await message.answer("Invalid amount")
        return

    data = await state.get_data()
    uid = data["balance_user_id"]

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if not user:
            await message.answer("User not found")
            await state.clear()
            return
        ok = await UserRepo.deduct_balance(session, user, amount, "Admin deduction")
        if not ok:
            await message.answer("Insufficient balance")
            await state.clear()
            return
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Removed ${amount:.2f} from user {uid}")


@router.callback_query(F.data == "adm_ban")
async def admin_ban_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🚫 <b>Ban Management</b>",
        reply_markup=admin_ban_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm_ban_user")
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.ban_user)
    await callback.message.edit_text("Enter user Telegram ID to ban:")
    await callback.answer()


@router.message(AdminStates.ban_user)
async def ban_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID")
        return

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if user:
            user.is_banned = True
            await session.commit()

    await state.clear()
    await message.answer(f"🚫 User {uid} banned.")


@router.callback_query(F.data == "adm_unban_user")
async def unban_user_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.unban_user)
    await callback.message.edit_text("Enter user Telegram ID to unban:")
    await callback.answer()


@router.message(AdminStates.unban_user)
async def unban_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("Invalid ID")
        return

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if user:
            user.is_banned = False
            await session.commit()

    await state.clear()
    await message.answer(f"✅ User {uid} unbanned.")


@router.message(Command("addbalance"))
async def cmd_addbalance(message: Message):
    if not await _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /addbalance <user_id> <amount>")
        return
    try:
        uid, amount = int(parts[1]), float(parts[2])
    except ValueError:
        await message.answer("Invalid arguments")
        return

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if not user:
            await message.answer("User not found")
            return
        await UserRepo.add_balance(session, user, amount, "Admin command")
        await session.commit()

    await message.answer(f"✅ Added ${amount:.2f} to {uid}")


@router.message(Command("removebalance"))
async def cmd_removebalance(message: Message):
    if not await _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Usage: /removebalance <user_id> <amount>")
        return
    try:
        uid, amount = int(parts[1]), float(parts[2])
    except ValueError:
        await message.answer("Invalid arguments")
        return

    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if not user:
            await message.answer("User not found")
            return
        ok = await UserRepo.deduct_balance(session, user, amount, "Admin command")
        if not ok:
            await message.answer("Insufficient balance")
            return
        await session.commit()

    await message.answer(f"✅ Removed ${amount:.2f} from {uid}")


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not await _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /ban <user_id>")
        return
    uid = int(parts[1])
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if user:
            user.is_banned = True
            await session.commit()
    await message.answer(f"🚫 Banned {uid}")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not await _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Usage: /unban <user_id>")
        return
    uid = int(parts[1])
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, uid)
        if user:
            user.is_banned = False
            await session.commit()
    await message.answer(f"✅ Unbanned {uid}")
