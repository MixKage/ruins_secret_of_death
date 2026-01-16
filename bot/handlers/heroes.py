from __future__ import annotations

from typing import Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot import db
from bot.game.characters import CHARACTERS, DEFAULT_CHARACTER_ID, get_character
from bot.handlers.helpers import get_user_row
from bot.keyboards import hero_detail_kb, heroes_menu_kb
from bot.progress import xp_to_level
from bot.utils.telegram import edit_or_send

router = Router()

UNLOCK_STEP = 5


def _unlock_state(level: int, unlocked_ids: list[str]) -> Tuple[set[str], int, int | None, int]:
    unlocked_set = set(unlocked_ids or [])
    unlocked_set.add(DEFAULT_CHARACTER_ID)
    total_unlockable = max(0, len(CHARACTERS) - 1)
    unlocked_extra = max(0, len(unlocked_set) - 1)
    slots = min(total_unlockable, level // UNLOCK_STEP)
    available = max(0, slots - unlocked_extra)
    required_level = None
    if unlocked_extra < total_unlockable:
        required_level = max(UNLOCK_STEP, (unlocked_extra + 1) * UNLOCK_STEP)
    return unlocked_set, available, required_level, total_unlockable


async def show_heroes_menu(callback: CallbackQuery, user_id: int, source: str = "menu") -> None:
    profile = await db.get_user_profile(user_id) or {}
    level, _current, _need = xp_to_level(int(profile.get("xp", 0)))
    unlocked_ids = await db.get_unlocked_heroes(user_id)
    unlocked_set, available, required_level, total_unlockable = _unlock_state(level, unlocked_ids)

    lines = [
        "<b>Выберите героя</b>",
        "Нажмите на героя, чтобы увидеть подробности.",
        "Выбор действует только на текущий забег.",
        f"<b>Уровень:</b> {level}",
        f"<b>Открыто:</b> {len(unlocked_set)}/{len(CHARACTERS)}",
    ]
    if available > 0:
        lines.append(f"<b>Доступно открытий:</b> {available}")
    elif required_level:
        lines.append(f"<b>Следующее открытие:</b> уровень {required_level}")
    else:
        lines.append("<b>Все герои открыты.</b>")

    await edit_or_send(
        callback,
        "\n".join(lines),
        reply_markup=heroes_menu_kb(list(CHARACTERS.values()), unlocked_set, source=source),
    )


async def _show_hero_detail(callback: CallbackQuery, user_id: int, hero_id: str, source: str) -> None:
    character = get_character(hero_id)
    profile = await db.get_user_profile(user_id) or {}
    level, _current, _need = xp_to_level(int(profile.get("xp", 0)))
    unlocked_ids = await db.get_unlocked_heroes(user_id)
    unlocked_set, available, required_level, _total_unlockable = _unlock_state(level, unlocked_ids)
    is_unlocked = hero_id in unlocked_set

    lines = [f"<b>{character.get('name', 'Герой')}</b>", ""]
    for desc in character.get("description", []):
        lines.append(f"- {desc}")
    lines.append("")
    lines.append(f"<b>Статус:</b> {'открыт' if is_unlocked else 'закрыт'}")
    if not is_unlocked:
        if available > 0:
            lines.append("<i>Можно открыть этого героя сейчас.</i>")
        elif required_level:
            lines.append(f"<i>Требуется уровень {required_level}.</i>")
            lines.append("<i>Уровень можно поднять через Stars в профиле.</i>")

    markup = hero_detail_kb(
        hero_id=hero_id,
        is_unlocked=is_unlocked,
        can_unlock=not is_unlocked and available > 0,
        required_level=required_level,
        source=source,
    )
    await edit_or_send(callback, "\n".join(lines), reply_markup=markup)


@router.callback_query(F.data.startswith("heroes:menu:"))
async def heroes_menu_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 else "menu"
    await callback.answer()
    await show_heroes_menu(callback, user_row[0], source=source)


@router.callback_query(F.data.startswith("hero:info:"))
async def hero_info_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    parts = callback.data.split(":")
    hero_id = parts[2] if len(parts) > 2 else ""
    source = parts[3] if len(parts) > 3 else "menu"
    if hero_id not in CHARACTERS:
        await callback.answer("Герой недоступен.", show_alert=True)
        await show_heroes_menu(callback, user_row[0], source=source)
        return
    await callback.answer()
    await _show_hero_detail(callback, user_row[0], hero_id, source)


@router.callback_query(F.data.startswith("hero:unlock:"))
async def hero_unlock_callback(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    parts = callback.data.split(":")
    hero_id = parts[2] if len(parts) > 2 else ""
    source = parts[3] if len(parts) > 3 else "menu"
    if hero_id not in CHARACTERS:
        await callback.answer("Герой недоступен.", show_alert=True)
        await show_heroes_menu(callback, user_row[0], source=source)
        return
    if hero_id == DEFAULT_CHARACTER_ID:
        await callback.answer("Рыцарь уже открыт.", show_alert=True)
        await _show_hero_detail(callback, user_row[0], hero_id, source)
        return
    profile = await db.get_user_profile(user_row[0]) or {}
    level, _current, _need = xp_to_level(int(profile.get("xp", 0)))
    unlocked_ids = await db.get_unlocked_heroes(user_row[0])
    unlocked_set, available, required_level, _total_unlockable = _unlock_state(level, unlocked_ids)
    if hero_id in unlocked_set:
        await callback.answer("Герой уже открыт.", show_alert=True)
        await _show_hero_detail(callback, user_row[0], hero_id, source)
        return
    if available <= 0:
        required_level = required_level or UNLOCK_STEP
        await callback.answer(f"Требуется уровень {required_level}.", show_alert=True)
        await _show_hero_detail(callback, user_row[0], hero_id, source)
        return
    await db.unlock_hero(user_row[0], hero_id)
    await callback.answer("Герой открыт.")
    await _show_hero_detail(callback, user_row[0], hero_id, source)


@router.callback_query(F.data == "hero:locked")
async def hero_locked_callback(callback: CallbackQuery) -> None:
    await callback.answer("Герой пока недоступен.", show_alert=True)
