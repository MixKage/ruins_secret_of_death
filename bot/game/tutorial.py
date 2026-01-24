from __future__ import annotations

import copy
from typing import Dict

from .combat_utils import _first_alive
from .characters import potion_use_label
from .common import _append_log
from .data import get_scroll_by_id, get_upgrade_by_id
from .effects import _apply_freeze
from .items import _add_potion, _add_scroll

TUTORIAL_TOTAL_STEPS = 10
TUTORIAL_SCENE_NAME = "Плац у казармы"
TUTORIAL_DEFAULT_CONFIG = {
    "player_hit": 6,
    "scroll_hit": 8,
    "enemy_hit": 8,
    "last_breath_hp": 9,
}
TUTORIAL_STEP_ACTIONS = {
    1: "info",
    2: "attack",
    3: "attack_all",
    4: "endturn",
    5: "potion",
    6: "scroll",
    7: "endturn",
    8: None,
    9: "attack",
    10: "attack",
}
TUTORIAL_STEP_PROMPTS = {
    1: "Нажмите «Справка», чтобы изучить противника.",
    2: "Атакуйте один раз (1 ОД).",
    3: "Используйте «Атаковать на все ОД».",
    4: "Завершите ход — враг ответит.",
    5: "Используйте малое зелье.",
    6: "Откройте инвентарь и примените ледяной свиток.",
    7: "Завершите ход — враг пропустит его.",
    9: "Атакуйте (1 ОД).",
    10: "Добейте врага ещё одной атакой.",
}
TUTORIAL_STEP_HINTS = {
    1: "Сначала нажмите «Справка».",
    2: "Сейчас нужна атака на 1 ОД.",
    3: "Нажмите «Атаковать на все ОД».",
    4: "Завершите ход.",
    5: "Используйте зелье, чтобы восстановиться.",
    6: "Нужно применить ледяной свиток из инвентаря.",
    7: "Завершите ход, чтобы увидеть эффект льда.",
    9: "Атакуйте врага (1 ОД).",
    10: "Добейте врага атакой (1 ОД).",
}


def new_tutorial_state() -> Dict:
    weapon = {
        "id": "tutorial_blade",
        "name": "Учебный клинок",
        "min_dmg": 6,
        "max_dmg": 6,
        "accuracy_bonus": 0.0,
        "splash_ratio": 0.0,
        "bleed_chance": 0.0,
        "bleed_damage": 0,
        "armor_pierce": 0.0,
        "min_floor": 1,
        "max_floor": 1,
        "level": 1,
    }
    potion = copy.deepcopy(get_upgrade_by_id("potion_small"))
    ice_scroll = copy.deepcopy(get_scroll_by_id("scroll_ice"))
    player = {
        "hp": 30,
        "hp_max": 30,
        "ap": 3,
        "ap_max": 3,
        "armor": 0.0,
        "accuracy": 0.7,
        "evasion": 0.05,
        "power": 0,
        "luck": 0.2,
        "weapon": weapon,
        "potions": [],
        "scrolls": [],
    }
    if potion:
        _add_potion(player, potion, count=1)
    if ice_scroll:
        _add_scroll(player, ice_scroll)
    enemy = {
        "id": "tutorial_recruit",
        "name": "Учебный рекрут у казармы",
        "hp": 34,
        "max_hp": 34,
        "attack": 8,
        "armor": 0.0,
        "armor_pierce": 0.0,
        "accuracy": 1.0,
        "evasion": 0.0,
        "always_hit": True,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "info": "Новобранец, отрабатывающий удары на плацу.",
        "danger": "учебный",
        "min_floor": 1,
        "max_floor": 1,
    }
    state = {
        "floor": 1,
        "phase": "tutorial",
        "tutorial": True,
        "tutorial_step": 1,
        "tutorial_scene": TUTORIAL_SCENE_NAME,
        "tutorial_config": dict(TUTORIAL_DEFAULT_CONFIG),
        "tutorial_flags": {},
        "desperate_charge_used": False,
        "player": player,
        "enemies": [enemy],
        "rewards": [],
        "treasure_reward": None,
        "event_options": [],
        "boss_artifacts": [],
        "show_info": False,
        "kills": {},
        "treasures_found": 0,
        "chests_opened": 0,
        "boss_defeated": False,
        "boss_kind": None,
        "boss_name": None,
        "boss_intro_lines": None,
        "hunter_trap_used": False,
        "hunter_trap_active": False,
        "rune_guard_shield_active": False,
        "rune_guard_shield_used": False,
        "rune_guard_throw_active": False,
        "rune_guard_throw_hits": 0,
        "cursed_ap_ratio": None,
        "log": [],
    }
    _append_log(state, "<b>Плац у казармы.</b> Вы готовитесь к первым ударам.")
    _tutorial_log_step_prompt(state)
    return state


