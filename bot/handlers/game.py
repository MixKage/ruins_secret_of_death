from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message, LabeledPrice

from bot import db
from bot.game.characters import DEFAULT_CHARACTER_ID, potion_action_label
from bot.game.logic import (
    apply_reward,
    apply_event_choice,
    apply_boss_artifact_choice,
    apply_treasure_choice,
    build_enemy_info_text,
    build_fallen_boss_intro,
    CHARACTERS,
    count_potions,
    end_turn,
    enforce_ap_cap,
    is_desperate_charge_available,
    new_run_state,
    new_tutorial_state,
    _append_log,
    player_attack,
    player_use_potion,
    player_use_potion_by_id,
    player_use_scroll,
    render_state,
    tutorial_apply_action,
    tutorial_force_endturn,
    tutorial_use_scroll,
    use_duel_zone,
    use_hunter_trap,
    use_rune_guard_throw,
    use_rune_guard_shield,
    TREASURE_REWARD_XP,
    LATE_BOSS_NAME_FALLBACK,
)
from bot.game.run_tasks import run_tasks_summary, run_tasks_xp
from bot.handlers.heroes import show_heroes_menu
from bot.keyboards import (
    battle_kb,
    boss_artifact_kb,
    event_kb,
    inventory_kb,
    potion_kb,
    main_menu_kb,
    run_tasks_kb,
    reward_kb,
    treasure_kb,
    forfeit_confirm_kb,
    tutorial_fail_kb,
    story_nav_kb,
    second_chance_kb,
    second_chance_owned_kb,
)
from bot.handlers.stars import (
    STARS_CURRENCY,
    STARS_PROVIDER_TOKEN,
    get_second_chance_price,
)
from bot.handlers.helpers import get_user_row, is_admin_user
from bot.progress import ensure_current_season, record_run_progress, xp_to_level
from bot.story import build_chapter_caption, chapter_photo_path, max_unlocked_chapter, STORY_MAX_CHAPTERS
from bot.utils.telegram import edit_or_send, safe_edit_text

router = Router()

def _pop_tutorial_alert(state: dict) -> str | None:
    return state.pop("tutorial_alert", None)


async def _answer_tutorial_alert(callback: CallbackQuery, alert: str | None) -> None:
    if alert:
        await callback.answer(alert, show_alert=True)
        return
    await callback.answer()

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

async def _show_character_select(callback: CallbackQuery, user_id: int) -> None:
    await show_heroes_menu(callback, user_id, source="menu")

async def _show_tutorial_failed(callback: CallbackQuery, state: dict) -> None:
    reason = state.get("tutorial_fail_reason")
    lines = ["<b>Обучение провалено.</b>"]
    if reason:
        lines.append(reason)
    lines.append("Хотите начать заново?")
    text = "\n".join(lines)
    if callback.message:
        await safe_edit_text(callback.message, text, reply_markup=tutorial_fail_kb())
    elif callback.from_user:
        await callback.bot.send_message(callback.from_user.id, text, reply_markup=tutorial_fail_kb())

async def _complete_tutorial(callback: CallbackQuery, user_id: int, run_id: int, state: dict) -> None:
    telegram_id = callback.from_user.id if callback.from_user else None
    if telegram_id is not None:
        await db.set_tutorial_done(telegram_id, True)
    await db.update_run(run_id, state)
    await db.finish_tutorial_run(run_id)
    text = (
        "<b>Учебный рекрут повержен.</b>\n"
        "Вы освоили ключевые механики Рыцаря и готовы к руинам.\n"
        "Совет: загляните в <b>Правила</b>, чтобы освежить детали."
    )
    is_admin = is_admin_user(callback.from_user)
    if callback.message:
        await safe_edit_text(callback.message, text, reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin))
    elif callback.from_user:
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin),
        )


async def _get_user_xp(user_id: int) -> int:
    profile = await db.get_user_profile(user_id)
    return int(profile.get("xp", 0)) if profile else 0


def _run_xp_gain(state: dict) -> int:
    treasure_xp = int(state.get("treasure_xp", 0))
    if treasure_xp <= 0:
        treasure_xp = int(state.get("treasures_found", 0)) * TREASURE_REWARD_XP
    floor = int(state.get("floor", 0))
    task_xp = run_tasks_xp(state)
    return max(0, floor + treasure_xp + task_xp)


