from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import db
from bot.game.logic import (
    apply_reward,
    apply_event_choice,
    apply_boss_artifact_choice,
    apply_treasure_choice,
    build_enemy_info_text,
    build_fallen_boss_intro,
    count_potions,
    end_turn,
    enforce_ap_cap,
    new_run_state,
    _append_log,
    player_attack,
    player_use_potion,
    player_use_potion_by_id,
    player_use_scroll,
    render_state,
    TREASURE_REWARD_XP,
    LATE_BOSS_NAME_FALLBACK,
)
from bot.keyboards import (
    battle_kb,
    boss_artifact_kb,
    event_kb,
    inventory_kb,
    potion_kb,
    main_menu_kb,
    reward_kb,
    treasure_kb,
    forfeit_confirm_kb,
)
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.progress import ensure_current_season, record_run_progress
from bot.utils.telegram import edit_or_send, safe_edit_text

router = Router()

async def _show_main_menu(callback: CallbackQuery, text: str = "Главное меню") -> None:
    is_admin = is_admin_user(callback.from_user)
    if callback.message:
        await safe_edit_text(callback.message, text, reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin))
    elif callback.from_user:
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin),
        )



async def _handle_forfeit(callback: CallbackQuery, user_id: int, run_id: int, state: dict) -> None:
    await db.update_run(run_id, state)
    await db.finish_run(run_id, state.get("floor", 0))
    await db.update_user_max_floor(user_id, state.get("floor", 0))
    await db.record_run_stats(user_id, state, died=False)
    await record_run_progress(user_id, state, died=False)
    await callback.answer("Забег завершен.")
    if callback.message:
        await safe_edit_text(
            callback.message,
            "Вы покинули руины. Забег завершен.",
            reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
        )



async def _ensure_fallen_boss_details(
    run_id: int,
    state: dict,
    exclude_telegram_id: int | None = None,
) -> None:
    if state.get("phase") != "boss_prep" or state.get("boss_kind") != "fallen":
        return
    if state.get("boss_name") and state.get("boss_intro_lines"):
        return
    boss_name = await db.get_random_boss_name(
        min_floor=10,
        exclude_telegram_id=exclude_telegram_id,
    )
    if not boss_name:
        boss_name = LATE_BOSS_NAME_FALLBACK
    state["boss_name"] = boss_name
    state["boss_intro_lines"] = build_fallen_boss_intro(boss_name)
    await db.update_run(run_id, state)


def _format_run_summary(state: dict, rank: int | None) -> str:
    player = state.get("player", {})
    floor = state.get("floor", 0)
    weapon = player.get("weapon", {}).get("name", "Без оружия")
    kills = state.get("kills", {}) or {}
    total_kills = sum(kills.values())
    chests_opened = state.get("chests_opened", 0)
    treasures_found = state.get("treasures_found", 0)
    treasure_xp = int(state.get("treasure_xp", 0))
    if treasure_xp <= 0:
        treasure_xp = int(treasures_found) * TREASURE_REWARD_XP
    bonus_xp = total_kills + treasure_xp
    hp_max = int(player.get("hp_max", 0))
    ap_max = int(player.get("ap_max", 0))
    armor = int(round(player.get("armor", 0)))
    accuracy = int(round(player.get("accuracy", 0) * 100))
    evasion = int(round(player.get("evasion", 0) * 100))
    power = int(player.get("power", 0))
    luck = int(round(player.get("luck", 0) * 100))

    lines = [
        "<b>Забег завершен</b>",
        "Ссылка на бота: <a href=\"https://t.me/Ruins_GameBot\">t.me/Ruins_GameBot</a>",
        f"<b>Достигнутый этаж:</b> {floor}",
        f"<b>Оружие:</b> <b>{weapon}</b>",
        f"<b>Убийств:</b> {total_kills}",
        f"<b>Сундуков открыто:</b> {chests_opened}",
        f"<b>Сокровищ найдено:</b> {treasures_found}",
        f"<b>Бонусный опыт:</b> {bonus_xp} (убийства {total_kills}, сокровища {treasures_found} x {TREASURE_REWARD_XP})",
        "",
        (
            f"<b>Итоговые статы:</b> HP {hp_max} | ОД {ap_max} | "
            f"Броня {armor} | Точность {accuracy}% | Уклонение {evasion}% | "
            f"Сила +{power} | Удача {luck}%"
        ),
    ]
    if rank is not None and rank <= 10:
        lines.append(f"<b>Вы в топ-10:</b> место {rank}")
    return "\n".join(lines)


def _battle_markup(state: dict):
    player = state["player"]
    has_potion = bool(player.get("potions"))
    can_attack = player["ap"] > 0
    can_attack_all = player["ap"] > 1
    can_endturn = player["ap"] <= 0
    show_info = bool(state.get("show_info"))
    return battle_kb(
        has_potion=has_potion,
        can_attack=can_attack,
        can_attack_all=can_attack_all,
        show_info=show_info,
        can_endturn=can_endturn,
    )


