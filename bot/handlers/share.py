from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.api_client import get_share as api_get_share

router = Router()


@router.callback_query(F.data == "menu:share")
async def share_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    response = await api_get_share(user.id)
    status = response.get("status")
    if status == "needs_start":
        await callback.answer(response.get("alert") or "Сначала нажмите /start", show_alert=True)
        return
    if status == "active_run":
        await callback.answer(response.get("alert") or "Завершите активный забег, чтобы поделиться.", show_alert=True)
        return
    if status == "no_runs":
        await callback.answer()
        await callback.bot.send_message(user.id, "Пока нет завершенных забегов.")
        return
    text = response.get("text")
    if not text:
        await callback.answer("Не удалось подготовить сообщение.", show_alert=True)
        return
    await callback.answer()
    await callback.bot.send_message(user.id, text)