async def _send_story_chapter(bot, chat_id: int, chapter: int, max_chapter: int) -> None:
    caption = build_chapter_caption(chapter)
    photo_path = chapter_photo_path(chapter)
    markup = story_nav_kb(chapter, max_chapter)
    if photo_path.exists():
        photo = FSInputFile(str(photo_path))
        await bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode="HTML")
        return
    await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

async def _send_tutorial_intro(bot, chat_id: int) -> None:
    caption = build_chapter_caption(0)
    await bot.send_message(chat_id, caption, parse_mode="HTML")


async def _maybe_send_story_chapters(bot, chat_id: int, old_xp: int, state: dict) -> None:
    gained_xp = _run_xp_gain(state)
    if gained_xp <= 0:
        return
    old_level, _old_current, _old_need = xp_to_level(old_xp)
    new_level, _new_current, _new_need = xp_to_level(old_xp + gained_xp)
    if new_level <= old_level:
        return
    max_chapter = max_unlocked_chapter(new_level)
    start = max(1, old_level + 1)
    end = min(new_level, STORY_MAX_CHAPTERS)
    for chapter in range(start, end + 1):
        await _send_story_chapter(bot, chat_id, chapter, max_chapter)

async def _finalize_run_after_death(
    callback: CallbackQuery,
    user_id: int,
    run_id: int,
    state: dict,
) -> None:
    _append_death_log(state)
    old_xp = await _get_user_xp(user_id)
    await db.update_run(run_id, state)
    await db.finish_run(run_id, state.get("floor", 0))
    await db.update_user_max_floor(user_id, state.get("floor", 0))
    await db.record_run_stats(user_id, state, died=True)
    await record_run_progress(user_id, state, died=True)

    await callback.answer()
    if callback.message:
        await safe_edit_text(callback.message, render_state(state), reply_markup=None)

    season_id, _season_key = await ensure_current_season()
    rank = await db.get_user_season_rank(user_id, season_id)
    summary_text = _format_run_summary(state, rank)
    await callback.bot.send_message(callback.from_user.id, summary_text)
    if callback.from_user:
        await _maybe_send_story_chapters(callback.bot, callback.from_user.id, old_xp, state)
    await callback.bot.send_message(
        callback.from_user.id,
        "Главное меню",
        reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
    )

def _append_death_log(state: dict) -> None:
    log = state.get("log", [])
    if any("Забег окончен." in str(line) for line in log):
        return
    _append_log(state, "<b>Вы падаете без сознания.</b> Забег окончен.")

async def _offer_second_chance(
    callback: CallbackQuery,
    run_id: int,
    state: dict,
) -> None:
    state["phase"] = "second_chance_offer"
    state["second_chance_offer_type"] = "buy"
    _append_log(
        state,
        f"Хотите выкупить амулет второго шанса за {get_second_chance_price()}⭐ и продолжить бой?",
    )
    await db.update_run(run_id, state)
    await callback.answer()
    if callback.message:
        await safe_edit_text(callback.message, render_state(state), reply_markup=second_chance_kb())
    elif callback.from_user:
        await callback.bot.send_message(
            callback.from_user.id,
            render_state(state),
            reply_markup=second_chance_kb(),
        )

async def _offer_second_chance_owned(
    callback: CallbackQuery,
    run_id: int,
    state: dict,
) -> None:
    state["phase"] = "second_chance_offer"
    state["second_chance_offer_type"] = "owned"
    _append_log(state, "Использовать амулет второго шанса или отказаться?")
    await db.update_run(run_id, state)
    await callback.answer()
    if callback.message:
        await safe_edit_text(callback.message, render_state(state), reply_markup=second_chance_owned_kb())
    elif callback.from_user:
        await callback.bot.send_message(
            callback.from_user.id,
            render_state(state),
            reply_markup=second_chance_owned_kb(),
        )


