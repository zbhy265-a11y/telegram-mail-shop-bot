from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from bot.config import config
from bot.database.repository import UserRepo
from bot.database.session import async_session
from bot.keyboards.user import main_menu

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: Message, command: CommandStart):
    referrer = None
    if command.args and command.args.startswith("ref_"):
        referrer = command.args[4:]
    await _register_and_welcome(message, referrer)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await _register_and_welcome(message)


async def _register_and_welcome(message: Message, referrer_code: str | None = None):
    async with async_session() as session:
        user, is_new = await UserRepo.get_or_create(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referrer_code=referrer_code,
        )
        await session.commit()
        balance = user.balance

    welcome = (
        "✨ <b>Welcome to Premium Mail Shop</b> ✨\n\n"
        "Your trusted marketplace for premium email accounts.\n"
        "Instant delivery • Secure payments • 24/7 support\n\n"
    )
    if is_new:
        welcome += "🎉 <b>Account created successfully!</b>\n\n"

    welcome += (
        f"💰 Balance: <b>{config.currency}{balance:.2f}</b>\n\n"
        "Select an option below to get started:"
    )

    await message.answer(welcome, reply_markup=main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    async with async_session() as session:
        user = await UserRepo.get_by_telegram_id(session, callback.from_user.id)
        balance = user.balance if user else 0.0

    text = (
        "🏠 <b>Main Menu</b>\n\n"
        f"💰 Balance: <b>{config.currency}{balance:.2f}</b>\n\n"
        "Select an option:"
    )
    await callback.message.edit_text(
        text, reply_markup=main_menu(), parse_mode="HTML"
    )
    await callback.answer()