async def _send_state(callback: CallbackQuery, state: dict, run_id: int | None = None) -> None:
    if run_id is not None:
        exclude_id = callback.from_user.id if callback.from_user else None
        await _ensure_fallen_boss_details(run_id, state, exclude_telegram_id=exclude_id)
        if enforce_ap_cap(state):
            await db.update_run(run_id, state)
    text = render_state(state)
    is_admin = is_admin_user(callback.from_user)
    markup = _markup_for_state(state, is_admin=is_admin)
    await edit_or_send(callback, text, reply_markup=markup)


def _markup_for_state(state: dict, is_admin: bool = False):
    if state["phase"] == "battle":
        return _battle_markup(state)
    if state["phase"] == "forfeit_confirm":
        return forfeit_confirm_kb()
    if state["phase"] == "reward":
        return reward_kb(len(state.get("rewards", [])))
    if state["phase"] == "event":
        return event_kb(state.get("event_options", []))
    if state["phase"] == "boss_prep":
        return boss_artifact_kb(state.get("boss_artifacts", []))
    if state["phase"] == "treasure":
        return treasure_kb()
    if state["phase"] == "inventory":
        return inventory_kb(state["player"].get("scrolls", []))
    if state["phase"] == "potion_select":
        small_count = count_potions(state["player"], "potion_small")
        medium_count = count_potions(state["player"], "potion_medium")
        strong_count = count_potions(state["player"], "potion_strong")
        return potion_kb(small_count, medium_count, strong_count)
    return main_menu_kb(has_active_run=False, is_admin=is_admin)


@router.callback_query(F.data == "menu:continue")
async def continue_run(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback, text="Нет активного забега.")
        return

    run_id, state = active
    await callback.answer()
    await _send_state(callback, state, run_id)


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
        await record_run_progress(user_id, state, died=False)

    state = new_run_state()
    run_id = await db.create_run(user_id, state)
    await callback.answer()
    await _send_state(callback, state, run_id)


@router.message(Command("reset"))
async def reset_handler(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    user_id = await db.ensure_user(user.id, user.username)
    active = await db.get_active_run(user_id)
    if not active:
        is_admin = is_admin_user(message.from_user)
        await message.answer("Активного забега нет.", reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin))
        return

    run_id, state = active
    await _ensure_fallen_boss_details(run_id, state)
    phase_name = {
        "battle": "бой",
        "reward": "награда",
        "event": "комнаты",
        "boss_prep": "артефакты перед боссом",
        "treasure": "сундук",
        "inventory": "инвентарь",
        "dead": "смерть",
    }.get(state.get("phase"), state.get("phase", "неизвестно"))
    await message.answer(f"<b>Текущая фаза:</b> {phase_name}")
    is_admin = is_admin_user(message.from_user)
    await message.answer(render_state(state), reply_markup=_markup_for_state(state, is_admin=is_admin))


@router.callback_query(F.data.startswith("action:"))
async def battle_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "battle":
        await callback.answer("Сейчас не фаза боя.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    action = callback.data.split(":", 1)[1]
    if action == "attack":
        player_attack(state)
    elif action == "attack_all":
        boss_target = None
        total_boss_damage = None
        alive_before = sum(1 for enemy in state.get("enemies", []) if enemy.get("hp", 0) > 0)
        if state.get("boss_kind"):
            boss_target = next((enemy for enemy in state.get("enemies", []) if enemy.get("hp", 0) > 0), None)
            if boss_target:
                total_boss_damage = 0
        while state["phase"] == "battle" and state["player"]["ap"] > 0:
            prev_hp = boss_target.get("hp", 0) if boss_target else 0
            player_attack(state, log_kills=False)
            if total_boss_damage is not None and boss_target:
                total_boss_damage += max(0, prev_hp - boss_target.get("hp", 0))
            if state["phase"] != "battle":
                break
        if total_boss_damage is not None and total_boss_damage > 0:
            _append_log(state, f"Суммарный урон по боссу: {total_boss_damage}.")
        if alive_before > 1:
            alive_after = sum(1 for enemy in state.get("enemies", []) if enemy.get("hp", 0) > 0)
            killed = max(0, alive_before - alive_after)
            _append_log(state, f"Побеждено врагов за ход: {killed}.")
    elif action == "inventory":
        state["phase"] = "inventory"
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    elif action == "potion":
        potions = state["player"].get("potions", [])
        potion_types = {potion.get("id") for potion in potions if potion.get("id")}
        if len(potion_types) > 1:
            state["phase"] = "potion_select"
            await db.update_run(run_id, state)
            await callback.answer()
            await _send_state(callback, state, run_id)
            return
        if potion_types:
            player_use_potion_by_id(state, next(iter(potion_types)))
        else:
            player_use_potion(state)
    elif action == "info":
        state["show_info"] = not state.get("show_info", False)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    elif action == "endturn":
        if state["player"]["ap"] > 0:
            await callback.answer("Сначала потратьте все ОД.", show_alert=True)
            return
        end_turn(state)
    elif action == "forfeit":
        state["phase"] = "forfeit_confirm"
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return

    if state["phase"] == "dead":
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_row[0], state.get("floor", 0))
        await db.record_run_stats(user_row[0], state, died=True)
        await record_run_progress(user_row[0], state, died=True)

        await callback.answer()
        if callback.message:
            await safe_edit_text(callback.message, render_state(state), reply_markup=None)

        season_id, _season_key = await ensure_current_season()
        rank = await db.get_user_season_rank(user_row[0], season_id)
        summary_text = _format_run_summary(state, rank)
        await callback.bot.send_message(callback.from_user.id, summary_text)
        await callback.bot.send_message(
            callback.from_user.id,
            "Главное меню",
            reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
        )
        return
    else:
        await db.update_run(run_id, state)

    await callback.answer()
    await _send_state(callback, state, run_id)



