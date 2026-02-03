import json
from datetime import date, datetime

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.game.characters import CHARACTERS, DEFAULT_CHARACTER_ID, get_character
from bot.keyboards import profile_kb
from bot.progress import BADGES, ensure_current_season, progress_bar, season_label, xp_to_level
from bot.utils.telegram import edit_or_send

router = Router()


def _format_date(value: str | datetime | date | None) -> str:
    if not value:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
            return dt.strftime("%d.%m.%Y")
        except ValueError:
            return value
    return str(value)


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


def _as_dict(value) -> dict:
    parsed = value
    for _ in range(10):
        if isinstance(parsed, (bytes, bytearray, memoryview)):
            parsed = bytes(parsed).decode("utf-8", errors="ignore")
            continue
        if isinstance(parsed, str):
            raw = parsed.strip()
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            continue
        break
    return parsed if isinstance(parsed, dict) else {}


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

    user_kills = sum(_as_dict(season_stats.get("kills")).values())
    user_chests = int(season_stats.get("chests_opened", 0))
    user_treasures = int(season_stats.get("treasures_found", 0))
    user_runs = int(season_stats.get("total_runs", 0))
    user_max_floor = int(season_stats.get("max_floor", 0))

    max_floor = max((int(row.get("max_floor", 0)) for row in rows), default=0)
    max_runs = max((int(row.get("total_runs", 0)) for row in rows), default=0)
    max_chests = max((int(row.get("chests_opened", 0)) for row in rows), default=0)
    max_treasures = max((int(row.get("treasures_found", 0)) for row in rows), default=0)
    max_kills = max((sum(_as_dict(row.get("kills")).values()) for row in rows), default=0)

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


async def build_profile_text(user_id: int, is_admin: bool) -> tuple[str, bool]:
    profile = await db.get_user_profile(user_id)
    if not profile:
        return "<i>Профиль недоступен.</i>", False

    season_id, season_key = await ensure_current_season()
    season_stats = await db.get_user_season_stats(user_id, season_id)
    total_stats = await db.get_user_stats(user_id) or {}
    rank = await db.get_user_season_rank(user_id, season_id)
    badges = await db.get_user_badges(user_id)
    season_rows = await db.get_season_stats_rows(season_id)
    star_summary = await db.get_star_purchase_summary(user_id)
    star_total = sum(entry.get("stars", 0) for entry in star_summary)
    last_closed = await db.get_last_season(ended_only=True)
    last_closed_key = last_closed[1] if last_closed else None

    total_kills = sum(_as_dict(total_stats.get("kills")).values())
    season_kills = sum(_as_dict(season_stats.get("kills")).values())
    hero_runs = _as_dict(total_stats.get("hero_runs"))
    level, xp_current, xp_needed = xp_to_level(int(profile.get("xp", 0)))
    bar = progress_bar(xp_current, xp_needed)
    if is_admin:
        unlocked_set = set(CHARACTERS.keys())
        available_unlocks = 0
        next_required_level = None
    else:
        unlocked_ids = await db.get_unlocked_heroes(user_id)
        unlocked_set = {DEFAULT_CHARACTER_ID}
        unlocked_set.update(unlocked_ids)
        unlocked_extra = max(0, len(unlocked_set) - 1)
        total_unlockable = max(0, len(CHARACTERS) - 1)
        slots = min(total_unlockable, level // 5)
        available_unlocks = max(0, slots - unlocked_extra)
        next_required_level = None
        if unlocked_extra < total_unlockable:
            next_required_level = max(5, (unlocked_extra + 1) * 5)

    seasonal_current, seasonal_history, permanent = _format_badges(
        badges,
        (last_closed_key or "__none__"),
    )
    potential_awards = _potential_season_awards(user_id, rank, season_stats, season_rows)

    lines = [
        "<b>Личный кабинет</b>",
        "<i>Руины помнят ваше имя.</i>",
        "",
        f"<b>Имя:</b> {profile.get('username') or 'Без имени'}",
        f"<b>В игре с:</b> {_format_date(profile.get('created_at'))}",
        f"<b>Текущий сезон:</b> {season_label(season_key)}",
        f"<b>Место в рейтинге:</b> {('#' + str(rank)) if rank else '—'}",
        "",
        f"<b>Опыт:</b> {xp_current}/{xp_needed} (ур. {level})",
        f"<b>Прогресс:</b> [{bar}]",
        f"<b>Открытые герои:</b> {', '.join(get_character(hero_id).get('name', hero_id) for hero_id in sorted(unlocked_set))}",
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

    if available_unlocks > 0:
        lines.append("")
        lines.append(f"<b>Доступно открытий:</b> {available_unlocks}")
    elif next_required_level:
        lines.append("")
        lines.append(f"<b>Следующее открытие:</b> уровень {next_required_level}")
    else:
        lines.append("")
        lines.append("<b>Все герои открыты.</b>")

    if star_summary:
        lines.append("")
        lines.append("<b>Stars:</b>")
        for entry in star_summary:
            levels = int(entry.get("levels", 0))
            count = int(entry.get("count", 0))
            stars = int(entry.get("stars", 0))
            xp_added = int(entry.get("xp_added", 0))
            lines.append(f"- +{levels} ур.: {count} (⭐{stars}) | XP +{xp_added}")

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
    if star_total:
        permanent.append(f"Куплено звезд: {star_total}")
    if permanent:
        lines.extend(f"- {name}" for name in permanent)
    else:
        lines.append("<i>Пока нет.</i>")

    return "\n".join(lines), available_unlocks > 0


@router.callback_query(F.data == "menu:profile")
async def profile_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    user_id = user_row[0]
    is_admin = is_admin_user(callback.from_user)
    lines, can_unlock = await build_profile_text(user_id, is_admin=is_admin)
    await callback.answer()
    await edit_or_send(callback, lines, reply_markup=profile_kb(can_unlock=can_unlock))
