from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.api_client import get_stats as api_get_stats
from bot.handlers.helpers import is_admin_user
from bot.keyboards import main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()


@router.callback_query(F.data == "menu:stats")
async def stats_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    response = await api_get_stats(user.id)
    text = response.get("text", "<i>Статистика пока пустая.</i>")
    has_active = bool(response.get("has_active_run"))
    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await edit_or_send(callback, text, reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin))
