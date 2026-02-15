from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, BufferedInputFile, Message, LabeledPrice

from bot.game.characters import potion_action_label
from bot.game.logic import (
    count_potions,
    is_desperate_charge_available,
    render_state,
    tutorial_force_endturn,
)
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
from bot.handlers.stars import STARS_PROVIDER_TOKEN
from bot.handlers.helpers import is_admin_user
from bot.utils.telegram import edit_or_send, safe_edit_text
from bot.api_client import get_active_run as api_get_active_run
from bot.api_client import run_action as api_run_action
from bot.api_client import get_story_chapter as api_get_story_chapter
from bot.api_client import get_story_photo as api_get_story_photo

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

async def _send_story_chapter(bot, chat_id: int, chapter: int, max_chapter: int) -> None:
    response = await api_get_story_chapter(chapter)
    caption = response.get("caption", "")
    markup = story_nav_kb(chapter, max_chapter)
    if response.get("has_photo"):
        try:
            photo_bytes = await api_get_story_photo(chapter)
            photo = BufferedInputFile(photo_bytes, filename=f"h{chapter}.jpg")
            await bot.send_photo(chat_id, photo, caption=caption, reply_markup=markup, parse_mode="HTML")
            return
        except Exception:
            pass
    await bot.send_message(chat_id, caption, reply_markup=markup, parse_mode="HTML")

async def _send_tutorial_intro(bot, chat_id: int) -> None:
    response = await api_get_story_chapter(0)
    caption = response.get("caption", "")
    await bot.send_message(chat_id, caption, parse_mode="HTML")


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


async def _send_state(callback: CallbackQuery, state: dict) -> None:
    text = render_state(state)
    is_admin = is_admin_user(callback.from_user)
    markup = _markup_for_state(state, is_admin=is_admin)
    await edit_or_send(callback, text, reply_markup=markup)


async def _send_story_chapters_from_api(
    callback: CallbackQuery,
    chapters: list[int],
    max_chapter: int | None,
) -> None:
    if not chapters or not callback.from_user:
        return
    limit = max_chapter or max(chapters)
    for chapter in chapters:
        await _send_story_chapter(callback.bot, callback.from_user.id, chapter, limit)


async def _apply_api_action(callback: CallbackQuery, action: str) -> None:
    user = callback.from_user
    if user is None:
        return
    response = await api_run_action(
        user.id,
        user.username,
        action,
    )
    alert = response.get("alert")
    show_alert = bool(response.get("show_alert"))
    if alert:
        await callback.answer(alert, show_alert=show_alert)
    else:
        await callback.answer()

    status = response.get("status")
    state = response.get("state")
    run_id = response.get("run_id")

    if response.get("tutorial_intro") and callback.from_user:
        await _send_tutorial_intro(callback.bot, callback.from_user.id)

    if status == "state":
        if state is not None:
            await _send_state(callback, state)
        return

    if status == "tutorial_failed":
        if state is not None:
            await _show_tutorial_failed(callback, state)
        return

    if status == "tutorial_complete":
        text = response.get(
            "completion_text",
            (
                "<b>Учебный рекрут повержен.</b>\n"
                "Вы освоили ключевые механики Рыцаря и готовы к руинам.\n"
                "Совет: загляните в <b>Правила</b>, чтобы освежить детали."
            ),
        )
        if callback.message:
            await safe_edit_text(
                callback.message,
                text,
                reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
            )
        elif callback.from_user:
            await callback.bot.send_message(
                callback.from_user.id,
                text,
                reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
            )
        return

    if status == "summary":
        if state is not None:
            if callback.message:
                await safe_edit_text(callback.message, render_state(state), reply_markup=None)
            elif callback.from_user:
                await callback.bot.send_message(callback.from_user.id, render_state(state))
        summary_text = response.get("summary_text")
        if summary_text and callback.from_user:
            await callback.bot.send_message(callback.from_user.id, summary_text)
        await _send_story_chapters_from_api(
            callback,
            response.get("story_chapters") or [],
            response.get("story_max_chapter"),
        )
        if callback.from_user:
            await callback.bot.send_message(
                callback.from_user.id,
                "Главное меню",
                reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin_user(callback.from_user)),
            )
        return

    if status == "menu":
        await _send_story_chapters_from_api(
            callback,
            response.get("story_chapters") or [],
            response.get("story_max_chapter"),
        )
        menu_text = response.get("menu_text") or "Главное меню"
        await _show_main_menu(callback, text=menu_text)
        return

    if status == "invoice":
        invoice = response.get("invoice") or {}
        if callback.from_user:
            await callback.bot.send_invoice(
                chat_id=callback.from_user.id,
                title=invoice.get("title", "Оплата"),
                description=invoice.get("description", ""),
                payload=invoice.get("payload", ""),
                currency=invoice.get("currency", "XTR"),
                prices=[LabeledPrice(label=invoice.get("label", "Оплата"), amount=int(invoice.get("amount", 0)))],
                provider_token=STARS_PROVIDER_TOKEN,
            )
        return

    if status == "heroes_menu":
        await _send_story_chapters_from_api(
            callback,
            response.get("story_chapters") or [],
            response.get("story_max_chapter"),
        )
        target_user_id = response.get("user_id")
        if callback.from_user and target_user_id:
            await show_heroes_menu(callback, int(target_user_id), source="menu")
        return


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
    user = callback.from_user
    if user is None:
        return
    active = await api_get_active_run(user.id)
    run_id = active.get("run_id")
    state = active.get("state")
    kind = active.get("kind")
    if not run_id or not state:
        await callback.answer("Активных забегов нет.", show_alert=True)
        await _show_main_menu(callback, text="Нет активного забега.")
        return
    if kind == "tutorial":
        await callback.answer()
        if state.get("phase") == "tutorial_failed":
            await _show_tutorial_failed(callback, state)
        else:
            await _send_state(callback, state)
        return

    await callback.answer()
    await _send_state(callback, state)


@router.callback_query(F.data == "menu:new")
async def start_new_run(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, "menu:new")

@router.callback_query(F.data.startswith("hero:select:"))
async def select_character(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)


@router.message(Command("reset"))
async def reset_handler(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    active = await api_get_active_run(user.id)
    state = active.get("state")
    if not state:
        is_admin = is_admin_user(message.from_user)
        await message.answer("Активного забега нет.", reply_markup=main_menu_kb(has_active_run=False, is_admin=is_admin))
        return

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
    await _apply_api_action(callback, callback.data)



@router.callback_query(F.data.startswith("forfeit:"))
async def forfeit_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)

@router.callback_query(F.data.startswith("second_chance:"))
async def second_chance_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)

@router.callback_query(F.data.startswith("tutorial:"))
async def tutorial_menu_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)




@router.callback_query(F.data.startswith("potion:"))
async def potion_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)

@router.callback_query(F.data.startswith("run_tasks:"))
async def run_tasks_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)
@router.callback_query(F.data.startswith("inventory:"))
async def inventory_action(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)
@router.callback_query(F.data.startswith("treasure:"))
async def treasure_choice(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)


@router.callback_query(F.data.startswith("boss:"))
async def boss_artifact_choice(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)


@router.callback_query(F.data.startswith("reward:"))
async def reward_choice(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)


@router.callback_query(F.data.startswith("event:"))
async def event_choice(callback: CallbackQuery) -> None:
    await _apply_api_action(callback, callback.data)
