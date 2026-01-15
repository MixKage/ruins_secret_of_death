from __future__ import annotations

from typing import Dict

DESPERATE_CHARGE_ACCURACY_BONUS = 0.25
DESPERATE_CHARGE_THRESHOLD_RATIO = 1 / 3

DEFAULT_CHARACTER_ID = "wanderer"
RUNE_GUARD_ID = "rune_guard"
BERSERK_ID = "berserk"
ASSASSIN_ID = "assassin"
RUNE_GUARD_HP_BONUS = 6
RUNE_GUARD_ARMOR_BONUS = 1.0
RUNE_GUARD_EVASION_PENALTY = 0.05
RUNE_GUARD_SHIELD_BONUS = 2.0
RUNE_GUARD_RETRIBUTION_PIERCE = 0.3
RUNE_GUARD_RETRIBUTION_THRESHOLD = 0.25
RUNE_GUARD_AP_BONUS = 1
BERSERK_HP_BONUS = 10
BERSERK_ARMOR_PENALTY = 1.0
BERSERK_RAGE_TIERS = [
    ("Ярость I", 0.7, 0.10),
    ("Ярость II", 0.4, 0.25),
    ("Ярость III", 0.2, 0.45),
    ("Ярость IV", 0.0, 0.65),
]
ASSASSIN_HP_PENALTY = 4
ASSASSIN_ARMOR_PENALTY = 1.0
ASSASSIN_EVASION_BONUS = 0.10
ASSASSIN_ACCURACY_BONUS = 0.05
ASSASSIN_FULL_HP_BONUS = 0.40
ASSASSIN_BACKSTAB_BONUS = 0.20
ASSASSIN_ECHO_RATIO = 0.50
ASSASSIN_POTION_HP_BONUS = 2

CHARACTERS = {
    DEFAULT_CHARACTER_ID: {
        "id": DEFAULT_CHARACTER_ID,
        "name": "Странник руин",
        "description": [
            "Сбалансированный герой без особых эффектов.",
            "Последнее издыхание: при HP ≤ 1/3 точность 100%.",
            "Решимость: на полном здоровье урон +20%.",
        ],
    },
    RUNE_GUARD_ID: {
        "id": RUNE_GUARD_ID,
        "name": "Страж рун",
        "description": [
            "HP +6, броня +1, уклонение -5%.",
            "Рунический заслон: при окончании хода с 0 ОД броня +2 до конца хода врагов.",
            "Расплата камня: получив удар >25% HP, следующий удар игнорирует 30% брони.",
            "Ровное дыхание: на полном HP в начале хода +1 ОД (не выше капа).",
            "Отчаянный рывок: при HP ≤ 1/3 1-я атака в ход стоит 0 ОД и точность +25%.",
        ],
    },
    BERSERK_ID: {
        "id": BERSERK_ID,
        "name": "Берсерк",
        "description": [
            "HP +10, броня -1, уклонение без изменений.",
            "Кровавая ярость I (HP 70-100%): урон +10%.",
            "Кровавая ярость II (HP 40-69%): урон +25%.",
            "Кровавая ярость III (HP 20-39%): урон +45%.",
            "Кровавая ярость IV (HP 1-19%): урон +65%.",
            "Кровавая добыча: первое убийство за ход восстанавливает 1 ОД.",
            "Неистовая живучесть: первый смертельный удар за игру полностью восстанавливает HP.",
        ],
    },
    ASSASSIN_ID: {
        "id": ASSASSIN_ID,
        "name": "Ассасин",
        "description": [
            "HP -4, броня -1, уклонение +10%, точность +5%.",
            "Безупречный удар: при полном HP урон +40%.",
            "Последняя тень: при HP ≤ 1/3 игнор брони и уклонения цели.",
            "Эхо убийства: первое убийство за ход наносит 50% урона всем врагам.",
            "Клинок в спину: первая атака по цели с полным HP наносит +20% урона.",
            "Ядовитые настои: зелья дают +2 HP.",
        ],
    },
}


def get_character(character_id: str | None) -> Dict:
    if character_id in CHARACTERS:
        return CHARACTERS[character_id]
    return CHARACTERS[DEFAULT_CHARACTER_ID]


def resolve_character_id(character_id: str | None) -> str:
    chosen_id = character_id or DEFAULT_CHARACTER_ID
    if chosen_id not in CHARACTERS:
        return DEFAULT_CHARACTER_ID
    return chosen_id