@router.callback_query(F.data.startswith("forfeit:"))
async def forfeit_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    action = callback.data.split(":", 1)[1]
    if action == "cancel":
        if state.get("phase") == "forfeit_confirm":
            state["phase"] = "battle"
            await db.update_run(run_id, state)
        await callback.answer("Отмена.")
        await _send_state(callback, state, run_id)
        return
    if action == "confirm":
        if state.get("phase") != "forfeit_confirm":
            await callback.answer("Нечего подтверждать.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        await _handle_forfeit(callback, user_row[0], run_id, state)
        return




@router.callback_query(F.data.startswith("potion:"))
async def potion_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "potion_select":
        await callback.answer("Сейчас не выбор зелий.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    action = callback.data.split(":", 1)[1]
    if action == "back":
        state["phase"] = "battle"
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return

    potion_id = None
    if action == "small":
        potion_id = "potion_small"
    elif action == "medium":
        potion_id = "potion_medium"
    elif action == "strong":
        potion_id = "potion_strong"

    if potion_id:
        state["phase"] = "battle"
        player_use_potion_by_id(state, potion_id)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return

    await callback.answer("Неверное действие.", show_alert=True)
@router.callback_query(F.data.startswith("inventory:"))
async def inventory_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "inventory":
        await callback.answer("Сейчас не инвентарь.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    parts = callback.data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    if action == "back":
        state["phase"] = "battle"
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "use_id" and len(parts) > 2:
        scroll_id = parts[2]
        state["phase"] = "battle"
        scrolls = state.get("player", {}).get("scrolls", [])
        index = None
        for idx, scroll in enumerate(scrolls):
            if scroll.get("id") == scroll_id:
                index = idx
                break
        if index is None:
            await callback.answer("Свиток не найден.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        player_use_scroll(state, index)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "use" and len(parts) > 2:
        try:
            index = int(parts[2])
        except ValueError:
            await callback.answer("Неверный свиток.", show_alert=True)
            return
        state["phase"] = "battle"
        player_use_scroll(state, index)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return

    await callback.answer("Неверное действие.", show_alert=True)
@router.callback_query(F.data.startswith("treasure:"))
async def treasure_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "treasure":
        await callback.answer("Сейчас не время для сундука.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    action = callback.data.split(":", 1)[1]
    equip = action == "equip"
    apply_treasure_choice(state, equip)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state, run_id)


@router.callback_query(F.data.startswith("boss:"))
async def boss_artifact_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "boss_prep":
        await callback.answer("Сейчас не время для артефакта.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    artifact_id = callback.data.split(":", 1)[1]
    apply_boss_artifact_choice(state, artifact_id)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state, run_id)


@router.callback_query(F.data.startswith("reward:"))
async def reward_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "reward":
        await callback.answer("Сейчас не фаза наград.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    reward_index = int(callback.data.split(":", 1)[1])
    apply_reward(state, reward_index)

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state, run_id)


@router.callback_query(F.data.startswith("event:"))
async def event_choice(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state["phase"] != "event":
        await callback.answer("Сейчас не фаза комнат.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    event_id = callback.data.split(":", 1)[1]
    apply_event_choice(state, event_id)

    if state["phase"] == "dead":
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_row[0], state.get("floor", 0))
        await db.record_run_stats(user_row[0], state, died=True)
        await record_run_progress(user_row[0], state, died=True)
    else:
        await db.update_run(run_id, state)

    await callback.answer()
    await _send_state(callback, state, run_id)
