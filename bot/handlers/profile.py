from datetime import datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.game.characters import get_character
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


def _potential_season_awards(
    user_id: int,
    rank: int | None,
    season_stats: dict,
    rows: list[dict],
) -> list[str]:
    if not rows:
        return []
    awards = []
    seen = set()

    def add_award(name: str, detail: str | None = None) -> None:
        label = f"{name} — {detail}" if detail else name
        if label in seen:
            return
        seen.add(label)
        awards.append(label)
    if rank:
        if rank == 1:
            add_award(BADGES["season_top1"].name, f"место #{rank}")
        elif rank == 2:
            add_award(BADGES["season_top2"].name, f"место #{rank}")
        elif rank == 3:
            add_award(BADGES["season_top3"].name, f"место #{rank}")
        if rank <= 10:
            add_award(BADGES["season_top10"].name, f"место #{rank}")

    user_kills = sum((season_stats.get("kills") or {}).values())
    user_chests = int(season_stats.get("chests_opened", 0))
    user_treasures = int(season_stats.get("treasures_found", 0))
    user_runs = int(season_stats.get("total_runs", 0))
    user_max_floor = int(season_stats.get("max_floor", 0))

    max_floor = max((int(row.get("max_floor", 0)) for row in rows), default=0)
    max_runs = max((int(row.get("total_runs", 0)) for row in rows), default=0)
    max_chests = max((int(row.get("chests_opened", 0)) for row in rows), default=0)
    max_treasures = max((int(row.get("treasures_found", 0)) for row in rows), default=0)
    max_kills = max((sum((row.get("kills") or {}).values()) for row in rows), default=0)

    if user_max_floor > 0 and user_max_floor == max_floor:
        add_award(BADGES["season_highest_floor"].name, f"этаж {user_max_floor}")
    if user_runs > 0 and user_runs == max_runs:
        add_award(BADGES["season_most_runs"].name, f"{user_runs} забегов")
    if user_chests > 0 and user_chests == max_chests:
        add_award(BADGES["season_most_chests"].name, f"{user_chests} сундуков")
    if user_treasures > 0 and user_treasures == max_treasures:
        add_award(BADGES["season_most_treasures"].name, f"{user_treasures} сокровищ")
    if user_kills > 0 and user_kills == max_kills:
        add_award(BADGES["season_most_kills"].name, f"{user_kills} убийств")

    return list(dict.fromkeys(awards))


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
    season_rows = await db.get_season_stats_rows(season_id)
    last_closed = await db.get_last_season(ended_only=True)
    last_closed_key = last_closed[1] if last_closed else None

    total_kills = sum((total_stats.get("kills") or {}).values())
    season_kills = sum((season_stats.get("kills") or {}).values())
    hero_runs = total_stats.get("hero_runs", {}) or {}

    username = profile.get("username") or "Без имени"
    created_at = _format_date(profile.get("created_at"))
    xp = int(profile.get("xp", 0))
    level, xp_current, xp_needed = xp_to_level(xp)
    bar = progress_bar(xp_current, xp_needed)

    seasonal_current, seasonal_history, permanent = _format_badges(
        badges,
        last_closed_key or "__none__",
    )
    potential_awards = _potential_season_awards(user_id, rank, season_stats, season_rows)

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
    if hero_runs:
        lines.append("")
        lines.append("<b>Забеги по героям:</b>")
        sorted_runs = sorted(hero_runs.items(), key=lambda item: (-int(item[1]), item[0]))
        for hero_id, count in sorted_runs:
            hero_name = get_character(hero_id).get("name", hero_id)
            lines.append(f"- {hero_name}: {count}")

    lines.append("")
    lines.append("<b>Претендуемые награды сезона:</b>")
    if potential_awards:
        lines.extend(f"- {name}" for name in potential_awards)
    else:
        lines.append("<i>Пока нет.</i>")

    if last_closed_key:
        lines.append("")
        lines.append("<b>Награды прошлого сезона:</b>")
        if seasonal_current:
            lines.extend(f"- {name}" for name in seasonal_current)
        else:
            lines.append("<i>Пока нет.</i>")

    lines.append("")
    lines.append("<b>История наград:</b>")
    if seasonal_history:
        lines.extend(f"- {name}" for name in seasonal_history)
    else:
        lines.append("<i>Пока нет.</i>")

    lines.append("")
    lines.append("<b>Вечные награды:</b>")
    if permanent:
        lines.extend(f"- {name}" for name in permanent)
    else:
        lines.append("<i>Пока нет.</i>")

    has_active = bool(await db.get_active_run(user_id))
    is_admin = is_admin_user(callback.from_user)
    await callback.answer()
    await edit_or_send(callback, "\n".join(lines), reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin))
