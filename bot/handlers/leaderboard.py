from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from html import escape

from bot import db
from bot.keyboards import main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()


def _format_leaderboard(rows):
    if not rows:
        return "<i>Рейтинг пуст.</i>"
    lines = ["<b>Рейтинг (топ-10):</b>"]
    for idx, (username, max_floor) in enumerate(rows, start=1):
        name = escape(username) if username else "Без имени"
        lines.append(f"{idx}. {name} — этаж <b>{max_floor}</b>")
    return "\n".join(lines)


@router.callback_query(F.data == "menu:leaderboard")
async def leaderboard_callback(callback: CallbackQuery) -> None:
    rows = await db.get_leaderboard()
    text = _format_leaderboard(rows)
    has_active = False
    user = callback.from_user
    if user:
        user_row = await db.get_user_by_telegram(user.id)
        if user_row:
            has_active = bool(await db.get_active_run(user_row[0]))
    await callback.answer()
    await edit_or_send(callback, text, reply_markup=main_menu_kb(has_active_run=has_active))


@router.message(Command("leaderboard"))
async def leaderboard_command(message: Message) -> None:
    rows = await db.get_leaderboard()
    text = _format_leaderboard(rows)
    await message.answer(text, reply_markup=main_menu_kb())