def tutorial_expected_action(state: Dict) -> str | None:
    step = int(state.get("tutorial_step", 1))
    return TUTORIAL_STEP_ACTIONS.get(step)


def tutorial_prompt(state: Dict) -> str:
    step = int(state.get("tutorial_step", 1))
    return TUTORIAL_STEP_PROMPTS.get(step, "")


def tutorial_hint(state: Dict) -> str:
    step = int(state.get("tutorial_step", 1))
    return TUTORIAL_STEP_HINTS.get(step, "Следуйте подсказке.")


def _tutorial_log_step_prompt(state: Dict) -> None:
    prompt = tutorial_prompt(state)
    if not prompt:
        return
    flags = state.setdefault("tutorial_flags", {})
    step = int(state.get("tutorial_step", 1))
    if flags.get("last_prompt_step") == step:
        return
    _append_log(state, prompt)
    flags["last_prompt_step"] = step


def tutorial_force_endturn(state: Dict) -> bool:
    return bool(state.get("tutorial")) and tutorial_expected_action(state) == "endturn"


def tutorial_apply_action(state: Dict, action: str) -> str:
    if not state.get("tutorial"):
        return "ignored"
    if state.get("tutorial_failed"):
        return "fail"
    if action == "forfeit":
        return _tutorial_fail(state, "Вы сдались.")
    if action == "info":
        state["show_info"] = not state.get("show_info", False)
        if tutorial_expected_action(state) != "info":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        _tutorial_advance(state)
        return "continue"
    if action == "attack":
        if tutorial_expected_action(state) != "attack":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        return _tutorial_attack(state, hits=1)
    if action == "attack_all":
        if tutorial_expected_action(state) != "attack_all":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        return _tutorial_attack(state, hits=2, consume_all=True)
    if action == "endturn":
        if tutorial_expected_action(state) != "endturn":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        return _tutorial_end_turn(state)
    if action == "potion":
        if tutorial_expected_action(state) != "potion":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        return _tutorial_use_potion(state)
    if action == "inventory":
        if tutorial_expected_action(state) != "scroll":
            _append_log(state, f"<i>{tutorial_hint(state)}</i>")
            return "continue"
        state["phase"] = "inventory"
        return "continue"
    _append_log(state, f"<i>{tutorial_hint(state)}</i>")
    return "continue"


def tutorial_use_scroll(state: Dict, scroll_id: str | None) -> str:
    if not state.get("tutorial"):
        return "ignored"
    if tutorial_expected_action(state) != "scroll":
        _append_log(state, f"<i>{tutorial_hint(state)}</i>")
        return "continue"
    if scroll_id != "scroll_ice":
        _append_log(state, "<i>Нужен ледяной свиток.</i>")
        return "continue"
    player = state["player"]
    scrolls = player.get("scrolls", [])
    index = None
    for idx, scroll in enumerate(scrolls):
        if scroll.get("id") == scroll_id:
            index = idx
            break
    if index is None:
        _append_log(state, "<i>Свиток не найден.</i>")
        return "continue"
    scroll = scrolls.pop(index)
    player["ap"] = max(0, int(player.get("ap", 0)) - 1)
    config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
    damage = int(config.get("scroll_hit", 8))
    target = _first_alive(state.get("enemies", []))
    if target:
        target["hp"] = max(0, target["hp"] - damage)
        _apply_freeze(target)
        _append_log(
            state,
            f"Вы читаете {scroll['name']}: {target['name']} получает {damage} урона и скован льдом.",
        )
    _tutorial_advance(state)
    return _tutorial_check_completion(state)


