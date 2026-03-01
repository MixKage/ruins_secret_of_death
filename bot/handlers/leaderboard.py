from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.api_client import get_leaderboard as api_get_leaderboard
from bot.api_client import get_active_run as api_get_active_run
from bot.handlers.helpers import is_admin_user
from bot.keyboards import leaderboard_kb, main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()


async def _show_leaderboard(callback: CallbackQuery, page: int) -> None:
    response = await api_get_leaderboard(page)
    total_pages = int(response.get("total_pages", 1))
    page = int(response.get("page", page))
    text = response.get("text", "<i>Рейтинг пуст.</i>")

    if page < 1:
        await callback.answer("Это первая страница.")
    elif page > total_pages:
        await callback.answer("Это последняя страница.")
    else:
        await callback.answer()

    await edit_or_send(callback, text, reply_markup=leaderboard_kb(page))


@router.callback_query(F.data == "menu:leaderboard")
async def leaderboard_callback(callback: CallbackQuery) -> None:
    await _show_leaderboard(callback, page=1)


@router.callback_query(F.data.startswith("menu:leaderboard:page:"))
async def leaderboard_page_callback(callback: CallbackQuery) -> None:
    try:
        page = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        page = 1
    await _show_leaderboard(callback, page=page)


@router.callback_query(F.data == "menu:main")
async def leaderboard_menu_callback(callback: CallbackQuery) -> None:
    has_active = False
    user = callback.from_user
    if user:
        active = await api_get_active_run(user.id)
        has_active = bool(active.get("run_id"))
    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await edit_or_send(callback, "Главное меню", reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin))


@router.message(Command("leaderboard"))
async def leaderboard_command(message: Message) -> None:
    response = await api_get_leaderboard(1)
    text = response.get("text", "<i>Рейтинг пуст.</i>")
    is_admin = is_admin_user(message.from_user)
    await message.answer(text, reply_markup=main_menu_kb(is_admin=is_admin))
