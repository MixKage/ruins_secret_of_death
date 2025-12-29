from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.handlers.broadcast import BROADCAST_KEY
from bot.handlers.helpers import is_admin_user
from bot.keyboards import admin_kb
from bot.progress import award_current_season_badges, award_latest_closed_season_badges, season_label
from bot.utils.telegram import edit_or_send

router = Router()


def _format_admin_panel(stats: dict) -> str:
    avg_death_floor = stats.get("avg_death_floor", 0.0)
    avg_text = f"{avg_death_floor:.1f}" if avg_death_floor else "—"
    runs_24h = stats.get("runs_24h", 0)
    users_24h = stats.get("users_24h", 0)
    top_killers = stats.get("top_killers", [])

    lines = [
        "<b>Админ панель</b>",
        f"<b>Игроков:</b> {stats.get('total_users', 0)}",
        f"<b>Активных забегов:</b> {stats.get('active_runs', 0)}",
        f"<b>Всего забегов:</b> {stats.get('total_runs', 0)}",
        f"<b>Смертей:</b> {stats.get('total_deaths', 0)}",
        f"<b>Ср. этаж смерти:</b> {avg_text}",
        f"<b>Активность 24ч:</b> {runs_24h} забегов | {users_24h} игроков",
        f"<b>Сундуков открыто:</b> {stats.get('total_chests', 0)}",
        f"<b>Сокровищ найдено:</b> {stats.get('total_treasures', 0)}",
        f"<b>Макс. этаж (глобально):</b> {stats.get('max_floor', 0)}",
    ]

    if top_killers:
        lines.append("")
        lines.append("<b>Топ-3 убийцы:</b>")
        for idx, (username, kills) in enumerate(top_killers, start=1):
            name = escape(username) if username else "Без имени"
            lines.append(f"{idx}. {name} — {kills}")

    lines.append("")
    lines.append(
        f"<b>Рассылка «Баланс»:</b> отправлено {stats.get('broadcast_sent', 0)} | "
        f"осталось {stats.get('broadcast_pending', 0)}"
    )

    return "\n".join(lines)


async def _show_admin_panel(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    stats = await db.get_admin_stats(BROADCAST_KEY)
    if not stats:
        await edit_or_send(callback, "Админ панель недоступна.", reply_markup=admin_kb())
        return
    text = _format_admin_panel(stats)
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin")
async def admin_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:refresh")
async def admin_refresh(callback: CallbackQuery) -> None:
    await callback.answer("Обновляю...")
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:season_badges")
async def admin_season_badges(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    season_key = await award_latest_closed_season_badges()
    if season_key:
        await callback.answer(f"Пересчитано: {season_label(season_key)}")
    else:
        season_key = await award_current_season_badges()
        await callback.answer(f"Пересчитано: {season_label(season_key)} (текущий)")
    await _show_admin_panel(callback)
