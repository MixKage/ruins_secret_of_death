from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, BufferedInputFile

from bot.api_client import get_heroes_menu as api_get_heroes_menu
from bot.api_client import get_hero_detail as api_get_hero_detail
from bot.api_client import unlock_hero as api_unlock_hero
from bot.api_client import get_hero_photo as api_get_hero_photo
from bot.game.characters import CHARACTERS, get_character
from bot.keyboards import hero_detail_kb, heroes_menu_kb
from bot.utils.telegram import edit_or_send, safe_edit_text

router = Router()


def _normalize_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    for _ in range(3):
        if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
            text = text[1:-1].strip()
            continue
        break
    return text or None


def _normalize_unlocked_ids(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    result: set[str] = set()
    for item in values:
        hero_id = _normalize_id(item)
        if hero_id:
            result.add(hero_id)
    result.add("wanderer")
    return result


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off", ""}:
            return False
    return bool(value)


async def _show_loading(callback: CallbackQuery) -> None:
    message = callback.message
    if not message or not message.text:
        return
    try:
        await safe_edit_text(message, "Загрузка...", reply_markup=None)
    except Exception:
        return


async def show_heroes_menu(callback: CallbackQuery, user_id: int, source: str = "menu") -> None:
    response = await api_get_heroes_menu(user_id)
    unlocked_ids = _normalize_unlocked_ids(response.get("unlocked_ids"))
    text = response.get("text", "<i>Герои недоступны.</i>")
    await edit_or_send(
        callback,
        text,
        reply_markup=heroes_menu_kb(list(CHARACTERS.values()), unlocked_ids, source=source),
    )


async def _show_hero_detail(callback: CallbackQuery, user_id: int, hero_id: str, source: str) -> None:
    response = await api_get_hero_detail(user_id, hero_id)
    character = get_character(hero_id)
    text = response.get("text", f"<b>{character.get('name', 'Герой')}</b>")
    markup = hero_detail_kb(
        hero_id=hero_id,
        is_unlocked=_as_bool(response.get("is_unlocked")),
        can_unlock=_as_bool(response.get("can_unlock")),
        required_level=response.get("required_level"),
        allow_stars=_as_bool(response.get("allow_stars")),
        source=source,
    )
    chat_id = callback.from_user.id if callback.from_user else None
    if chat_id is None and callback.message:
        chat_id = callback.message.chat.id
    if chat_id is not None:
        try:
            photo_bytes = await api_get_hero_photo(hero_id)
        except Exception:
            photo_bytes = None
        if photo_bytes:
            photo = BufferedInputFile(photo_bytes, filename=f"{hero_id}.jpg")
            await callback.bot.send_photo(
                chat_id,
                photo,
                caption=text,
                reply_markup=markup,
                parse_mode="HTML",
            )
            return
    await edit_or_send(callback, text, reply_markup=markup)


@router.callback_query(F.data.startswith("heroes:menu:"))
async def heroes_menu_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    parts = callback.data.split(":")
    source = parts[2] if len(parts) > 2 else "menu"
    await callback.answer()
    await show_heroes_menu(callback, user.id, source=source)


@router.callback_query(F.data.startswith("hero:info:"))
async def hero_info_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    parts = callback.data.split(":")
    hero_id = parts[2] if len(parts) > 2 else ""
    source = parts[3] if len(parts) > 3 else "menu"
    if hero_id not in CHARACTERS:
        await callback.answer("Герой недоступен.", show_alert=True)
        await show_heroes_menu(callback, user.id, source=source)
        return
    await callback.answer()
    await _show_loading(callback)
    await _show_hero_detail(callback, user.id, hero_id, source)


@router.callback_query(F.data.startswith("hero:unlock:"))
async def hero_unlock_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    parts = callback.data.split(":")
    hero_id = parts[2] if len(parts) > 2 else ""
    source = parts[3] if len(parts) > 3 else "menu"
    if hero_id not in CHARACTERS:
        await callback.answer("Герой недоступен.", show_alert=True)
        await show_heroes_menu(callback, user.id, source=source)
        return
    response = await api_unlock_hero(user.id, hero_id)
    status = response.get("status")
    if status == "stars":
        await callback.answer()
        from bot.handlers.stars import stars_menu_callback
        await stars_menu_callback(callback)
        return
    detail = response.get("detail") or {}
    await callback.answer("Герой открыт." if _as_bool(detail.get("is_unlocked")) else "")
    await _show_hero_detail(callback, user.id, hero_id, source)


@router.callback_query(F.data == "hero:locked")
async def hero_locked_callback(callback: CallbackQuery) -> None:
    await callback.answer("Герой пока недоступен.", show_alert=True)
