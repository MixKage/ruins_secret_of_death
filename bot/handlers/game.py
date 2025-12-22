from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import db
from bot.game.logic import (
    apply_reward,
    apply_event_choice,
    apply_boss_artifact_choice,
    apply_treasure_choice,
    build_enemy_info_text,
    end_turn,
    new_run_state,
    player_attack,
    player_use_potion,
    render_state,
)
from bot.keyboards import battle_kb, boss_artifact_kb, event_kb, main_menu_kb, reward_kb, treasure_kb
from bot.handlers.helpers import get_user_row
from bot.utils.telegram import edit_or_send, safe_edit_text

router = Router()


def _battle_markup(state: dict):
    player = state["player"]
    has_potion = bool(player.get("potions"))
    can_attack = player["ap"] > 0
    show_info = bool(state.get("show_info"))
    return battle_kb(has_potion=has_potion, can_attack=can_attack, show_info=show_info)


async def _send_state(callback: CallbackQuery, state: dict) -> None:
    text = render_state(state)
    if state["phase"] == "battle":
        markup = _battle_markup(state)
    elif state["phase"] == "reward":
        markup = reward_kb(len(state.get("rewards", [])))
    elif state["phase"] == "event":
        markup = event_kb(state.get("event_options", []))
    elif state["phase"] == "boss_prep":
        markup = boss_artifact_kb(state.get("boss_artifacts", []))
    elif state["phase"] == "treasure":
        markup = treasure_kb()
    else:
        markup = main_menu_kb(has_active_run=False)

    await edit_or_send(callback, text, reply_markup=markup)


@router.callback_query(F.data == "menu:continue")
async def continue_run(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        if callback.message:
            await safe_edit_text(callback.message, "Нет активного забега.", reply_markup=main_menu_kb())
        return

    _, state = active
    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data == "menu:new")
async def start_new_run(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    user_id = await db.ensure_user(user.id, user.username)
    active = await db.get_active_run(user_id)
    if active:
        run_id, state = active
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_id, state.get("floor", 0))
        await db.record_run_stats(user_id, state, died=False)

    state = new_run_state()
    await db.create_run(user_id, state)
    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data.startswith("action:"))
async def battle_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        return

    run_id, state = active
    if state["phase"] != "battle":
        await callback.answer("Сейчас не фаза боя.", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]
    if action == "attack":
        player_attack(state)
    elif action == "potion":
        player_use_potion(state)
    elif action == "info":
        state["show_info"] = not state.get("show_info", False)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state)
        return
    elif action == "endturn":
        end_turn(state)
    elif action == "forfeit":
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_row[0], state.get("floor", 0))
        await db.record_run_stats(user_row[0], state, died=False)
        await callback.answer("Забег завершен.")
        if callback.message:
            await safe_edit_text(
                callback.message,
                "Вы покинули руины. Забег завершен.",
                reply_markup=main_menu_kb(has_active_run=False),
            )
        return

    if state["phase"] == "dead":
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_row[0], state.get("floor", 0))
        await db.record_run_stats(user_row[0], state, died=True)
    else:
        await db.update_run(run_id, state)

    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data.startswith("treasure:"))
async def treasure_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        return

    run_id, state = active
    if state["phase"] != "treasure":
        await callback.answer("Сейчас не время для сундука.", show_alert=True)
        return

    action = callback.data.split(":", 1)[1]
    equip = action == "equip"
    apply_treasure_choice(state, equip)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data.startswith("boss:"))
async def boss_artifact_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        return

    run_id, state = active
    if state["phase"] != "boss_prep":
        await callback.answer("Сейчас не время для артефакта.", show_alert=True)
        return

    artifact_id = callback.data.split(":", 1)[1]
    apply_boss_artifact_choice(state, artifact_id)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data.startswith("reward:"))
async def reward_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        return

    run_id, state = active
    if state["phase"] != "reward":
        await callback.answer("Сейчас не фаза наград.", show_alert=True)
        return

    reward_index = int(callback.data.split(":", 1)[1])
    apply_reward(state, reward_index)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data.startswith("event:"))
async def event_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        return

    run_id, state = active
    if state["phase"] != "event":
        await callback.answer("Сейчас не фаза комнат.", show_alert=True)
        return

    event_id = callback.data.split(":", 1)[1]
    apply_event_choice(state, event_id)

    if state["phase"] == "dead":
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_row[0], state.get("floor", 0))
        await db.record_run_stats(user_row[0], state, died=True)
    else:
        await db.update_run(run_id, state)

    await callback.answer()
    await _send_state(callback, state)
