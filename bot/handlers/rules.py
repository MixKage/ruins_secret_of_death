from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_kb
from bot.utils.telegram import edit_or_send
from bot.texts import RULES_TEXT

router = Router()


@router.callback_query(F.data == "menu:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, RULES_TEXT, reply_markup=main_menu_kb())


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    await message.answer(RULES_TEXT, reply_markup=main_menu_kb())