async def _handle_forfeit(callback: CallbackQuery, user_id: int, run_id: int, state: dict) -> None:
    old_xp = await _get_user_xp(user_id)
    await db.update_run(run_id, state)
    await db.finish_run(run_id, state.get("floor", 0))
    await db.update_user_max_floor(user_id, state.get("floor", 0))
    await db.record_run_stats(user_id, state, died=False)
    await record_run_progress(user_id, state, died=False)
    if callback.from_user:
        await _maybe_send_story_chapters(callback.bot, callback.from_user.id, old_xp, state)
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
    bonus_xp = treasure_xp
    tasks_completed, tasks_total, task_xp = run_tasks_summary(state)
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
        f"<b>Опыт за сокровища:</b> {bonus_xp} (сокровища {treasures_found} x {TREASURE_REWARD_XP})",
        "",
        (
            f"<b>Итоговые статы:</b> HP {hp_max} | ОД {ap_max} | "
            f"Броня {armor} | Точность {accuracy}% | Уклонение {evasion}% | "
            f"Сила +{power} | Удача {luck}%"
        ),
    ]
    if tasks_total > 0:
        lines.insert(
            8,
            f"<b>Испытания руин:</b> {tasks_completed}/{tasks_total} (+{task_xp} XP)",
        )
    if rank is not None and rank <= 10:
        lines.append(f"<b>Вы в топ-10:</b> место {rank}")
    return "\n".join(lines)


