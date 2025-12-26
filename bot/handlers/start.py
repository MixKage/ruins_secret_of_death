from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import db
from bot.handlers.helpers import is_admin_id
from bot.keyboards import main_menu_kb
from bot.texts import WELCOME_TEXT

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    user_id = await db.ensure_user(user.id, user.username)
    active_run = await db.get_active_run(user_id)
    is_admin = is_admin_id(user.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(bool(active_run), is_admin=is_admin))
