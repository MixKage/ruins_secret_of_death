from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import main_menu_kb
from bot.texts import RULES_TEXT

router = Router()


@router.callback_query(F.data == "menu:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(RULES_TEXT, reply_markup=main_menu_kb())
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc):
                raise
    else:
        await callback.bot.send_message(callback.from_user.id, RULES_TEXT, reply_markup=main_menu_kb())


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    await message.answer(RULES_TEXT, reply_markup=main_menu_kb())