def _tutorial_attack(state: Dict, hits: int, consume_all: bool = False) -> str:
    player = state["player"]
    config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
    damage = int(config.get("player_hit", 6))
    total_damage = damage * max(1, hits)
    target = _first_alive(state.get("enemies", []))
    if not target:
        return "continue"
    if consume_all:
        player["ap"] = 0
        _append_log(state, f"Вы атакуете на все ОД: {hits} удара по {damage} урона.")
    else:
        player["ap"] = max(0, int(player.get("ap", 0)) - 1)
        _append_log(state, f"Вы наносите {damage} урона по {target['name']}.")
    target["hp"] = max(0, target["hp"] - total_damage)
    _tutorial_advance(state)
    return _tutorial_check_completion(state)


def _tutorial_end_turn(state: Dict) -> str:
    player = state["player"]
    player["ap"] = int(player.get("ap_max", 1))
    step = int(state.get("tutorial_step", 1))
    enemy = _first_alive(state.get("enemies", []))
    if enemy is None:
        return "continue"
    config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
    if step == 4:
        damage = int(config.get("enemy_hit", 8))
        player["hp"] = max(0, player["hp"] - damage)
        _append_log(state, f"{enemy['name']} бьет вас на {damage} урона.")
        if player["hp"] <= 0:
            return _tutorial_fail(state, "Вы пали в учебной схватке.")
    elif step == 7:
        if enemy.get("skip_turns", 0) > 0:
            enemy["skip_turns"] = max(0, enemy.get("skip_turns", 0) - 1)
            _append_log(state, f"{enemy['name']} скован льдом и пропускает ход.")
        else:
            _append_log(state, f"{enemy['name']} замирает на месте.")
    _tutorial_advance(state)
    return _tutorial_check_completion(state)


def _tutorial_use_potion(state: Dict) -> str:
    player = state["player"]
    if not player.get("potions"):
        _append_log(state, "<i>Зелья закончились.</i>")
        return "continue"
    potion = player["potions"].pop()
    heal = int(potion.get("heal", 0))
    ap_restore = int(potion.get("ap_restore", 0))
    player["hp"] = min(int(player.get("hp_max", 0)), int(player.get("hp", 0)) + heal)
    player["ap"] = min(int(player.get("ap_max", 1)), int(player.get("ap", 0)) + ap_restore)
    label = potion_use_label(state.get("character_id"))
    _append_log(state, f"Вы используете {label}: +{heal} HP, +{ap_restore} ОД.")
    _tutorial_advance(state)
    return "continue"


def _tutorial_advance(state: Dict) -> None:
    step = int(state.get("tutorial_step", 1)) + 1
    state["tutorial_step"] = step
    if step == 8:
        _tutorial_enter_last_breath(state)
        state["tutorial_step"] = step + 1
    _tutorial_log_step_prompt(state)


def _tutorial_enter_last_breath(state: Dict) -> None:
    flags = state.setdefault("tutorial_flags", {})
    if flags.get("last_breath_shown"):
        return
    player = state.get("player", {})
    config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
    forced_hp = int(config.get("last_breath_hp", 9))
    player["hp"] = max(1, min(int(player.get("hp_max", 1)), forced_hp))
    _append_log(
        state,
        "<i>Удар наставника для демонстрации вашей силы снимает Вам 21 HP.</i>\n"
        "<b>Вы на последнем издыхании.</b> Когда Ваше HP ≤ 1/3 от максимального, точность становится 100%. "
        "Ваш стиль боя раскрывается именно здесь.",
    )
    flags["last_breath_shown"] = True


def _tutorial_check_completion(state: Dict) -> str:
    step = int(state.get("tutorial_step", 1))
    enemy = _first_alive(state.get("enemies", []))
    if step >= TUTORIAL_TOTAL_STEPS and (enemy is None or enemy.get("hp", 0) <= 0):
        state["tutorial_completed"] = True
        return "complete"
    return "continue"


def _tutorial_fail(state: Dict, reason: str) -> str:
    state["tutorial_failed"] = True
    state["tutorial_fail_reason"] = reason
    state["phase"] = "tutorial_failed"
    message = "<b>Обучение провалено.</b>"
    if reason:
        message = f"{message} {reason}"
    _append_log(state, message)
    return "fail"
