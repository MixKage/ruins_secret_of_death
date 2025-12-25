from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import db
from bot.keyboards import leaderboard_kb, main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()


PAGE_SIZE = 10


def _format_leaderboard(rows, page: int, total_pages: int) -> str:
    if not rows:
        return "<i>Рейтинг пуст.</i>"
    lines = [f"<b>Рейтинг:</b> страница {page}/{total_pages}"]
    start_rank = (page - 1) * PAGE_SIZE + 1
    for idx, (username, max_floor) in enumerate(rows, start=start_rank):
        name = escape(username) if username else "Без имени"
        lines.append(f"{idx}. {name} — этаж <b>{max_floor}</b>")
    return "\n".join(lines)


async def _show_leaderboard(callback: CallbackQuery, page: int) -> None:
    requested_page = page
    page = max(1, page)
    total = await db.get_leaderboard_total()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > total_pages:
        page = total_pages

    rows = await db.get_leaderboard_page(PAGE_SIZE, (page - 1) * PAGE_SIZE)
    text = _format_leaderboard(rows, page, total_pages)

    if requested_page < 1:
        await callback.answer("Это первая страница.")
    elif requested_page > total_pages:
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
        user_row = await db.get_user_by_telegram(user.id)
        if user_row:
            has_active = bool(await db.get_active_run(user_row[0]))
    await callback.answer()
    await edit_or_send(callback, "Главное меню", reply_markup=main_menu_kb(has_active_run=has_active))


@router.message(Command("leaderboard"))
async def leaderboard_command(message: Message) -> None:
    total = await db.get_leaderboard_total()
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    rows = await db.get_leaderboard_page(PAGE_SIZE, 0)
    text = _format_leaderboard(rows, 1, total_pages)
    await message.answer(text, reply_markup=main_menu_kb())
