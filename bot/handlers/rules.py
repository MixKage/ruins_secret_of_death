from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.handlers.helpers import is_admin_user
from bot.keyboards import main_menu_kb
from bot.utils.telegram import edit_or_send
from bot.texts import RULES_TEXT

router = Router()


@router.callback_query(F.data == "menu:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await edit_or_send(callback, RULES_TEXT, reply_markup=main_menu_kb(is_admin=is_admin))


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    is_admin = is_admin_user(message.from_user)
    await message.answer(RULES_TEXT, reply_markup=main_menu_kb(is_admin=is_admin))