def apply_character_starting_stats(player: Dict, character_id: str) -> None:
    if character_id == RUNE_GUARD_ID:
        player["hp_max"] += RUNE_GUARD_HP_BONUS
        player["hp"] += RUNE_GUARD_HP_BONUS
        player["armor"] += RUNE_GUARD_ARMOR_BONUS
        player["evasion"] = max(0.0, player["evasion"] - RUNE_GUARD_EVASION_PENALTY)
        return
    if character_id == BERSERK_ID:
        player["hp_max"] += BERSERK_HP_BONUS
        player["hp"] += BERSERK_HP_BONUS
        player["armor"] = float(player.get("armor", 0.0)) - BERSERK_ARMOR_PENALTY
        return
    if character_id == ASSASSIN_ID:
        player["hp_max"] = max(1, int(player.get("hp_max", 1)) - ASSASSIN_HP_PENALTY)
        player["hp"] = max(
            1,
            min(player["hp_max"], int(player.get("hp", player["hp_max"])) - ASSASSIN_HP_PENALTY),
        )
        player["armor"] = float(player.get("armor", 0.0)) - ASSASSIN_ARMOR_PENALTY
        player["evasion"] = float(player.get("evasion", 0.0)) + ASSASSIN_EVASION_BONUS
        player["accuracy"] = float(player.get("accuracy", 0.0)) + ASSASSIN_ACCURACY_BONUS
        return


def _is_rune_guard(state: Dict) -> bool:
    return state.get("character_id") == RUNE_GUARD_ID


def _is_berserk(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == BERSERK_ID


def _is_assassin(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == ASSASSIN_ID


def _is_default_character(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == DEFAULT_CHARACTER_ID


def _is_full_hp(player: Dict) -> bool:
    hp_max = int(player.get("hp_max", 0))
    if hp_max <= 0:
        return False
    return player.get("hp", 0) >= hp_max


def _has_resolve(state: Dict, player: Dict) -> bool:
    return _is_default_character(state) and _is_full_hp(player)


def _has_steady_breath(state: Dict, player: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == RUNE_GUARD_ID and _is_full_hp(player)


def _is_last_breath(player: Dict) -> bool:
    max_hp = max(1, int(player.get("hp_max", 1)))
    return player.get("hp", 0) <= max_hp * DESPERATE_CHARGE_THRESHOLD_RATIO


def _has_last_breath(state: Dict, player: Dict) -> bool:
    return _is_default_character(state) and _is_last_breath(player)


def _berserk_rage_state(state: Dict, player: Dict) -> tuple[str, float] | None:
    if not _is_berserk(state):
        return None
    hp_max = max(1, int(player.get("hp_max", 1)))
    hp = max(0, int(player.get("hp", 0)))
    if hp <= 0:
        return None
    ratio = hp / hp_max
    for name, min_ratio, bonus in BERSERK_RAGE_TIERS:
        if ratio >= min_ratio:
            return name, bonus
    name, _, bonus = BERSERK_RAGE_TIERS[-1]
    return name, bonus


def _berserk_damage_bonus(state: Dict, player: Dict) -> float:
    rage = _berserk_rage_state(state, player)
    if not rage:
        return 0.0
    return rage[1]


def _assassin_full_hp_bonus(state: Dict, player: Dict) -> float:
    if _is_assassin(state) and _is_full_hp(player):
        return ASSASSIN_FULL_HP_BONUS
    return 0.0


def _assassin_shadow_active(state: Dict, player: Dict) -> bool:
    return _is_assassin(state) and _is_last_breath(player)


def _assassin_backstab_bonus(state: Dict, target: Dict) -> float:
    if not _is_assassin(state):
        return 0.0
    hp = int(target.get("hp", 0))
    max_hp = int(target.get("max_hp", 0))
    if max_hp > 0 and hp >= max_hp:
        return ASSASSIN_BACKSTAB_BONUS
    return 0.0


def _assassin_echo_ratio(state: Dict) -> float:
    if _is_assassin(state):
        return ASSASSIN_ECHO_RATIO
    return 0.0


def _assassin_potion_bonus(state: Dict) -> int:
    if _is_assassin(state):
        return ASSASSIN_POTION_HP_BONUS
    return 0


def _is_desperate_charge(state: Dict, player: Dict | None = None) -> bool:
    if not _is_rune_guard(state):
        return False
    player = player or state.get("player", {})
    return _is_last_breath(player)


def _desperate_charge_accuracy_bonus(state: Dict, player: Dict) -> float:
    if _is_desperate_charge(state, player):
        return DESPERATE_CHARGE_ACCURACY_BONUS
    return 0.0


def is_desperate_charge_available(state: Dict) -> bool:
    player = state.get("player")
    if not player:
        return False
    return _is_desperate_charge(state, player) and not state.get("desperate_charge_used")
