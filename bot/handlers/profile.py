from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.keyboards import main_menu_kb
from bot.progress import BADGES, ensure_current_season, progress_bar, season_label, xp_to_level
from bot.utils.telegram import edit_or_send

router = Router()


def _format_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d.%m.%Y")
    except ValueError:
        return value


def _format_badges(badges, season_key: str) -> tuple[list[str], list[str], list[str]]:
    seasonal_current = []
    seasonal_history = []
    permanent = []
    for entry in badges:
        badge = BADGES.get(entry["badge_id"])
        if not badge:
            continue
        label = badge.name
        count = entry.get("count", 0)
        if count > 1:
            label = f"{label} x{count}"
        if badge.seasonal:
            seasonal_history.append(label)
            if entry.get("last_awarded_season") == season_key:
                seasonal_current.append(badge.name)
        else:
            permanent.append(label)
    return seasonal_current, seasonal_history, permanent


@router.callback_query(F.data == "menu:profile")
async def profile_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    user_id = user_row[0]
    profile = await db.get_user_profile(user_id)
    if not profile:
        await callback.answer()
        await edit_or_send(callback, "<i>Профиль недоступен.</i>", reply_markup=main_menu_kb())
        return

    season_id, season_key = await ensure_current_season()
    season_stats = await db.get_user_season_stats(user_id, season_id)
    total_stats = await db.get_user_stats(user_id) or {}
    rank = await db.get_user_season_rank(user_id, season_id)
    badges = await db.get_user_badges(user_id)

    total_kills = sum((total_stats.get("kills") or {}).values())
    season_kills = sum((season_stats.get("kills") or {}).values())

    username = profile.get("username") or "Без имени"
    created_at = _format_date(profile.get("created_at"))
    xp = int(profile.get("xp", 0))
    level, xp_current, xp_needed = xp_to_level(xp)
    bar = progress_bar(xp_current, xp_needed)

    seasonal_current, seasonal_history, permanent = _format_badges(badges, season_key)

    lines = [
        "<b>Личный кабинет</b>",
        "<i>Руины помнят ваше имя.</i>",
        "",
        f"<b>Имя:</b> {username}",
        f"<b>В игре с:</b> {created_at}",
        f"<b>Текущий сезон:</b> {season_label(season_key)}",
        f"<b>Место в рейтинге:</b> {('#' + str(rank)) if rank else '—'}",
        "",
        f"<b>Опыт:</b> {xp_current}/{xp_needed} (ур. {level})",
        f"<b>Прогресс:</b> [{bar}]",
        "",
        "<b>Статистика сезона:</b>",
        f"- Убийства: {season_kills}",
        f"- Сундуков открыто: {season_stats.get('chests_opened', 0)}",
        f"- Сокровищ найдено: {season_stats.get('treasures_found', 0)}",
        "",
        "<b>Статистика всего:</b>",
        f"- Убийства: {total_kills}",
        f"- Сундуков открыто: {total_stats.get('chests_opened', 0)}",
        f"- Сокровищ найдено: {total_stats.get('treasures_found', 0)}",
    ]

    lines.append("")
    lines.append("<b>Значки сезона:</b>")
    if seasonal_current:
        lines.extend(f"- {name}" for name in seasonal_current)
    else:
        lines.append("<i>Пока нет.</i>")

    lines.append("")
    lines.append("<b>История сезонов:</b>")
    if seasonal_history:
        lines.extend(f"- {name}" for name in seasonal_history)
    else:
        lines.append("<i>Пока нет.</i>")

    lines.append("")
    lines.append("<b>Вечные значки:</b>")
    if permanent:
        lines.extend(f"- {name}" for name in permanent)
    else:
        lines.append("<i>Пока нет.</i>")

    has_active = bool(await db.get_active_run(user_id))
    is_admin = is_admin_user(callback.from_user)
    await callback.answer()
    await edit_or_send(callback, "\n".join(lines), reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin))
