from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot import db
from bot.game.logic import new_tutorial_state, render_state, tutorial_force_endturn, is_desperate_charge_available
from bot.handlers.helpers import is_admin_id
from bot.keyboards import battle_kb, inventory_kb, main_menu_kb, tutorial_fail_kb
from bot.story import build_chapter_caption
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
    )


async def _send_tutorial_intro(message: Message) -> None:
    caption = build_chapter_caption(0)
    await message.answer(caption, parse_mode="HTML")


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    user_id = await db.ensure_user(user.id, user.username)
    tutorial_done = await db.get_tutorial_done(user.id)
    if not tutorial_done:
        active_tutorial = await db.get_active_tutorial(user_id)
        if active_tutorial:
            _run_id, state = active_tutorial
        else:
            state = new_tutorial_state()
            await db.create_tutorial_run(user_id, state)
            await _send_tutorial_intro(message)
        text = _tutorial_fail_text(state) if state.get("phase") == "tutorial_failed" else render_state(state)
        await message.answer(text, reply_markup=_tutorial_markup(state))
        return
    active_run = await db.get_active_run(user_id)
    is_admin = is_admin_id(user.id)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb(bool(active_run), is_admin=is_admin))
