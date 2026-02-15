from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.api_client import get_profile as api_get_profile
from bot.keyboards import profile_kb
from bot.utils.telegram import edit_or_send

router = Router()


@router.callback_query(F.data == "menu:profile")
async def profile_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    response = await api_get_profile(user.id)
    lines = response.get("text", "<i>Профиль недоступен.</i>")
    can_unlock = bool(response.get("can_unlock"))
    await callback.answer()
    await edit_or_send(callback, lines, reply_markup=profile_kb(can_unlock=can_unlock))