def _battle_markup(state: dict):
    player = state["player"]
    has_potion = bool(player.get("potions"))
    can_attack = player["ap"] > 0 or is_desperate_charge_available(state)
    can_attack_all = player["ap"] > 1
    can_endturn = player["ap"] <= 0 or tutorial_force_endturn(state)
    show_info = bool(state.get("show_info"))
    potion_label = potion_action_label(state.get("character_id"))
    return battle_kb(
        has_potion=has_potion,
        can_attack=can_attack,
        can_attack_all=can_attack_all,
        show_info=show_info,
        can_endturn=can_endturn,
        potion_label=potion_label,
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
    if state["phase"] == "tutorial":
        return _battle_markup(state)
    if state["phase"] == "tutorial_failed":
        return tutorial_fail_kb()
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
        duel_charges = (
            state.get("duel_zone_charges")
            if state.get("character_id") == "duelist"
            else None
        )
        rune_guard_ready = (
            state.get("character_id") == "rune_guard"
            and not state.get("rune_guard_shield_used")
            and not state.get("rune_guard_shield_active")
            and not state.get("rune_guard_throw_active")
        )
        rune_guard_throw_ready = (
            state.get("character_id") == "rune_guard"
            and not state.get("rune_guard_shield_used")
            and not state.get("rune_guard_throw_active")
            and not state.get("rune_guard_shield_active")
        )
        hunter_trap_ready = (
            state.get("character_id") == "hunter"
            and not state.get("hunter_trap_used")
            and not state.get("hunter_trap_active")
            and not state.get("boss_kind")
        )
        return inventory_kb(
            state["player"].get("scrolls", []),
            duel_zone_charges=duel_charges,
            rune_guard_shield_ready=rune_guard_ready,
            rune_guard_throw_ready=rune_guard_throw_ready,
            hunter_trap_ready=hunter_trap_ready,
        )
    if state["phase"] == "run_tasks":
        return run_tasks_kb()
    if state["phase"] == "potion_select":
        small_count = count_potions(state["player"], "potion_small")
        medium_count = count_potions(state["player"], "potion_medium")
        strong_count = count_potions(state["player"], "potion_strong")
        character_id = state.get("character_id")
        if character_id == "executioner":
            strong_count = 0
        return potion_kb(small_count, medium_count, strong_count, character_id=character_id)
    if state["phase"] == "second_chance_offer":
        if state.get("second_chance_offer_type") == "owned":
            return second_chance_owned_kb()
        return second_chance_kb()
    return main_menu_kb(has_active_run=False, is_admin=is_admin)


@router.callback_query(F.data == "menu:continue")
async def continue_run(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    active = await db.get_active_run(user_row[0])
    if not active:
        tutorial_active = await db.get_active_tutorial(user_row[0])
        if tutorial_active:
            run_id, state = tutorial_active
            await callback.answer()
            if state.get("phase") == "tutorial_failed":
                await _show_tutorial_failed(callback, state)
            else:
                await _send_state(callback, state, run_id)
            return
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
    tutorial_done = await db.get_tutorial_done(user.id)
    if not tutorial_done:
        active_tutorial = await db.get_active_tutorial(user_id)
        created = False
        if active_tutorial:
            run_id, state = active_tutorial
        else:
            state = new_tutorial_state()
            run_id = await db.create_tutorial_run(user_id, state)
            created = True
            await _send_tutorial_intro(callback.bot, user.id)
        await callback.answer("Сначала пройдите обучение.")
        if state.get("phase") == "tutorial_failed":
            await _show_tutorial_failed(callback, state)
        else:
            if created and callback.from_user:
                text = render_state(state)
                markup = _markup_for_state(state, is_admin=is_admin_user(callback.from_user))
                await callback.bot.send_message(callback.from_user.id, text, reply_markup=markup)
            else:
                await _send_state(callback, state, run_id)
        return
    active = await db.get_active_run(user_id)
    if active:
        run_id, state = active
        old_xp = await _get_user_xp(user_id)
        await db.update_run(run_id, state)
        await db.finish_run(run_id, state.get("floor", 0))
        await db.update_user_max_floor(user_id, state.get("floor", 0))
        await db.record_run_stats(user_id, state, died=False)
        await record_run_progress(user_id, state, died=False)
        if callback.from_user:
            await _maybe_send_story_chapters(callback.bot, callback.from_user.id, old_xp, state)
    await callback.answer()
    await _show_character_select(callback, user_id)

@router.callback_query(F.data.startswith("hero:select:"))
async def select_character(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    user = callback.from_user
    if user is None:
        return
    if not await db.get_tutorial_done(user.id):
        await callback.answer("Сначала пройдите обучение.", show_alert=True)
        return
    character_id = callback.data.split(":")[-1]
    if character_id not in CHARACTERS:
        await callback.answer("Герой недоступен.", show_alert=True)
        await _show_character_select(callback, user_row[0])
        return
    unlocked_ids = await db.get_unlocked_heroes(user_row[0])
    if not is_admin_user(callback.from_user):
        if character_id not in unlocked_ids and character_id != DEFAULT_CHARACTER_ID:
            await callback.answer("Герой пока не открыт.", show_alert=True)
            await _show_character_select(callback, user_row[0])
            return
    active = await db.get_active_run(user_row[0])
    if active:
        await callback.answer("У вас уже есть активный забег.", show_alert=True)
        run_id, state = active
        await _send_state(callback, state, run_id)
        return
    state = new_run_state(character_id=character_id)
    run_id = await db.create_run(user_row[0], state)
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
        active = await db.get_active_tutorial(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    action = callback.data.split(":", 1)[1]
    if state.get("tutorial"):
        result = tutorial_apply_action(state, action)
        if state.get("tutorial_failed") or result == "fail":
            alert = _pop_tutorial_alert(state)
            await db.update_run(run_id, state)
            await _answer_tutorial_alert(callback, alert)
            await _show_tutorial_failed(callback, state)
            return
        if state.get("tutorial_completed") or result == "complete":
            await _complete_tutorial(callback, user_row[0], run_id, state)
            return
        alert = _pop_tutorial_alert(state)
        await db.update_run(run_id, state)
        await _answer_tutorial_alert(callback, alert)
        await _send_state(callback, state, run_id)
        return
    if state["phase"] != "battle":
        await callback.answer("Сейчас не фаза боя.", show_alert=True)
        await _send_state(callback, state, run_id)
        return
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
    elif action == "run_tasks":
        state["phase"] = "run_tasks"
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
        if state.get("player", {}).get("second_chance"):
            await _offer_second_chance_owned(callback, run_id, state)
        else:
            await _offer_second_chance(callback, run_id, state)
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

@router.callback_query(F.data.startswith("second_chance:"))
async def second_chance_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state.get("phase") != "second_chance_offer":
        await callback.answer("Второй шанс сейчас недоступен.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    action = callback.data.split(":", 1)[1]
    offer_type = state.get("second_chance_offer_type", "buy")
    if action == "buy":
        if offer_type != "buy":
            await callback.answer("Сейчас можно только использовать амулет.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        if callback.from_user is None:
            return
        payload = f"stars_second_chance:{callback.from_user.id}:{run_id}"
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title="Амулет второго шанса",
            description="Мгновенно возрождает: 1 HP и полный запас ОД.",
            payload=payload,
            currency=STARS_CURRENCY,
            prices=[LabeledPrice(label="Второй шанс", amount=get_second_chance_price())],
            provider_token=STARS_PROVIDER_TOKEN,
        )
        await callback.answer()
        return

    if action == "use":
        if offer_type != "owned":
            await callback.answer("Амулета у вас нет.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        from bot.game.logic import apply_second_chance
        apply_second_chance(state, note="Амулет второго шанса спасает вас: 1 HP и полные ОД.", consume=True)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return

    if action == "decline":
        state["phase"] = "dead"
        state.pop("second_chance_offer_type", None)
        _append_death_log(state)
        await _finalize_run_after_death(callback, user_row[0], run_id, state)
        return

    await callback.answer("Неверное действие.", show_alert=True)

@router.callback_query(F.data.startswith("tutorial:"))
async def tutorial_menu_action(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    user_id = await db.ensure_user(user.id, user.username)
    action = callback.data.split(":", 1)[1] if callback.data else ""
    active = await db.get_active_tutorial(user_id)
    if action == "restart":
        state = new_tutorial_state()
        if active:
            run_id, _ = active
            await db.update_run(run_id, state)
        else:
            run_id = await db.create_tutorial_run(user_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "menu":
        if active:
            run_id, _ = active
            await db.finish_tutorial_run(run_id)
        await callback.answer()
        await _show_main_menu(callback)
        return
    await callback.answer("Неверное действие.", show_alert=True)




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

@router.callback_query(F.data.startswith("run_tasks:"))
async def run_tasks_action(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return

    active = await db.get_active_run(user_row[0])
    if not active:
        active = await db.get_active_tutorial(user_row[0])
    if not active:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback)
        return

    run_id, state = active
    if state.get("phase") != "run_tasks":
        await callback.answer("Сейчас не испытания.", show_alert=True)
        await _send_state(callback, state, run_id)
        return

    action = callback.data.split(":", 1)[1]
    if action == "back":
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
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
        active = await db.get_active_tutorial(user_row[0])
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
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "use_id" and len(parts) > 2:
        scroll_id = parts[2]
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            result = tutorial_use_scroll(state, scroll_id)
            if state.get("tutorial_failed") or result == "fail":
                alert = _pop_tutorial_alert(state)
                await db.update_run(run_id, state)
                await _answer_tutorial_alert(callback, alert)
                await _show_tutorial_failed(callback, state)
                return
            if state.get("tutorial_completed") or result == "complete":
                await _complete_tutorial(callback, user_row[0], run_id, state)
                return
            alert = _pop_tutorial_alert(state)
            await db.update_run(run_id, state)
            await _answer_tutorial_alert(callback, alert)
            await _send_state(callback, state, run_id)
            return
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
    if action == "duel_zone":
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            await callback.answer("Недоступно в обучении.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        use_duel_zone(state)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "rune_guard_shield":
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            await callback.answer("Недоступно в обучении.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        use_rune_guard_shield(state)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "rune_guard_throw":
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            await callback.answer("Недоступно в обучении.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        use_rune_guard_throw(state)
        await db.update_run(run_id, state)
        await callback.answer()
        await _send_state(callback, state, run_id)
        return
    if action == "hunter_trap":
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            await callback.answer("Недоступно в обучении.", show_alert=True)
            await _send_state(callback, state, run_id)
            return
        use_hunter_trap(state)
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
        state["phase"] = "tutorial" if state.get("tutorial") else "battle"
        if state.get("tutorial"):
            scrolls = state.get("player", {}).get("scrolls", [])
            scroll_id = scrolls[index].get("id") if index < len(scrolls) else None
            result = tutorial_use_scroll(state, scroll_id)
            if state.get("tutorial_failed") or result == "fail":
                alert = _pop_tutorial_alert(state)
                await db.update_run(run_id, state)
                await _answer_tutorial_alert(callback, alert)
                await _show_tutorial_failed(callback, state)
                return
            if state.get("tutorial_completed") or result == "complete":
                await _complete_tutorial(callback, user_row[0], run_id, state)
                return
            alert = _pop_tutorial_alert(state)
            await db.update_run(run_id, state)
            await _answer_tutorial_alert(callback, alert)
            await _send_state(callback, state, run_id)
            return
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
        if state.get("player", {}).get("second_chance"):
            await _offer_second_chance_owned(callback, run_id, state)
        else:
            await _offer_second_chance(callback, run_id, state)
        return

    await db.update_run(run_id, state)
    await callback.answer()
    await _send_state(callback, state, run_id)
