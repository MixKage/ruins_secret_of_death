from __future__ import annotations

from typing import Dict

DESPERATE_CHARGE_ACCURACY_BONUS = 0.25
DESPERATE_CHARGE_THRESHOLD_RATIO = 1 / 3

DEFAULT_CHARACTER_ID = "wanderer"
RUNE_GUARD_ID = "rune_guard"
BERSERK_ID = "berserk"
ASSASSIN_ID = "assassin"
HUNTER_ID = "hunter"
EXECUTIONER_ID = "executioner"
DUELIST_ID = "duelist"
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
BERSERK_MEAT_ACCURACY_BONUS = 0.30
ASSASSIN_HP_PENALTY = 4
ASSASSIN_ARMOR_PENALTY = 1.0
ASSASSIN_EVASION_BONUS = 0.10
ASSASSIN_ACCURACY_BONUS = 0.05
ASSASSIN_FULL_HP_BONUS = 0.40
ASSASSIN_BACKSTAB_BONUS = 0.20
ASSASSIN_ECHO_RATIO = 0.50
ASSASSIN_POTION_HP_BONUS = 2
HUNTER_HP_BONUS = 2
HUNTER_EVASION_BONUS = 0.05
HUNTER_ACCURACY_BONUS = 0.10
HUNTER_MARK_DAMAGE_BONUS = 0.25
HUNTER_FIRST_SHOT_BONUS = 0.10
EXECUTIONER_HP_BONUS = 4
EXECUTIONER_ARMOR_BONUS = 1.0
EXECUTIONER_EVASION_PENALTY = 0.05
EXECUTIONER_BLEED_DAMAGE_BONUS = 0.25
EXECUTIONER_BLEED_CHANCE_BONUS = 0.20
DUELIST_ARMOR_BONUS = 0.0
DUELIST_EVASION_BONUS = 0.10
DUELIST_ACCURACY_BONUS = 0.05
DUELIST_DUEL_DAMAGE_BONUS = 0.25
DUELIST_DUEL_ACCURACY_BONUS = 0.15
DUELIST_BLADE_PIERCE_BONUS = 0.25
DUELIST_ZONE_CHARGES = 2
DUELIST_ZONE_TURNS = 2
DUELIST_PARRY_REDUCTION = 0.30
DUELIST_PARRY_COUNTER_RATIO = 0.50
POTION_NAMING = {
    DEFAULT_CHARACTER_ID: {
        "noun_forms": ("зелье", "зелья", "зелий"),
        "noun_genitive_singular": "зелья",
        "noun_accusative": "зелье",
        "button_noun": "",
        "action_label": "Зелье",
        "menu_title": "Выбор зелья",
        "received_verb": "Получено",
        "no_match_adjective": "подходящего",
        "adjectives": {
            "potion_small": ("малое", "малых"),
            "potion_medium": ("среднее", "средних"),
            "potion_strong": ("сильное", "сильных"),
        },
    },
    EXECUTIONER_ID: {
        "noun_forms": ("вытяжка мученика", "вытяжки мученика", "вытяжек мученика"),
        "noun_genitive_singular": "вытяжки мученика",
        "noun_accusative": "вытяжку мученика",
        "button_noun": "вытяжка",
        "action_label": "Вытяжка",
        "menu_title": "Выбор вытяжки",
        "received_verb": "Получена",
        "no_match_adjective": "подходящей",
        "adjectives": {
            "potion_small": ("малая", "малых"),
            "potion_medium": ("средняя", "средних"),
            "potion_strong": ("сильная", "сильных"),
        },
    },
    BERSERK_ID: {
        "noun_forms": ("кусок мяса", "куска мяса", "кусков мяса"),
        "noun_genitive_singular": "куска мяса",
        "noun_accusative": "кусок мяса",
        "button_noun": "кусок",
        "action_label": "Кусок",
        "menu_title": "Выбор куска мяса",
        "received_verb": "Получено",
        "no_match_adjective": "подходящего",
        "adjectives": {
            "potion_small": ("малый", "малых"),
            "potion_medium": ("средний", "средних"),
            "potion_strong": ("большой", "больших"),
        },
    },
}

