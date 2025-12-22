from html import escape

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.handlers.helpers import get_user_row

router = Router()


def _percent(value: float) -> str:
    return f"{int(round(value * 100))}%"


def _format_share_message(state: dict, max_floor: int, rank: int | None) -> str:
    player = state.get("player", {})
    floor = max(max_floor, state.get("floor", 0))
    weapon = escape(player.get("weapon", {}).get("name", "Без оружия"))

    hp_max = int(player.get("hp_max", 0))
    ap_max = int(player.get("ap_max", 0))
    armor = int(round(player.get("armor", 0)))
    accuracy = _percent(player.get("accuracy", 0))
    evasion = _percent(player.get("evasion", 0))
    power = int(player.get("power", 0))
    luck = _percent(player.get("luck", 0))

    lines = [
        "<b>Поделись забегом!</b>",
        "Ссылка на бота: <a href=\"https://t.me/Ruins_GameBot\">t.me/Ruins_GameBot</a>",
        "",
        f"Я дошел до <b>{floor}</b> этажа — руины запомнят это.",
        f"<b>Оружие:</b> <b>{weapon}</b>",
        (
            f"<b>Статы:</b> HP {hp_max} | ОД {ap_max} | Броня {armor} | "
            f"Точность {accuracy} | Уклонение {evasion} | Сила +{power} | Удача {luck}"
        ),
    ]

    if rank is not None:
        lines.append("")
        lines.append(f"<b>Кстати, я занимаю {rank} место в рейтинге.</b>")

    return "\n".join(lines)


@router.callback_query(F.data == "menu:share")
async def share_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    user = callback.from_user
    if user is None:
        return

    user_id = user_row[0]
    active = await db.get_active_run(user_id)
    if active:
        await callback.answer("Завершите активный забег, чтобы поделиться.", show_alert=True)
        return

    last_run = await db.get_last_run(user_id)
    if not last_run:
        await callback.answer()
        await callback.bot.send_message(user.id, "Пока нет завершенных забегов.")
        return

    _, max_floor, state = last_run
    leaderboard = await db.get_leaderboard_with_ids()
    rank = None
    for idx, (row_user_id, _username, _max_floor) in enumerate(leaderboard, start=1):
        if row_user_id == user_id:
            rank = idx
            break

    text = _format_share_message(state, max_floor, rank)
    await callback.answer()
    await callback.bot.send_message(user.id, text, disable_web_page_preview=True)
    await callback.bot.send_message(user.id, text)
