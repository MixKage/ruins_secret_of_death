from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.game.data import ENEMIES
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.keyboards import main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()


def _enemy_name_map() -> dict:
    return {item["id"]: item["name"] for item in ENEMIES}


def _format_stats(stats: dict, max_floor: int) -> str:
    if not stats:
        return "<i>Статистика пока пустая.</i>"

    total_runs = stats.get("total_runs", 0)
    deaths = stats.get("deaths", 0)
    treasures_found = stats.get("treasures_found", 0)
    chests_opened = stats.get("chests_opened", 0)
    kills = stats.get("kills", {})
    total_kills = sum(kills.values())

    death_floor = None
    death_count = 0
    for floor, count in stats.get("deaths_by_floor", {}).items():
        if count > death_count:
            death_floor = floor
            death_count = count

    lines = [
        "<b>Общая статистика</b>",
        f"<b>Всего забегов:</b> {total_runs}",
        f"<b>Максимальный этаж:</b> {max_floor}",
        f"<b>Всего убийств:</b> {total_kills}",
        f"<b>Сундуков открыто:</b> {chests_opened}",
        f"<b>Найдено сокровищ:</b> {treasures_found}",
    ]

    if deaths > 0 and death_floor is not None:
        lines.append(f"<b>Смертей:</b> {deaths} (чаще всего на этаже <b>{death_floor}</b> — {death_count} раз)")
    else:
        lines.append(f"<b>Смертей:</b> {deaths}")

    if total_kills > 0:
        lines.append("")
        lines.append("<b>Кого вы победили:</b>")
        name_map = _enemy_name_map()
        for enemy_id, count in sorted(kills.items(), key=lambda item: item[1], reverse=True):
            name = name_map.get(enemy_id, enemy_id)
            lines.append(f"- {name}: {count}")

    return "\n".join(lines)


@router.callback_query(F.data == "menu:stats")
async def stats_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    user_id = user_row[0]
    max_floor = user_row[3] if len(user_row) > 3 else 0
    stats = await db.get_user_stats(user_id)
    text = _format_stats(stats or {}, max_floor)
    has_active = bool(await db.get_active_run(user_id))

    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await edit_or_send(callback, text, reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin))