CHARACTERS = {
    DEFAULT_CHARACTER_ID: {
        "id": DEFAULT_CHARACTER_ID,
        "name": "Рыцарь",
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
            "Щит Рун: при окончании хода с 0 ОД броня +2 до конца хода врагов.",
            "Каменный Ответ: получив удар >25% HP, следующий удар игнорирует 30% брони.",
            "Стойкая Воля: на полном HP в начале хода +1 ОД (не выше капа).",
            "Рывок Чести: при HP ≤ 1/3 1-я атака в ход стоит 0 ОД и точность +25%.",
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
            "Неистовая живучесть: первый смертельный удар за игру отменяет смерть и полностью восстанавливает HP.",
            "Сытая ярость: после каждого куска мяса точность +30% на 1 ход.",
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
    HUNTER_ID: {
        "id": HUNTER_ID,
        "name": "Охотник",
        "description": [
            "HP +2, броня без изменений, уклонение +5%, точность +10%.",
            "Охотничья метка: первая атака по цели накладывает метку.",
            "Добыча: по цели с меткой урон +25%.",
            "Перенос метки: при убийстве цели метка переходит на случайного врага из первых ceil(N/2).",
            "Гон по следу: первое убийство за ход восстанавливает 1 ОД.",
            "Выверенный выстрел: первая атака в ход получает +10% точности.",
            "На последнем издыхании: при HP ≤ 1/3 точность 100%.",
        ],
    },
    EXECUTIONER_ID: {
        "id": EXECUTIONER_ID,
        "name": "Палач",
        "description": [
            "HP +4, броня +1, уклонение -5%, точность без изменений.",
            "Точность мясника: если оружие накладывает кровотечение, шанс +20% (макс. 100%).",
            "Вытяжка мученика: зелья лечения переименованы, сильные недоступны.",
            "Жатва: по кровоточащим целям урон +25%.",
            "Приговор: убийство кровоточащего врага лечит 5 HP (до 2 раз за ход).",
            "Натиск: если есть кровотечение, следующая атака в ход получает +1 ОД.",
            "На последнем издыхании: при HP ≤ 1/3 точность 100%.",
            "Цена смерти: после 3 ходов на последнем издыхании получает -10 HP.",
        ],
    },
    DUELIST_ID: {
        "id": DUELIST_ID,
        "name": "Дуэлянт",
        "description": [
            "HP без изменений, броня без изменений, уклонение +10%, точность +5%.",
            "Дуэль: при 1 живом враге урон +25% и точность +15%.",
            "Парирование: первый успешный удар врага в фазу снижает урон на 30% и контратакует на 50% предотвращенного урона.",
            "Клинок чести: первая атака в ход игнорирует 25% брони цели.",
            "Дуэльная зона: 2 заряда на этаж, при использовании на враге активирует эффект дуэли на 2 хода или до его смерти.",
            "На последнем издыхании: при HP ≤ 1/3 точность 100%.",
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


def _potion_terms(character_id: str | None) -> Dict:
    resolved = resolve_character_id(character_id)
    return POTION_NAMING.get(resolved, POTION_NAMING[DEFAULT_CHARACTER_ID])


def _russian_plural_index(count: int) -> int:
    if count % 10 == 1 and count % 100 != 11:
        return 0
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return 1
    return 2


def potion_action_label(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms.get("action_label", "Зелье")


def potion_menu_title(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms.get("menu_title", "Выбор зелья")


def potion_use_label(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms.get("noun_accusative", terms["noun_forms"][0])


def potion_noun_genitive_plural(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms["noun_forms"][2]


def potion_noun_plural(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms["noun_forms"][1]


def potion_noun_genitive_singular(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms.get("noun_genitive_singular", terms["noun_forms"][1])


def potion_received_verb(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    return terms.get("received_verb", "Получено")


def potion_no_match_message(character_id: str | None) -> str:
    terms = _potion_terms(character_id)
    adjective = terms.get("no_match_adjective", "подходящего")
    noun = potion_noun_genitive_singular(character_id)
    return f"Нет {adjective} {noun}."


def potion_empty_message(character_id: str | None) -> str:
    noun = potion_noun_genitive_plural(character_id)
    if noun:
        noun = noun[0].upper() + noun[1:]
    return f"{noun} нет."


def potion_label(character_id: str | None, potion_id: str, count: int = 1, title: bool = False) -> str:
    terms = _potion_terms(character_id)
    adjective = terms.get("adjectives", {}).get(potion_id, ("", ""))[0 if count == 1 else 1]
    if count == 1:
        noun = terms["noun_forms"][0]
    else:
        noun = terms["noun_forms"][_russian_plural_index(count)]
    label = f"{adjective} {noun}".strip()
    if title and label:
        label = label[0].upper() + label[1:]
    return label


def potion_label_with_count(character_id: str | None, potion_id: str, count: int) -> str:
    label = potion_label(character_id, potion_id, count=count)
    if count > 1:
        label = f"{count} {label}"
    return label


def potion_button_label(character_id: str | None, potion_id: str, title: bool = False) -> str:
    terms = _potion_terms(character_id)
    adjective = terms.get("adjectives", {}).get(potion_id, ("", ""))[0]
    noun = terms.get("button_noun", terms["noun_forms"][0])
    label = f"{adjective} {noun}".strip()
    if title and label:
        label = label[0].upper() + label[1:]
    return label


def potion_full_name(character_id: str | None, potion: Dict) -> str:
    potion_id = potion.get("id", "")
    label = potion_label(character_id, potion_id, title=True)
    heal = int(potion.get("heal", 0))
    ap_restore = int(potion.get("ap_restore", 0))
    if heal or ap_restore:
        return f"{label} (лечит {heal} HP и +{ap_restore} ОД)"
    return label


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
    if character_id == HUNTER_ID:
        player["hp_max"] = max(1, int(player.get("hp_max", 1)) + HUNTER_HP_BONUS)
        player["hp"] = min(player["hp_max"], int(player.get("hp", player["hp_max"])) + HUNTER_HP_BONUS)
        player["evasion"] = float(player.get("evasion", 0.0)) + HUNTER_EVASION_BONUS
        player["accuracy"] = float(player.get("accuracy", 0.0)) + HUNTER_ACCURACY_BONUS
        return
    if character_id == EXECUTIONER_ID:
        player["hp_max"] = max(1, int(player.get("hp_max", 1)) + EXECUTIONER_HP_BONUS)
        player["hp"] = min(player["hp_max"], int(player.get("hp", player["hp_max"])) + EXECUTIONER_HP_BONUS)
        player["armor"] = float(player.get("armor", 0.0)) + EXECUTIONER_ARMOR_BONUS
        player["evasion"] = float(player.get("evasion", 0.0)) - EXECUTIONER_EVASION_PENALTY
        return
    if character_id == DUELIST_ID:
        player["armor"] = float(player.get("armor", 0.0)) + DUELIST_ARMOR_BONUS
        player["evasion"] = float(player.get("evasion", 0.0)) + DUELIST_EVASION_BONUS
        player["accuracy"] = float(player.get("accuracy", 0.0)) + DUELIST_ACCURACY_BONUS
        return


def _is_rune_guard(state: Dict) -> bool:
    return state.get("character_id") == RUNE_GUARD_ID


def _is_berserk(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == BERSERK_ID


def _is_assassin(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == ASSASSIN_ID


def _is_hunter(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == HUNTER_ID


def _is_executioner(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == EXECUTIONER_ID


def _is_duelist(state: Dict) -> bool:
    return resolve_character_id(state.get("character_id")) == DUELIST_ID


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
    return (
        _is_default_character(state)
        or _is_hunter(state)
        or _is_executioner(state)
        or _is_duelist(state)
    ) and _is_last_breath(player)


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


def _hunter_mark_bonus(state: Dict, target: Dict) -> float:
    if _is_hunter(state) and target.get("hunter_mark"):
        return HUNTER_MARK_DAMAGE_BONUS
    return 0.0


def _hunter_first_shot_bonus(state: Dict) -> float:
    if _is_hunter(state):
        return HUNTER_FIRST_SHOT_BONUS
    return 0.0


def _executioner_damage_bonus(state: Dict, target: Dict) -> float:
    if _is_executioner(state) and target.get("bleed_turns", 0) > 0:
        return EXECUTIONER_BLEED_DAMAGE_BONUS
    return 0.0


def _duelist_duel_damage_bonus(state: Dict, duel_active: bool) -> float:
    if _is_duelist(state) and duel_active:
        return DUELIST_DUEL_DAMAGE_BONUS
    return 0.0


def _duelist_duel_accuracy_bonus(state: Dict, duel_active: bool) -> float:
    if _is_duelist(state) and duel_active:
        return DUELIST_DUEL_ACCURACY_BONUS
    return 0.0


def _duelist_blade_pierce_bonus(state: Dict, used: bool) -> float:
    if _is_duelist(state) and not used:
        return DUELIST_BLADE_PIERCE_BONUS
    return 0.0


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
