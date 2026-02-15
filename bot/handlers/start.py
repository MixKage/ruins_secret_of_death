from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.api_client import start_state as api_start_state
from bot.api_client import get_story_chapter as api_get_story_chapter
from bot.game.characters import potion_action_label
from bot.game.logic import render_state, tutorial_force_endturn, is_desperate_charge_available
from bot.handlers.helpers import is_admin_id
from bot.keyboards import battle_kb, inventory_kb, main_menu_kb, tutorial_fail_kb
from bot.texts import WELCOME_TEXT

router = Router()


def _tutorial_fail_text(state: dict) -> str:
    reason = state.get("tutorial_fail_reason")
    lines = ["<b>Обучение провалено.</b>"]
    if reason:
        lines.append(reason)
    lines.append("Хотите начать заново?")
    return "\n".join(lines)


def _tutorial_markup(state: dict):
    phase = state.get("phase")
    if phase == "tutorial_failed":
        return tutorial_fail_kb()
    if phase == "inventory":
        return inventory_kb(state.get("player", {}).get("scrolls", []))
    player = state.get("player", {})
    return battle_kb(
        has_potion=bool(player.get("potions")),
        can_attack=player.get("ap", 0) > 0 or is_desperate_charge_available(state),
        can_attack_all=player.get("ap", 0) > 1,
        show_info=bool(state.get("show_info")),
        can_endturn=player.get("ap", 0) <= 0 or tutorial_force_endturn(state),
        potion_label=potion_action_label(state.get("character_id")),
    )


async def _send_tutorial_intro(message: Message) -> None:
    response = await api_get_story_chapter(0)
    caption = response.get("caption", "")
    await message.answer(caption, parse_mode="HTML")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    response = await api_start_state(user.id, user.username)
    if response.get("status") == "tutorial":
        if response.get("tutorial_intro"):
            await _send_tutorial_intro(message)
        state = response.get("state")
        if not state:
            await message.answer("Не удалось загрузить обучение.")
            return
        text = _tutorial_fail_text(state) if response.get("tutorial_failed") else render_state(state)
        await message.answer(text, reply_markup=_tutorial_markup(state))
        return

    is_admin = is_admin_id(user.id)
    has_active = bool(response.get("has_active_run"))
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(has_active, is_admin=is_admin))
