import copy
import random
from typing import Dict, List, Tuple

from .data import CHEST_LOOT, ENEMIES, SCROLLS, UPGRADES, WEAPONS, get_scroll_by_id, get_upgrade_by_id, get_weapon_by_id

MAX_LOG_LINES = 4
MESSAGE_LIMIT = 4096
INFO_TRUNCATED_LINE = "<i>Справка обрезана.</i>"
TREASURE_REWARD_XP = 5

ENEMY_DAMAGE_BUDGET_RATIO = 0.4
ENEMY_DAMAGE_BUDGET_RATIO_POST_BOSS = 0.6

LUCK_MAX = 0.7
FULL_HEALTH_DAMAGE_BONUS = 0.2

AP_MAX_BASE_CAP = 4
AP_MAX_STEP_PER_TIER = 2

ARMOR_CAP_BEFORE_50 = 4
ARMOR_CAP_BEFORE_100 = 6
EVASION_CAP_BEFORE_50 = 0.4
EVASION_CAP_BEFORE_100 = 0.8

POTION_LIMITS = {
    "potion_small": 10,
    "potion_medium": 5,
    "potion_strong": 2,
}

CURSED_FLOOR_MIN_FLOOR = 50
CURSED_AP_RATIO = 0.75
CURSED_FLOOR_CHANCE = 0.2

BOSS_FLOOR = 10
LATE_BOSS_FLOOR_STEP = 10
LATE_BOSS_NAME_FALLBACK = "Павший герой"
ULTIMATE_BOSS_FLOOR_STEP = 50
DAUGHTER_BOSS_NAME = "Дочь некроманта"
LATE_BOSS_SCALE_POWER = 0.12
LATE_BOSS_SCALE_ARMOR = 0.05
LATE_BOSS_SCALE_ACCURACY = 0.02
LATE_BOSS_SCALE_EVASION = 0.01
LATE_BOSS_MIN_TURNS = 4
LATE_BOSS_EVASION_PIERCE = 0.3
LATE_BOSS_GUARANTEED_HIT_EVERY = 2
DAUGHTER_BOSS_BASE_MULT = 1.5
DAUGHTER_BOSS_STEP_BONUS = 0.5
ENEMY_ARMOR_REDUCED_RATIO = 0.7
ENEMY_ARMOR_PIERCE_START_FLOOR = 50
ENEMY_ARMOR_PIERCE_BASE = 0.1
ENEMY_ARMOR_PIERCE_PER_FLOOR = 0.002
ENEMY_ARMOR_PIERCE_MAX = 0.2
EVASION_REDUCTION_START_FLOOR = 50
EVASION_REDUCTION_PER_FLOOR = 0.003
EVASION_REDUCTION_MAX = 0.25
MUTATED_NAME_PREFIX = "Мутированный"
MUTATED_NAME_PREFIX_LATE = "Оскверненный"
ELITE_TRAIT_SHADOW = "shadow_blade"
ELITE_TRAIT_STONE = "stone_skin"
ELITE_TRAIT_TRUE_STRIKE = "true_strike"
STONE_SKIN_ARMOR_BONUS = 1.0
STONE_SKIN_MAX_BONUS = 5.0
ELITE_NAME_PREFIX = "Проклятый"
SURVIVE_ONE_TURN_FLOOR = 50

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

BOSS_ARTIFACT_OPTIONS = [
    {
        "id": "artifact_power",
        "name": "Печать ярости",
        "effect": "+2 к урону",
    },
    {
        "id": "artifact_ap",
        "name": "Печать воли",
        "effect": "+1 к макс. ОД",
    },
    {
        "id": "artifact_potions",
        "name": "Алхимический набор",
        "effect": "2 средних зелья + случайный свиток",
    },
]

BOSS_INTRO_LINES = [
    "<b>Врата Некроманта</b>",
    "Вы ступаете в огромный зал, где воздух тяжел и липок от пепла.",
    "Факелы гаснут один за другим, а под сводами поднимается холод.",
    "В центре круга из соли и костей стоит <b>Некромант</b> — хозяин руин.",
    "Его голос звучит, как хор мертвых, и стены отвечают ему эхом.",
    "<i>Этот бой решит судьбу руин. Готовьтесь.</i>",
]

DAUGHTER_INTRO_LINES = [
    "<b>Зал Забытых Костей</b>",
    "Вы ощущаете, как древняя магия стягивает воздух в тугой узел.",
    "Из тьмы выходит дочь некроманта — та, ради кого он спускался в руины.",
    "Она давно испила зелье бессмертия, но душа не вернулась — осталась лишь пустая оболочка.",
    "В её взгляде нет света. Только голод и желание убивать.",
    "<i>Это не бой — это приговор. Выдержите.</i>",
]

def _append_log(state: Dict, message: str) -> None:
    state.setdefault("log", []).append(message)
    state["log"] = state["log"][-MAX_LOG_LINES:]

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))

def _percent(value: float, show_percent: bool = True) -> str:
    percent_value = int(round(value * 100))
    return f"{percent_value}%" if show_percent else str(percent_value)

def _trim_lines_to_limit(lines: List[str], limit: int) -> List[str]:
    if limit <= 0:
        return []
    result = []
    current_len = 0
    for line in lines:
        add_len = len(line) + (1 if result else 0)
        if current_len + add_len > limit:
            break
        result.append(line)
        current_len += add_len
    if len(result) < len(lines):
        trunc_line = INFO_TRUNCATED_LINE
        add_len = len(trunc_line) + (1 if result else 0)
        if current_len + add_len <= limit:
            result.append(trunc_line)
    return result

def _effective_ap_max(state: Dict) -> int:
    player = state.get("player", {})
    ap_max = max(1, int(player.get("ap_max", 1)))
    ratio = state.get("cursed_ap_ratio")
    if not ratio:
        return ap_max
    return max(1, int(ap_max * ratio))

def _apply_cursed_ap(state: Dict) -> bool:
    player = state.get("player", {})
    effective = _effective_ap_max(state)
    if player.get("ap", 0) > effective:
        player["ap"] = effective
        return True
    return False

def _roll_cursed_floor(floor: int) -> bool:
    if floor < CURSED_FLOOR_MIN_FLOOR:
        return False
    if is_any_boss_floor(floor):
        return False
    return random.random() < CURSED_FLOOR_CHANCE

def _has_trait(enemy: Dict, trait: str) -> bool:
    return trait in enemy.get("traits", [])

def _enemy_always_hits(enemy: Dict) -> bool:
    if enemy.get("always_hit"):
        return True
    if _has_trait(enemy, ELITE_TRAIT_TRUE_STRIKE):
        return True
    if _has_trait(enemy, ELITE_TRAIT_SHADOW):
        return True
    return False

def _enemy_guaranteed_hit_every(enemy: Dict) -> int:
    return int(enemy.get("guaranteed_hit_every", 0) or 0)

def _enemy_base_hit_chance(enemy: Dict, defender_evasion: float, floor: int | None) -> float:
    if _enemy_always_hits(enemy):
        return 1.0
    evasion = 0.0 if _has_trait(enemy, ELITE_TRAIT_TRUE_STRIKE) else defender_evasion
    evasion_pierce = float(enemy.get("evasion_pierce", 0.0))
    if evasion_pierce > 0:
        evasion = max(0.0, evasion * (1.0 - evasion_pierce))
    evasion = _effective_evasion(evasion, floor)
    return _clamp(enemy.get("accuracy", 0.0) - evasion, 0.15, 0.95)

def _enemy_expected_hit_chance(enemy: Dict, defender_evasion: float, floor: int | None) -> float:
    base = _enemy_base_hit_chance(enemy, defender_evasion, floor)
    guaranteed_every = _enemy_guaranteed_hit_every(enemy)
    if guaranteed_every > 0 and base < 1.0:
        base = min(1.0, base + (1.0 - base) / guaranteed_every)
    return base

def _apply_stone_skin(state: Dict, enemy: Dict) -> None:
    if not _has_trait(enemy, ELITE_TRAIT_STONE):
        return
    if enemy.get("hp", 0) <= 0:
        return
    base_armor = enemy.get("armor_base", enemy.get("armor", 0.0))
    max_armor = base_armor + STONE_SKIN_MAX_BONUS
    new_armor = min(max_armor, enemy.get("armor", 0.0) + STONE_SKIN_ARMOR_BONUS)
    if new_armor > enemy.get("armor", 0.0):
        enemy["armor"] = new_armor
        _append_log(state, f"{enemy['name']} каменеет: броня усиливается.")

def _magic_scroll_damage(player: Dict, ap_max: int | None = None) -> int:
    weapon = player.get("weapon", {})
    max_weapon = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    ap_value = int(ap_max if ap_max is not None else player.get("ap_max", 1))
    dmg = max_weapon * ap_value
    dmg = max(20, int(dmg))
    if _has_resolve(player):
        dmg = int(round(dmg * (1.0 + FULL_HEALTH_DAMAGE_BONUS)))
    return dmg

def _apply_burn(enemy: Dict, damage: int) -> None:
    enemy["burn_turns"] = max(enemy.get("burn_turns", 0), 1)
    enemy["burn_damage"] = max(enemy.get("burn_damage", 0), damage)




def _potion_stats(player: Dict, potion_id: str) -> Tuple[int, int]:
    for potion in player.get("potions", []):
        if potion.get("id") == potion_id:
            return int(potion.get("heal", 0)), int(potion.get("ap_restore", 0))
    fallback = get_upgrade_by_id(potion_id)
    if fallback:
        return int(fallback.get("heal", 0)), int(fallback.get("ap_restore", 0))
    return 0, 0

def count_potions(player: Dict, potion_id: str) -> int:
    return sum(1 for potion in player.get("potions", []) if potion.get("id") == potion_id)


def _potion_limit(potion_id: str) -> int:
    return POTION_LIMITS.get(potion_id, 999)


def _add_potion(player: Dict, potion: Dict | None, count: int = 1) -> Tuple[int, int]:
    if not potion or count <= 0:
        return 0, 0
    potion_id = potion.get("id")
    if not potion_id:
        for _ in range(count):
            player.setdefault("potions", []).append(copy.deepcopy(potion))
        return count, 0
    limit = _potion_limit(potion_id)
    current = count_potions(player, potion_id)
    space = max(0, limit - current)
    to_add = min(space, count)
    for _ in range(to_add):
        player.setdefault("potions", []).append(copy.deepcopy(potion))
    return to_add, count - to_add

def _fill_potions(player: Dict, ratio: float = 1.0) -> Dict[str, int]:
    added_counts: Dict[str, int] = {}
    for potion_id in ("potion_small", "potion_medium", "potion_strong"):
        limit = _potion_limit(potion_id)
        target = max(1, int(limit * ratio)) if limit > 0 else 0
        current = count_potions(player, potion_id)
        if current >= target:
            continue
        potion = copy.deepcopy(get_upgrade_by_id(potion_id))
        if not potion:
            continue
        to_add = target - current
        added, _ = _add_potion(player, potion, count=to_add)
        if added:
            added_counts[potion_id] = added
    return added_counts


def _add_scroll(player: Dict, scroll: Dict | None) -> Dict | None:
    if not scroll:
        return None
    if not isinstance(player.get("scrolls"), list):
        player["scrolls"] = []
    added = copy.deepcopy(scroll)
    player["scrolls"].append(added)
    return added


def _apply_freeze(enemy: Dict) -> None:
    enemy["skip_turns"] = max(enemy.get("skip_turns", 0), 1)



def _is_luck_maxed(player: Dict) -> bool:
    return player.get("luck", 0.0) >= LUCK_MAX


def _has_resolve(player: Dict) -> bool:
    hp_max = int(player.get("hp_max", 0))
    if hp_max <= 0:
        return False
    return player.get("hp", 0) >= hp_max


def _ap_max_cap_for_floor(floor: int) -> int:
    safe_floor = max(1, int(floor or 1))
    return AP_MAX_BASE_CAP + AP_MAX_STEP_PER_TIER * (safe_floor // 10)

def _armor_cap_for_floor(floor: int) -> int | None:
    safe_floor = max(1, int(floor or 1))
    if safe_floor < 50:
        return ARMOR_CAP_BEFORE_50
    if safe_floor < 100:
        return ARMOR_CAP_BEFORE_100
    return None

def _is_armor_capped(player: Dict, floor: int) -> bool:
    cap = _armor_cap_for_floor(floor)
    if cap is None:
        return False
    return player.get("armor", 0) >= cap

def _evasion_cap_for_floor(floor: int) -> float | None:
    safe_floor = max(1, int(floor or 1))
    if safe_floor < 50:
        return EVASION_CAP_BEFORE_50
    if safe_floor < 100:
        return EVASION_CAP_BEFORE_100
    return None

def _is_evasion_capped(player: Dict, floor: int) -> bool:
    cap = _evasion_cap_for_floor(floor)
    if cap is None:
        return False
    return player.get("evasion", 0.0) >= cap


def _is_ap_max_capped(player: Dict, floor: int) -> bool:
    return int(player.get("ap_max", 0)) >= _ap_max_cap_for_floor(floor)


def _enforce_ap_max_cap(player: Dict, floor: int) -> bool:
    cap = _ap_max_cap_for_floor(floor)
    current = int(player.get("ap_max", 0))
    if current <= cap:
        return False
    player["ap_max"] = cap
    if player.get("ap", 0) > cap:
        player["ap"] = cap
    return True

def enforce_ap_cap(state: Dict) -> bool:
    player = state.get("player")
    if not player:
        return False
    changed = _enforce_ap_max_cap(player, state.get("floor", 1))
    if _apply_cursed_ap(state):
        changed = True
    return changed


def _enemy_damage_budget_ratio(floor: int) -> float:
    base = ENEMY_DAMAGE_BUDGET_RATIO_POST_BOSS if floor > BOSS_FLOOR else ENEMY_DAMAGE_BUDGET_RATIO
    if floor > 20:
        steps = (floor - 20) // 10
        base += 0.1 * steps
    return min(base, 1.0)

def _enemy_armor_pierce_for_floor(floor: int) -> float:
    if floor <= ENEMY_ARMOR_PIERCE_START_FLOOR:
        return 0.0
    steps = floor - ENEMY_ARMOR_PIERCE_START_FLOOR
    pierce = ENEMY_ARMOR_PIERCE_BASE + ENEMY_ARMOR_PIERCE_PER_FLOOR * steps
    return min(ENEMY_ARMOR_PIERCE_MAX, pierce)

def _enemy_damage_to_player(enemy: Dict, player: Dict, floor: int | None = None) -> int:
    attack = float(enemy.get("attack", 0))
    armor = float(player.get("armor", 0))
    pierce = float(enemy.get("armor_pierce", 0.0))
    if floor is not None:
        pierce = max(pierce, _enemy_armor_pierce_for_floor(floor))
    reduced_portion = attack * ENEMY_ARMOR_REDUCED_RATIO
    bypass_portion = attack * (1.0 - ENEMY_ARMOR_REDUCED_RATIO)
    effective_armor = armor * (1.0 - pierce)
    reduced_damage = max(0.0, reduced_portion - effective_armor)
    total = reduced_damage + bypass_portion
    return max(1, int(round(total)))

def _effective_evasion(evasion: float, floor: int | None) -> float:
    if floor is None or floor < EVASION_REDUCTION_START_FLOOR:
        return evasion
    reduction = min(EVASION_REDUCTION_MAX, EVASION_REDUCTION_PER_FLOOR * (floor - EVASION_REDUCTION_START_FLOOR))
    return max(0.0, evasion * (1.0 - reduction))

def _is_last_breath(player: Dict, floor: int) -> bool:
    max_hp = max(1, int(player.get("hp_max", 1)))
    return player["hp"] <= max_hp / 3

def _grant_small_potion(player: Dict) -> Tuple[int, int]:
    potion = copy.deepcopy(get_upgrade_by_id("potion_small"))
    return _add_potion(player, potion, count=1)

def _grant_medium_potion(player: Dict, count: int = 1) -> Tuple[int, int]:
    potion = copy.deepcopy(get_upgrade_by_id("potion_medium"))
    return _add_potion(player, potion, count=count)




def _grant_strong_potion(player: Dict, count: int = 1) -> Tuple[int, int]:
    potion = copy.deepcopy(get_upgrade_by_id("potion_strong"))
    return _add_potion(player, potion, count=count)
def _grant_random_scroll(player: Dict) -> Dict | None:
    if not SCROLLS:
        return None
    scroll = random.choice(SCROLLS)
    return _add_scroll(player, scroll)

def _grant_lightning_scroll(player: Dict) -> Dict | None:
    scroll = copy.deepcopy(get_scroll_by_id("scroll_lightning"))
    return _add_scroll(player, scroll)

def _mutate_enemy_template(template: Dict, prefix: str, info_suffix: str) -> Dict:
    mutated = copy.deepcopy(template)
    name = mutated.get("name", "")
    traits = mutated.get("traits", [])
    if traits:
        prefix = f"{ELITE_NAME_PREFIX} "
        if not name.startswith(prefix):
            mutated["name"] = f"{ELITE_NAME_PREFIX} {name}"
    else:
        tag = f"{prefix} "
        if not name.startswith(tag):
            mutated["name"] = f"{prefix} {name}"
    mutated["base_hp"] = int(round(mutated.get("base_hp", 0) * 1.25))
    mutated["base_attack"] = mutated.get("base_attack", 0) * 1.2
    mutated["base_armor"] = mutated.get("base_armor", 0) * 1.1
    mutated["base_accuracy"] = _clamp(mutated.get("base_accuracy", 0.5) + 0.05, 0.4, 0.95)
    mutated["base_evasion"] = _clamp(mutated.get("base_evasion", 0.05) + 0.03, 0.02, 0.3)
    mutated["hp_per_floor"] = mutated.get("hp_per_floor", 0) * 1.15
    mutated["attack_per_floor"] = mutated.get("attack_per_floor", 0) * 1.2
    mutated["armor_per_floor"] = mutated.get("armor_per_floor", 0) * 1.15
    mutated["min_floor"] = max(int(template.get("min_floor", 1)), BOSS_FLOOR + 1)
    mutated["max_floor"] = 999
    info = mutated.get("info", "").strip()
    if traits:
        if info and "Элитный" not in info:
            mutated["info"] = f"{info} Элитный слуга проклятых руин."
        elif not info:
            mutated["info"] = "Элитный слуга проклятых руин."
    else:
        if info and info_suffix not in info:
            mutated["info"] = f"{info} {info_suffix}"
        elif not info:
            mutated["info"] = info_suffix
    return mutated

WEAPON_RARITY_TIERS = [
    (11, "Редкий"),
    (20, "Эпический"),
    (30, "Легендарный"),
    (40, "Мифический"),
    (50, "Древний"),
    (60, "Реликтовый"),
    (70, "Божественный"),
    (80, "Вечный"),
    (90, "Абсолютный"),
    (100, "Апокрифический"),
]

def _weapon_rarity_prefix(floor: int) -> str | None:
    prefix = None
    for min_floor, name in WEAPON_RARITY_TIERS:
        if floor >= min_floor:
            prefix = name
    return prefix

def _strip_rarity_prefix(name: str) -> str:
    for _, prefix in WEAPON_RARITY_TIERS:
        tag = f"{prefix} "
        if name.startswith(tag):
            return name[len(tag):]
    return name

def _enhanced_weapon(weapon: Dict, floor: int) -> Dict:
    enhanced = copy.deepcopy(weapon)
    if floor <= BOSS_FLOOR:
        return enhanced
    enhanced["min_dmg"] = enhanced.get("min_dmg", 0) + 2
    enhanced["max_dmg"] = enhanced.get("max_dmg", 0) + 3
    enhanced["accuracy_bonus"] = _clamp(enhanced.get("accuracy_bonus", 0.0) + 0.05, -0.2, 0.3)
    enhanced["splash_ratio"] = _clamp(enhanced.get("splash_ratio", 0.0) + 0.05, 0.0, 0.5)
    enhanced["bleed_chance"] = _clamp(enhanced.get("bleed_chance", 0.0) + 0.05, 0.0, 0.6)
    enhanced["bleed_damage"] = enhanced.get("bleed_damage", 0) + (1 if enhanced.get("bleed_chance", 0) > 0 else 0)
    enhanced["armor_pierce"] = _clamp(enhanced.get("armor_pierce", 0.0) + 0.05, 0.0, 0.6)
    prefix = _weapon_rarity_prefix(floor)
    if prefix:
        base_name = _strip_rarity_prefix(enhanced.get("name", ""))
        enhanced["name"] = f"{prefix} {base_name}".strip()
    return enhanced

def _filter_by_floor(items: List[Dict], floor: int) -> List[Dict]:
    filtered = []
    for item in items:
        min_floor = item.get("min_floor", 1)
        max_floor = item.get("max_floor", 999)
        if min_floor <= floor <= max_floor:
            filtered.append(item)
    return filtered

def _weapons_for_floor(floor: int) -> List[Dict]:
    if floor > BOSS_FLOOR:
        return [_enhanced_weapon(item, floor) for item in WEAPONS]
    weapons = _filter_by_floor(WEAPONS, floor)
    return weapons or WEAPONS

def _enemies_for_floor(floor: int) -> List[Dict]:
    if floor > BOSS_FLOOR:
        base_pool = [item for item in ENEMIES if item.get("id") != "necromancer"]
        if floor >= SURVIVE_ONE_TURN_FLOOR:
            prefix = MUTATED_NAME_PREFIX_LATE
            suffix = "Осквернен в глубине руин."
        else:
            prefix = MUTATED_NAME_PREFIX
            suffix = "Мутировал в глубине руин."
        mutated = [_mutate_enemy_template(item, prefix, suffix) for item in base_pool]
        filtered = _filter_by_floor(mutated, floor)
        return filtered or mutated
    enemies = _filter_by_floor(ENEMIES, floor)
    return enemies or ENEMIES

def _chest_loot_for_floor(floor: int) -> List[Dict]:
    filtered = []
    for item in CHEST_LOOT:
        min_floor = item.get("min_floor", 1)
        max_floor = item.get("max_floor", 999)
        if min_floor <= floor <= max_floor:
            filtered.append(item)
    return filtered



def _filter_chest_loot_for_player(pool: List[Dict], player: Dict | None, floor: int) -> List[Dict]:
    if not player:
        return pool
    filtered = pool
    if _is_luck_maxed(player):
        filtered = [item for item in filtered if not (item.get("type") == "upgrade" and item.get("id") == "lucky_amulet")]
    if _is_ap_max_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("type") == "upgrade" and item.get("id") == "stamina")]
    if _is_armor_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("type") == "upgrade" and item.get("id") == "plating")]
    if _is_evasion_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("type") == "upgrade" and item.get("id") == "agility")]
    return filtered


def _upgrades_for_floor(floor: int) -> List[Dict]:
    upgrades = _filter_by_floor(UPGRADES, floor)
    return upgrades or UPGRADES


def _filter_upgrades_for_player(upgrades: List[Dict], player: Dict | None, floor: int) -> List[Dict]:
    if not player:
        return upgrades
    filtered = upgrades
    if _is_luck_maxed(player):
        filtered = [item for item in filtered if not (item.get("stat") == "luck" or item.get("id") == "lucky_amulet")]
    if _is_ap_max_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("stat") == "ap_max" or item.get("id") == "stamina")]
    if _is_armor_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("stat") == "armor" or item.get("id") == "plating")]
    if _is_evasion_capped(player, floor):
        filtered = [item for item in filtered if not (item.get("stat") == "evasion" or item.get("id") == "agility")]
    return filtered

def scale_weapon_stats(weapon: Dict, floor: int) -> None:
    current_level = weapon.get("level", 1)
    if floor <= current_level:
        return
    increase = floor - current_level
    weapon["min_dmg"] += increase
    weapon["max_dmg"] += increase
    if weapon.get("bleed_damage"):
        weapon["bleed_damage"] += increase // 2
    weapon["level"] = floor

EVENT_OPTIONS = [
    {
        "id": "holy_spring",
        "name": "Источник благодати",
        "effect": "Полностью восстанавливает здоровье",
    },
    {
        "id": "treasure_chest",
        "name": "Сундук древних",
        "effect": "Шанс на награду +2 этажа или свиток магии + малое зелье",
    },
    {
        "id": "campfire",
        "name": "Костер паломника",
        "effect": "+2-3 к макс. HP + малое зелье",
    },
]

def is_boss_floor(floor: int) -> bool:
    return floor == BOSS_FLOOR

def is_ultimate_boss_floor(floor: int) -> bool:
    return floor >= ULTIMATE_BOSS_FLOOR_STEP and floor % ULTIMATE_BOSS_FLOOR_STEP == 0

def is_late_boss_floor(floor: int) -> bool:
    return floor > BOSS_FLOOR and floor % LATE_BOSS_FLOOR_STEP == 0 and not is_ultimate_boss_floor(floor)

def is_any_boss_floor(floor: int) -> bool:
    return is_boss_floor(floor) or is_late_boss_floor(floor) or is_ultimate_boss_floor(floor)

def generate_boss_artifacts() -> List[Dict]:
    return [copy.deepcopy(option) for option in BOSS_ARTIFACT_OPTIONS]

def build_boss(player: Dict) -> Dict:
    ap_max = int(player.get("ap_max", 2))
    potions = len(player.get("potions", []))
    ap_bonus = max(0, ap_max - 2)
    potion_bonus = min(potions, 5)
    scale = 1.0 + ap_bonus * 0.08 + potion_bonus * 0.04
    scale = _clamp(scale, 1.0, 1.4)

    hp_max = max(80, int(player["hp_max"] * 2.2 * scale))
    attack = max(12, int(player["hp_max"] * 0.35 * scale))
    armor = max(3.0, player.get("armor", 0) * 0.6 + 2.0 + ap_bonus * 0.2)
    accuracy = 0.78
    evasion = 0.08
    return {
        "id": "necromancer",
        "name": "Некромант",
        "hp": hp_max,
        "max_hp": hp_max,
        "attack": attack,
        "armor": armor,
        "accuracy": accuracy,
        "evasion": evasion,
        "always_hit": True,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "info": "Создатель проклятия. Его слова пусты, но воля крепка.",
        "danger": "легендарная",
        "min_floor": BOSS_FLOOR,
        "max_floor": BOSS_FLOOR,
    }

def build_fallen_boss_intro(boss_name: str) -> List[str]:
    return [
        f"Когда-то павший в этих руинах герой <b>{boss_name}</b> был поднят темной силой и идет в атаку на вас!",
    ]

def build_late_boss(player: Dict, floor: int, boss_name: str) -> Dict:
    steps = max(1, (floor - BOSS_FLOOR) // LATE_BOSS_FLOOR_STEP)
    weapon = player.get("weapon", {})
    max_hit = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    avg_hit = (int(weapon.get("min_dmg", 0)) + int(weapon.get("max_dmg", 0))) / 2 + int(player.get("power", 0))
    resolve_mult = 1.2 if _has_resolve(player) else 1.0
    turn_burst = max(1, max_hit * int(player.get("ap_max", 1)) * resolve_mult)

    hp_base = max(player.get("hp_max", 0) * 3.0, turn_burst * 1.8)
    min_turn_hp = turn_burst * (LATE_BOSS_MIN_TURNS - 1) + 1
    hp = int(max(hp_base, min_turn_hp) * (1.0 + 0.12 * steps))
    attack = int(max(player.get("hp_max", 0) * 0.33, 12) * (1.0 + 0.07 * steps))
    armor_pierce = weapon.get("armor_pierce", 0.0)
    armor = max(2.5, avg_hit * 0.25 / max(0.2, 1.0 - armor_pierce))
    accuracy = _clamp(0.78 + 0.015 * steps, 0.7, 0.92)
    evasion = _clamp(0.07 + 0.01 * steps, 0.05, 0.22)
    armor_pierce = _enemy_armor_pierce_for_floor(floor)

    return {
        "id": "fallen_hero",
        "name": boss_name,
        "hp": hp,
        "max_hp": hp,
        "attack": max(1, attack),
        "armor": armor,
        "armor_pierce": armor_pierce,
        "evasion_pierce": LATE_BOSS_EVASION_PIERCE,
        "guaranteed_hit_every": LATE_BOSS_GUARANTEED_HIT_EVERY,
        "guaranteed_hit_count": 0,
        "accuracy": accuracy,
        "evasion": evasion,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "info": "Павший авантюрист, поднятый темной силой. Частично игнорирует уклонение. Каждый третий удар неизбежен.",
        "danger": "легендарная",
        "min_floor": floor,
        "max_floor": floor,
    }

def build_daughter_boss(player: Dict, floor: int) -> Dict:
    steps = max(1, floor // ULTIMATE_BOSS_FLOOR_STEP)
    power_mult = DAUGHTER_BOSS_BASE_MULT + (steps - 1) * DAUGHTER_BOSS_STEP_BONUS
    weapon = player.get("weapon", {})
    max_hit = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    avg_hit = (int(weapon.get("min_dmg", 0)) + int(weapon.get("max_dmg", 0))) / 2 + int(player.get("power", 0))
    resolve_mult = 1.2 if _has_resolve(player) else 1.0
    burst = max_hit * int(player.get("ap_max", 1)) * resolve_mult

    hp_base = max(player.get("hp_max", 0) * 4.5, burst * 3.0, 2000)
    hp = int(hp_base * power_mult)
    player_hp_max = int(player.get("hp_max", 0))
    attack = int(max(player_hp_max * 0.45, 18) * power_mult)
    max_attack = max(1, int(player_hp_max * 0.6))
    attack = min(attack, max_attack)
    armor_pierce = weapon.get("armor_pierce", 0.0)
    armor = max(4.0, avg_hit * 0.35 / max(0.2, 1.0 - armor_pierce)) * power_mult
    accuracy = _clamp(0.85 + 0.02 * steps, 0.8, 0.97)
    evasion = _clamp(0.1 + 0.015 * steps, 0.08, 0.28)
    armor_pierce = _enemy_armor_pierce_for_floor(floor)

    return {
        "id": "necromancer_daughter",
        "name": DAUGHTER_BOSS_NAME,
        "hp": hp,
        "max_hp": hp,
        "attack": max(1, attack),
        "armor": armor,
        "armor_pierce": armor_pierce,
        "accuracy": accuracy,
        "evasion": evasion,
        "always_hit": True,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "info": "Дочь некроманта, лишенная души и ведомая жаждой убийства.",
        "danger": "легендарная",
        "min_floor": floor,
        "max_floor": floor,
    }

def new_run_state() -> Dict:
    weapon = copy.deepcopy(random.choice(_weapons_for_floor(1)))
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
        "power": 1,
        "luck": 0.2,
        "weapon": weapon,
        "potions": [],
        "scrolls": [],
    }
    if potion:
        _add_potion(player, potion, count=1)
    if ice_scroll:
        _add_scroll(player, ice_scroll)
    state = {
        "floor": 1,
        "phase": "battle",
        "player": player,
        "enemies": generate_enemy_group(1, player),
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
        "cursed_ap_ratio": None,
        "log": [],
    }
    _append_log(state, f"Вы нашли <b>{weapon['name']}</b> и спускаетесь на этаж <b>1</b>.")
    return state


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
    _append_log(state, f"Вы используете зелье: +{heal} HP, +{ap_restore} ОД.")
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

def _max_group_size_for_floor(floor: int) -> int:
    if floor <= 3:
        return 1
    if floor <= 6:
        return 2
    return 3

def generate_enemy_group(floor: int, player: Dict, ap_max_override: int | None = None) -> List[Dict]:
    enemies = _enemies_for_floor(floor)
    player_hp_max = max(1, int(player.get("hp_max", 1)))
    ap_source = ap_max_override if ap_max_override is not None else player.get("ap_max", 1)
    player_ap_max = max(1, int(ap_source))
    player_view = player
    if ap_max_override is not None and int(player.get("ap_max", 1)) != player_ap_max:
        player_view = dict(player)
        player_view["ap_max"] = player_ap_max
    max_group = _max_group_size_for_floor(floor)
    min_group = 1
    if floor > 11:
        if player_ap_max >= 5:
            min_group = 3
        elif player_ap_max >= 3:
            min_group = 2
    if floor > 20:
        min_group += (floor - 20) // 10
    if max_group < min_group:
        max_group = min_group
    attempts = 0
    budget = max(1, player_hp_max) * _enemy_damage_budget_ratio(floor)
    while attempts < 30:
        attempts += 1
        if max_group <= min_group:
            group_size = min_group
        else:
            group_size = random.randint(min_group, max_group)
        group = [build_enemy(random.choice(enemies), floor, player_view) for _ in range(group_size)]
        if _enemy_group_within_budget(group, budget):
            return _sort_elites_last(group)

    group = [build_enemy(random.choice(enemies), floor, player_view) for _ in range(min_group)]
    _scale_group_attack_to_budget(group, budget)
    return _sort_elites_last(group)

def _min_enemy_hp_after_full_turn(player: Dict, enemy: Dict) -> int:
    weapon = player.get("weapon", {})
    base = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    armor_pierce = weapon.get("armor_pierce", 0.0)
    armor = max(0.0, enemy.get("armor", 0.0) * (1.0 - armor_pierce))
    per_hit = max(1, int(base - armor))
    ap_max = max(1, int(player.get("ap_max", 1)))
    return per_hit * ap_max + 1

def _sort_elites_last(enemies: List[Dict]) -> List[Dict]:
    return sorted(enemies, key=lambda enemy: 1 if enemy.get("traits") else 0)

def build_enemy(template: Dict, floor: int, player: Dict | None = None) -> Dict:
    max_hp = int(template["base_hp"] + template["hp_per_floor"] * floor)
    attack = template["base_attack"] + template["attack_per_floor"] * floor
    armor = template["base_armor"] + template["armor_per_floor"] * floor
    accuracy = _clamp(template["base_accuracy"] + floor * 0.01, 0.4, 0.95)
    evasion = _clamp(template["base_evasion"] + floor * 0.005, 0.02, 0.3)
    traits = list(template.get("traits", []))
    armor_pierce = _enemy_armor_pierce_for_floor(floor)
    enemy = {
        "id": template["id"],
        "name": template["name"],
        "hp": max_hp,
        "max_hp": max_hp,
        "attack": attack,
        "armor": armor,
        "armor_pierce": armor_pierce,
        "armor_base": armor,
        "accuracy": accuracy,
        "evasion": evasion,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "traits": traits,
        "info": template.get("info", ""),
        "danger": template.get("danger", "неизвестна"),
        "min_floor": template.get("min_floor", 1),
        "max_floor": template.get("max_floor", 999),
    }
    if ELITE_TRAIT_SHADOW in traits:
        enemy["shadow_dodge_used"] = False
    if player and floor > SURVIVE_ONE_TURN_FLOOR:
        min_hp = _min_enemy_hp_after_full_turn(player, enemy)
        if enemy["hp"] < min_hp:
            enemy["hp"] = min_hp
            enemy["max_hp"] = min_hp
    return enemy

def _scale_group_attack_to_budget(enemies: List[Dict], budget: float) -> None:
    total_attack = sum(enemy["attack"] for enemy in enemies)
    if total_attack <= 0 or total_attack <= budget:
        return
    ratio = budget / total_attack
    for enemy in enemies:
        enemy["attack"] = max(1.0, enemy["attack"] * ratio)
    total_attack = sum(enemy["attack"] for enemy in enemies)
    overflow = total_attack - budget
    if overflow <= 0:
        return
    for enemy in sorted(enemies, key=lambda item: item["attack"], reverse=True):
        if overflow <= 0:
            break
        reducible = max(0.0, enemy["attack"] - 1.0)
        if reducible <= 0:
            continue
        delta = min(reducible, overflow)
        enemy["attack"] -= delta
        overflow -= delta

def _enemy_group_within_budget(enemies: List[Dict], budget: float) -> bool:
    if not enemies:
        return True
    total_attack = sum(enemy["attack"] for enemy in enemies)
    return total_attack <= budget

def roll_hit(attacker_accuracy: float, defender_evasion: float, floor: int | None = None) -> bool:
    effective_evasion = _effective_evasion(defender_evasion, floor)
    chance = _clamp(attacker_accuracy - effective_evasion, 0.15, 0.95)
    return random.random() < chance

def roll_damage(weapon: Dict, player: Dict, target: Dict) -> int:
    base = random.randint(weapon["min_dmg"], weapon["max_dmg"]) + player["power"]
    armor = max(0.0, target["armor"] * (1.0 - weapon["armor_pierce"]))
    reduced_portion = base * ENEMY_ARMOR_REDUCED_RATIO
    bypass_portion = base * (1.0 - ENEMY_ARMOR_REDUCED_RATIO)
    dmg = int(max(1, round(max(0.0, reduced_portion - armor) + bypass_portion)))
    if _has_resolve(player):
        dmg = max(1, int(round(dmg * (1.0 + FULL_HEALTH_DAMAGE_BONUS))))
    return dmg

def _alive_enemies(enemies: List[Dict]) -> List[Dict]:
    return [enemy for enemy in enemies if enemy["hp"] > 0]

def _tally_kills(state: Dict) -> None:
    kills = state.setdefault("kills", {})
    for enemy in state.get("enemies", []):
        if enemy["hp"] <= 0 and not enemy.get("counted_dead", False):
            enemy["counted_dead"] = True
            enemy_id = enemy.get("id", "unknown")
            kills[enemy_id] = kills.get(enemy_id, 0) + 1

def _first_alive(enemies: List[Dict]) -> Dict:
    for enemy in enemies:
        if enemy["hp"] > 0:
            return enemy
    return None

def _floor_range_label(min_floor: int, max_floor: int) -> str:
    if max_floor >= 999:
        return f"{min_floor}+"
    if min_floor == max_floor:
        return f"{min_floor}"
    return f"{min_floor}-{max_floor}"

def build_enemy_info_text(enemies: List[Dict], player: Dict | None = None, floor: int | None = None) -> str:
    alive = [enemy for enemy in enemies if enemy.get("hp", 0) > 0]
    if not alive:
        return "Справка недоступна: врагов нет."
    seen = set()
    lines = ["<b>Справка по противникам:</b>"]
    if player:
        lines.append("<i>Урон рассчитан с учетом ваших характеристик.</i>")
        if len(alive) > 1:
            total_expected = 0.0
            total_max = 0
            player_armor = player.get("armor", 0)
            player_evasion = player.get("evasion", 0.0)
            for enemy in alive:
                hit_damage = _enemy_damage_to_player(enemy, player, floor)
                hit_chance = _enemy_expected_hit_chance(enemy, player_evasion, floor)
                total_expected += hit_damage * hit_chance
                total_max += hit_damage
            total_display = max(1, int(round(total_expected)))
            lines.append(f"<b>Средний ожидаемый урон за ход:</b> {total_display}")
            lines.append(f"<b>Макс. урон при попадании всех:</b> {total_max}")
        elif len(alive) == 1:
            enemy = alive[0]
            hit_damage = _enemy_damage_to_player(enemy, player, floor)
            lines.append(f"<b>Макс. урон при попадании:</b> {hit_damage}")
    for enemy in alive:
        enemy_id = enemy.get("id")
        if enemy_id in seen:
            continue
        seen.add(enemy_id)
        danger = enemy.get("danger", "неизвестна")
        info = enemy.get("info", "").strip()
        min_floor = int(enemy.get("min_floor", 1))
        max_floor = int(enemy.get("max_floor", 999))
        floors = _floor_range_label(min_floor, max_floor)
        attack = int(round(enemy.get("attack", 0)))
        enemy_armor = enemy.get("armor", 0)
        enemy_armor_display = int(round(enemy_armor))
        if player:
            weapon = player.get("weapon", {})
            hit_damage = _enemy_damage_to_player(enemy, player, floor)
            player_accuracy = player.get("accuracy", 0.0) + weapon.get("accuracy_bonus", 0.0)
            enemy_evasion = _effective_evasion(enemy.get("evasion", 0.0), floor)
            if floor is not None and _is_last_breath(player, floor):
                hit_chance = 1.0
            else:
                hit_chance = _clamp(player_accuracy - enemy_evasion, 0.15, 0.95)
            hit_chance_pct = int(round(hit_chance * 100))
            if _enemy_always_hits(enemy):
                damage_text = (
                    f"<b>Урон противника:</b> {hit_damage} | "
                    "<b>Промах невозможен</b>"
                )
            else:
                damage_text = (
                    f"<b>Урон противника:</b> {hit_damage} | "
                    f"<b>Шанс попадания по врагу:</b> {hit_chance_pct}%"
                )
            evasion_pierce = float(enemy.get("evasion_pierce", 0.0))
            if evasion_pierce > 0:
                pierce_pct = int(round(evasion_pierce * 100))
                damage_text = f"{damage_text} | <b>Игнор уклонения:</b> {pierce_pct}%"
            armor_pierce = weapon.get("armor_pierce", 0.0)
            pierce_pct = int(round(armor_pierce * 100))
            if pierce_pct > 0:
                effective_armor = enemy_armor * (1.0 - armor_pierce)
                effective_armor_display = int(round(effective_armor))
                armor_text = (
                    f"Броня: <b>{enemy_armor_display}</b> "
                    f"(эффективная {effective_armor_display}, бронепробой {pierce_pct}%)"
                )
            else:
                armor_text = f"Броня: <b>{enemy_armor_display}</b>"
        else:
            damage_text = f"<b>Урон:</b> {attack}"
            armor_text = f"Броня: <b>{enemy_armor_display}</b>"
        info_text = f"<i>{info}</i> " if info else ""
        lines.append(
            f"- <b>{enemy['name']}</b>: {info_text}"
            f"{damage_text}. {armor_text}. Опасность: <b>{danger}</b>. Этажи: <i>{floors}</i>."
        )
    return "\n".join(lines)

def end_turn(state: Dict) -> None:
    if state["phase"] != "battle":
        return
    player = state["player"]
    _enforce_ap_max_cap(player, state["floor"])
    player["ap"] = _effective_ap_max(state)
    enemy_phase(state)
    _tally_kills(state)
    check_battle_end(state)

def player_attack(state: Dict, log_kills: bool = True) -> None:
    player = state["player"]
    if player["ap"] <= 0:
        _append_log(state, "Нет ОД для атаки.")
        return

    player["ap"] -= 1
    weapon = player["weapon"]
    target = _first_alive(state["enemies"])
    if target is None:
        return

    alive_before = len(_alive_enemies(state["enemies"]))

    last_breath = _is_last_breath(player, state["floor"])
    shadow_evaded = False
    if _has_trait(target, ELITE_TRAIT_SHADOW) and not target.get("shadow_dodge_used"):
        target["shadow_dodge_used"] = True
        shadow_evaded = True
        hit = False
    else:
        hit = True if last_breath else roll_hit(
            player["accuracy"] + weapon["accuracy_bonus"],
            target["evasion"],
            state.get("floor"),
        )
    if hit:
        damage = roll_damage(weapon, player, target)
        target["hp"] -= damage
        _append_log(state, f"Вы наносите {damage} урона по {target['name']}.")
        _apply_stone_skin(state, target)

        if weapon["splash_ratio"] > 0:
            splash_targets = [enemy for enemy in state["enemies"] if enemy is not target and enemy["hp"] > 0]
            if splash_targets:
                splash_damage = max(1, int(damage * weapon["splash_ratio"]))
                hit_targets = splash_targets[:3]
                for enemy in hit_targets:
                    enemy["hp"] -= splash_damage
                    _apply_stone_skin(state, enemy)
                _append_log(state, f"Сплэш урон: {splash_damage} по {len(hit_targets)} врагам.")

        if weapon["bleed_chance"] > 0 and random.random() < weapon["bleed_chance"]:
            target["bleed_turns"] = max(target["bleed_turns"], 2)
            target["bleed_damage"] = max(target["bleed_damage"], weapon["bleed_damage"])
            _append_log(state, f"{target['name']} истекает кровью.")
    else:
        if shadow_evaded:
            _append_log(state, f"{target['name']} растворяется в тени и избегает удара.")
        else:
            _append_log(state, "Вы промахиваетесь.")

    check_battle_end(state)

    if log_kills and alive_before > 3:
        alive_after = len(_alive_enemies(state["enemies"]))
        killed = max(0, alive_before - alive_after)
        _append_log(state, f"Побеждено врагов за ход: {killed}.")

def player_use_potion(state: Dict) -> None:
    player = state["player"]
    if not player["potions"]:
        _append_log(state, "Зелий нет.")
        return

    potion = player["potions"].pop()
    player["hp"] = min(player["hp_max"], player["hp"] + potion["heal"])
    player["ap"] = min(_effective_ap_max(state), player["ap"] + potion["ap_restore"])
    _append_log(state, f"Вы используете зелье: +{potion['heal']} HP, +{potion['ap_restore']} ОД.")

    check_battle_end(state)

def player_use_potion_by_id(state: Dict, potion_id: str) -> None:
    player = state["player"]
    potions = player.get("potions", [])
    for idx, potion in enumerate(potions):
        if potion.get("id") == potion_id:
            potion = potions.pop(idx)
            player["hp"] = min(player["hp_max"], player["hp"] + potion["heal"])
            player["ap"] = min(_effective_ap_max(state), player["ap"] + potion["ap_restore"])
            _append_log(state, f"Вы используете зелье: +{potion['heal']} HP, +{potion['ap_restore']} ОД.")
            check_battle_end(state)
            return
    _append_log(state, "Нет подходящего зелья.")


def player_use_scroll(state: Dict, scroll_index: int) -> None:
    player = state["player"]
    if not isinstance(player.get("scrolls"), list):
        player["scrolls"] = []
    scrolls = player.get("scrolls", [])
    if player["ap"] <= 0:
        _append_log(state, "Нет ОД для использования свитка.")
        return
    if scroll_index < 0 or scroll_index >= len(scrolls):
        _append_log(state, "Свиток не найден.")
        return
    target = _first_alive(state["enemies"])
    if target is None:
        _append_log(state, "Некого поражать магией.")
        return

    scroll = scrolls.pop(scroll_index)
    player["ap"] -= 1
    damage = _magic_scroll_damage(player, ap_max=_effective_ap_max(state))
    element = scroll.get("element")

    if element == "lightning":
        targets = _alive_enemies(state["enemies"])
        for enemy in targets:
            enemy["hp"] -= damage
            _apply_stone_skin(state, enemy)
        _append_log(state, f"Вы читаете {scroll['name']}: молнии бьют по всем врагам на {damage} урона.")
    elif element == "ice":
        target["hp"] -= damage
        _apply_stone_skin(state, target)
        _apply_freeze(target)
        _append_log(state, f"Вы читаете {scroll['name']}: {target['name']} получает {damage} урона и скован льдом.")
    else:
        target["hp"] -= damage
        _apply_stone_skin(state, target)
        _apply_burn(target, damage)
        _append_log(state, f"Вы читаете {scroll['name']}: {target['name']} получает {damage} урона и горит.")

    check_battle_end(state)

def enemy_phase(state: Dict) -> None:
    player = state["player"]
    enemies = _alive_enemies(state["enemies"])
    total_damage = 0

    for enemy in list(enemies):
        if enemy["bleed_turns"] > 0:
            enemy["hp"] -= enemy["bleed_damage"]
            enemy["bleed_turns"] -= 1
            _append_log(state, f"{enemy['name']} теряет {enemy['bleed_damage']} HP от кровотечения.")
        if enemy.get("burn_turns", 0) > 0:
            enemy["hp"] -= enemy.get("burn_damage", 0)
            enemy["burn_turns"] -= 1
            _append_log(state, f"{enemy['name']} горит и теряет {enemy.get('burn_damage', 0)} HP.")

    _tally_kills(state)
    enemies = _alive_enemies(state["enemies"])
    if not enemies:
        return
    group_size = len(enemies)

    for enemy in enemies:
        if enemy.get("skip_turns", 0) > 0:
            enemy["skip_turns"] -= 1
            _append_log(state, f"{enemy['name']} скован льдом и пропускает ход.")
            continue
        floor = state.get("floor")
        guaranteed_every = _enemy_guaranteed_hit_every(enemy)
        if guaranteed_every > 0:
            counter = int(enemy.get("guaranteed_hit_count", 0)) + 1
            enemy["guaranteed_hit_count"] = counter
            if counter % guaranteed_every == 0:
                hit = True
            else:
                hit = random.random() < _enemy_base_hit_chance(enemy, player["evasion"], floor)
        else:
            hit = random.random() < _enemy_base_hit_chance(enemy, player["evasion"], floor)
        if hit:
            damage = _enemy_damage_to_player(enemy, player, state.get("floor", 1))
            player["hp"] -= damage
            total_damage += damage
            _append_log(state, f"{enemy['name']} бьет вас на {damage} урона.")
        else:
            _append_log(state, f"{enemy['name']} промахивается.")
        if player["hp"] <= 0:
            player["hp"] = 0
            state["phase"] = "dead"
            _append_log(state, "<b>Вы падаете без сознания.</b> Забег окончен.")
            return

    if state["phase"] == "battle" and group_size > 1 and total_damage > 0:
        _append_log(state, f"Суммарный урон от врагов: {total_damage}.")

def check_battle_end(state: Dict) -> None:
    if state["phase"] == "dead":
        return
    _tally_kills(state)
    if not _alive_enemies(state["enemies"]):
        if state.get("floor") == BOSS_FLOOR and any(enemy.get("id") == "necromancer" for enemy in state.get("enemies", [])):
            state["boss_defeated"] = True
            _append_log(state, "<b>Некромант пал.</b> Руины на миг затихли.")
            _append_log(state, "Но зелье вечной жизни все еще не найдено — путь продолжается.")
        elif state.get("boss_kind") == "daughter":
            _append_log(state, "<b>Дочь некроманта повержена.</b> Но тьма в руинах не рассеивается.")
            player = state["player"]
            player["hp_max"] += 5
            player["hp"] += 5
            _append_log(state, "Награда: <b>+5</b> к макс. HP.")
            state["treasure_xp"] = state.get("treasure_xp", 0) + 10
            _append_log(state, "Награда: <b>+10 XP</b>.")
            added = _fill_potions(state["player"], ratio=0.5)
            if added:
                _append_log(state, "Запас зелий пополнен до половины.")
            else:
                _append_log(state, "Запас зелий уже полон.")
            scroll = _grant_lightning_scroll(state["player"])
            if scroll:
                _append_log(state, f"Получен свиток: <b>{scroll['name']}</b>.")
        elif state.get("boss_kind") == "fallen":
            boss_name = state.get("boss_name") or LATE_BOSS_NAME_FALLBACK
            _append_log(state, f"<b>{boss_name}</b> повержен. Руины снова молчат.")
            player = state["player"]
            player["hp_max"] += 5
            player["hp"] += 5
            _append_log(state, "Награда: <b>+5</b> к макс. HP.")
            added, dropped = _grant_strong_potion(state["player"], count=1)
            if added:
                _append_log(state, "Награда: <b>сильное зелье</b>.")
            if dropped:
                _append_log(state, "Нет места для зелий — награда сгорает.")
        state["phase"] = "reward"
        state["rewards"] = generate_rewards(state["floor"], state.get("player"))
        _append_log(state, f"<b>Этаж {state['floor']}</b> зачищен. Выберите награду.")

def generate_event_options() -> List[Dict]:
    return [copy.deepcopy(option) for option in EVENT_OPTIONS]

def _event_options_for_floor(floor: int) -> List[Dict]:
    options = generate_event_options()
    if floor < CURSED_FLOOR_MIN_FLOOR:
        return options
    for option in options:
        if option.get("id") == "holy_spring":
            option["effect"] = "Полностью восстанавливает здоровье + малое зелье"
        elif option.get("id") == "treasure_chest":
            option["effect"] = "Шанс на награду +2 этажа или свиток магии + малое и среднее зелье"
        elif option.get("id") == "campfire":
            option["effect"] = "+2-3 к макс. HP + малое и среднее зелье"
    return options

def _build_chest_reward(floor: int, player: Dict | None = None) -> Dict | None:
    pool = _filter_chest_loot_for_player(_chest_loot_for_floor(floor), player, floor)
    if not pool:
        return None
    entry = copy.deepcopy(random.choice(pool))
    item_type = entry.get("type")
    item_id = entry.get("id")
    if item_type == "weapon":
        weapon = copy.deepcopy(get_weapon_by_id(item_id))
        if not weapon:
            return None
        if floor > BOSS_FLOOR:
            weapon = _enhanced_weapon(weapon, floor)
        scale_weapon_stats(weapon, floor)
        return {"type": "weapon", "item": weapon}
    if item_type == "upgrade":
        upgrade = copy.deepcopy(get_upgrade_by_id(item_id))
        if not upgrade:
            return None
        return {"type": "upgrade", "item": upgrade}
    if item_type == "scroll":
        scroll = copy.deepcopy(get_scroll_by_id(item_id))
        if not scroll:
            return None
        return {"type": "scroll", "item": scroll}
    return None

def generate_rewards(floor: int, player: Dict | None = None) -> List[Dict]:
    rewards = []
    used_ids = set()
    upgrades = _filter_upgrades_for_player(_upgrades_for_floor(floor), player, floor)
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [
        ("upgrade", item) for item in upgrades
    ]
    while len(rewards) < 3 and pool:
        reward_type, item = random.choice(pool)
        item_id = item["id"]
        if item_id in used_ids:
            continue
        used_ids.add(item_id)
        reward_item = copy.deepcopy(item)
        if reward_type == "weapon":
            scale_weapon_stats(reward_item, floor)
        rewards.append({"type": reward_type, "item": reward_item})
    return rewards

def generate_single_reward(floor: int, player: Dict | None = None) -> Dict:
    upgrades = _filter_upgrades_for_player(_upgrades_for_floor(floor), player, floor)
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [
        ("upgrade", item) for item in upgrades
    ]
    reward_type, item = random.choice(pool)
    reward_item = copy.deepcopy(item)
    if reward_type == "weapon":
        scale_weapon_stats(reward_item, floor)
    return {"type": reward_type, "item": reward_item}

def apply_reward_item(state: Dict, reward: Dict) -> bool:
    player = state["player"]
    if reward["type"] == "weapon":
        player["weapon"] = reward["item"]
        _append_log(state, f"Вы берете оружие: <b>{reward['item']['name']}</b>.")
        return True
    if reward["type"] == "upgrade":
        upgrade = reward["item"]
        if upgrade["type"] == "stat":
            stat = upgrade["stat"]
            if stat == "luck":
                if _is_luck_maxed(player):
                    _append_log(state, "Удача уже на максимуме.")
                    return False
                player["luck"] = _clamp(player.get("luck", 0.0) + upgrade["amount"], 0.0, LUCK_MAX)
                _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
                return True
            if stat == "ap_max":
                cap = _ap_max_cap_for_floor(state.get("floor", 1))
                current = int(player.get("ap_max", 0))
                if current >= cap:
                    _append_log(state, "Максимум ОД на этом этаже уже достигнут.")
                    return False
                new_value = current + upgrade["amount"]
                if new_value > cap:
                    new_value = cap
                player["ap_max"] = new_value
                if player.get("ap", 0) > new_value:
                    player["ap"] = new_value
                _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
                return True
            if stat == "armor":
                cap = _armor_cap_for_floor(state.get("floor", 1))
                current = player.get("armor", 0)
                if cap is not None and current >= cap:
                    _append_log(state, "Броня уже достигла максимума для этого этажа.")
                    return False
                new_value = current + upgrade["amount"]
                if cap is not None and new_value > cap:
                    new_value = cap
                player["armor"] = new_value
                _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
                return True
            if stat == "evasion":
                cap = _evasion_cap_for_floor(state.get("floor", 1))
                current = player.get("evasion", 0.0)
                if cap is not None and current >= cap:
                    _append_log(state, "Уклонение уже достигло максимума для этого этажа.")
                    return False
                new_value = current + upgrade["amount"]
                if cap is not None and new_value > cap:
                    new_value = cap
                player["evasion"] = new_value
                _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
                return True
            player[stat] = player.get(stat, 0) + upgrade["amount"]
            if stat == "hp_max":
                player["hp"] = min(player["hp_max"], player["hp"] + upgrade["amount"])
            _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
            return True
        if upgrade["type"] == "potion":
            added, dropped = _add_potion(player, upgrade, count=1)
            if added:
                _append_log(state, f"Получено зелье: <b>{upgrade['name']}</b>.")
            if dropped:
                _append_log(state, "Нет места для зелий — находка сгорает.")
            return True
    if reward["type"] == "scroll":
        scroll = _add_scroll(player, reward["item"])
        if scroll:
            _append_log(state, f"Получен свиток: <b>{scroll['name']}</b>.")
            return True
        return False
    return False


def prepare_event(state: Dict) -> None:
    last_event_id = state.get("last_event_id")
    state["phase"] = "event"
    options = _event_options_for_floor(state.get("floor", 1))
    if last_event_id in {"treasure_chest", "campfire"}:
        options = [option for option in options if option.get("id") != last_event_id]
    state["event_options"] = options
    state["treasure_reward"] = None
    state["boss_artifacts"] = []
    state["show_info"] = False
    _append_log(state, "Между этажами вы находите <b>развилку</b>.")

def apply_reward(state: Dict, reward_index: int) -> None:
    rewards = state.get("rewards", [])
    if reward_index < 0 or reward_index >= len(rewards):
        _append_log(state, "Неверный выбор награды.")
        return

    reward = rewards[reward_index]
    if not apply_reward_item(state, reward):
        return
    next_floor = state.get("floor", 0) + 1
    if is_any_boss_floor(next_floor):
        advance_floor(state)
    else:
        prepare_event(state)

def apply_event_choice(state: Dict, event_id: str) -> None:
    player = state["player"]
    state["last_event_id"] = event_id
    advance = True
    late_floor = state.get("floor", 0) >= CURSED_FLOOR_MIN_FLOOR
    if event_id == "holy_spring":
        player["hp"] = player["hp_max"]
        _append_log(state, "Источник благодати полностью <b>исцеляет</b> вас.")
        if late_floor:
            added, dropped = _grant_small_potion(player)
            if added:
                _append_log(state, "Вы находите <b>малое зелье</b>.")
            if dropped:
                _append_log(state, "Нет места для зелий — находка сгорает.")
    elif event_id == "treasure_chest":
        state["chests_opened"] = state.get("chests_opened", 0) + 1
        chance = _clamp(player["luck"], 0.05, 0.7)
        if random.random() < chance:
            reward = _build_chest_reward(state["floor"] + 2, player)
            if not reward:
                reward = generate_single_reward(state["floor"] + 2, player)
            _append_log(state, "Сундук раскрывает <b>редкую</b> находку.")
            state["phase"] = "treasure"
            state["treasure_reward"] = reward
            state["event_options"] = []
            state["treasures_found"] = state.get("treasures_found", 0) + 1
            advance = False
        else:
            _append_log(state, "<i>Сундук пуст. Удача отвернулась.</i>")
        dropped_any = False
        added, dropped = _grant_small_potion(player)
        if added:
            _append_log(state, "Вы находите <b>малое зелье</b>.")
        dropped_any = dropped_any or dropped
        if late_floor:
            added, dropped = _grant_medium_potion(player, count=1)
            if added:
                _append_log(state, "Вы находите <b>среднее зелье</b>.")
            dropped_any = dropped_any or dropped
        if dropped_any:
            _append_log(state, "Нет места для зелий — находка сгорает.")
    elif event_id == "campfire":
        bonus = random.randint(2, 3)
        player["hp_max"] += bonus
        player["hp"] += bonus
        _append_log(state, f"Костер укрепляет вас: <b>+{bonus}</b> к макс. HP.")
        dropped_any = False
        added, dropped = _grant_small_potion(player)
        if added:
            _append_log(state, "Вы находите <b>малое зелье</b>.")
        dropped_any = dropped_any or dropped
        if late_floor:
            added, dropped = _grant_medium_potion(player, count=1)
            if added:
                _append_log(state, "Вы находите <b>среднее зелье</b>.")
            dropped_any = dropped_any or dropped
        if dropped_any:
            _append_log(state, "Нет места для зелий — находка сгорает.")
    else:
        _append_log(state, "Неверный выбор комнаты.")

    if advance:
        advance_floor(state)

def apply_boss_artifact_choice(state: Dict, artifact_id: str) -> None:
    player = state["player"]
    if artifact_id in {"artifact_power", "artifact_hp"}:
        player["power"] = player.get("power", 0) + 2
        _append_log(state, "Печать ярости наполняет вас: <b>+2</b> к урону.")
    elif artifact_id == "artifact_ap":
        cap = _ap_max_cap_for_floor(state.get("floor", 1))
        if int(player.get("ap_max", 0)) >= cap:
            _append_log(state, "Максимум ОД на этом этаже уже достигнут.")
            return
        player["ap_max"] += 1
        if player["ap_max"] > cap:
            player["ap_max"] = cap
        _append_log(state, "Артефакт воли укрепляет дух: <b>+1</b> к макс. ОД.")
    elif artifact_id == "artifact_potions":
        added, dropped = _grant_medium_potion(player, count=2)
        scroll = _grant_random_scroll(player)
        if added == 1:
            _append_log(state, "Алхимический набор дарует <b>среднее зелье</b>.")
        elif added > 1:
            _append_log(state, f"Алхимический набор дарует <b>{added} средних зелья</b>.")
        if scroll:
            _append_log(state, f"Также вы получаете свиток <b>{scroll['name']}</b>.")
        if dropped:
            _append_log(state, "Лишние зелья сгорают.")
    else:
        _append_log(state, "Вы не смогли выбрать артефакт.")

    player["hp"] = player["hp_max"]
    player["ap"] = player["ap_max"]
    state["boss_artifacts"] = []
    boss_kind = state.get("boss_kind")
    if boss_kind == "daughter":
        state["enemies"] = [build_daughter_boss(player, state.get("floor", BOSS_FLOOR))]
        state["phase"] = "battle"
        _append_log(state, "Дочь некроманта выходит из тени. Битва начинается.")
    elif boss_kind == "fallen":
        boss_name = state.get("boss_name") or LATE_BOSS_NAME_FALLBACK
        state["boss_name"] = boss_name
        state["enemies"] = [build_late_boss(player, state.get("floor", BOSS_FLOOR), boss_name)]
        state["phase"] = "battle"
        _append_log(state, f"{boss_name} поднимает оружие. Битва начинается.")
    else:
        state["enemies"] = [build_boss(player)]
        state["phase"] = "battle"
        _append_log(state, "Вы распахиваете двери. Некромант поднимает посох.")

def apply_treasure_choice(state: Dict, equip: bool) -> None:
    reward = state.get("treasure_reward")
    if not reward:
        _append_log(state, "Награда сундука недоступна.")
        advance_floor(state)
        return
    state["treasure_xp"] = state.get("treasure_xp", 0) + TREASURE_REWARD_XP
    if equip:
        apply_reward_item(state, reward)
    else:
        _append_log(state, "Вы оставляете находку в сундуке.")
    state["treasure_reward"] = None
    advance_floor(state)

def advance_floor(state: Dict) -> None:
    state["floor"] += 1
    state["rewards"] = []
    state["treasure_reward"] = None
    state["event_options"] = []
    state["boss_artifacts"] = []
    state["show_info"] = False
    state["cursed_ap_ratio"] = None
    player = state["player"]
    _enforce_ap_max_cap(player, state["floor"])
    if is_any_boss_floor(state["floor"]):
        player["hp"] = player["hp_max"]
        player["ap"] = player["ap_max"]
        state["phase"] = "boss_prep"
        state["boss_artifacts"] = generate_boss_artifacts()
        if is_boss_floor(state["floor"]):
            state["boss_kind"] = "necromancer"
            state["boss_name"] = "Некромант"
            state["boss_intro_lines"] = BOSS_INTRO_LINES
            state["enemies"] = [build_boss(player)]
        elif is_ultimate_boss_floor(state["floor"]):
            state["boss_kind"] = "daughter"
            state["boss_name"] = DAUGHTER_BOSS_NAME
            state["boss_intro_lines"] = DAUGHTER_INTRO_LINES
            state["enemies"] = [build_daughter_boss(player, state["floor"])]
        else:
            state["boss_kind"] = "fallen"
            state["boss_name"] = None
            state["boss_intro_lines"] = None
            state["enemies"] = [build_boss(player)]
        return
    if _roll_cursed_floor(state["floor"]):
        state["cursed_ap_ratio"] = CURSED_AP_RATIO
    player["ap"] = _effective_ap_max(state)
    state["boss_kind"] = None
    state["boss_name"] = None
    state["boss_intro_lines"] = None
    state["phase"] = "battle"
    state["enemies"] = generate_enemy_group(state["floor"], player, _effective_ap_max(state))
    _append_log(state, f"Вы спускаетесь на этаж <b>{state['floor']}</b>.")
    if state.get("cursed_ap_ratio"):
        _append_log(state, "Проклятый этаж: ОД снижены до <b>3/4</b>.")

def render_state(state: Dict) -> str:
    player = state["player"]
    weapon = player["weapon"]
    enemies = _alive_enemies(state["enemies"])
    effective_ap_max = _effective_ap_max(state)
    tutorial_active = bool(state.get("tutorial"))

    last_breath_active = _is_last_breath(player, state["floor"])
    accuracy_value = 1.0 if last_breath_active else player["accuracy"]
    accuracy_display = "∞" if last_breath_active else _percent(accuracy_value, show_percent=False)

    base_evasion = player.get("evasion", 0.0)
    effective_evasion = _effective_evasion(base_evasion, state.get("floor"))
    if effective_evasion != base_evasion:
        evasion_text = f"{_percent(base_evasion)} (эфф. {_percent(effective_evasion)})"
    else:
        evasion_text = _percent(base_evasion)

    lines = [
        f"<b>Этаж:</b> {state['floor']}",
        f"<b>HP:</b> {player['hp']}/{player['hp_max']} | <b>ОД:</b> {min(player['ap'], effective_ap_max)}/{effective_ap_max}",
        f"<b>Лимит ОД:</b> {_ap_max_cap_for_floor(state['floor'])}",
        (
            f"<b>Точность:</b> {accuracy_display} | "
            f"<b>Уклонение:</b> {evasion_text} | "
            f"<b>Броня:</b> {int(round(player['armor']))} | "
            f"<b>Удача:</b> {_percent(player.get('luck', 0.0))}"
        ),
        f"<b>Сила:</b> +{player.get('power', 0)} урона",
    ]
    if tutorial_active:
        step = int(state.get("tutorial_step", 1))
        scene = state.get("tutorial_scene", TUTORIAL_SCENE_NAME)
        prompt = tutorial_prompt(state)
        header = [
            "<b>Обучение</b>",
            f"<b>Локация:</b> {scene}",
        ]
        if prompt:
            header.append(f"<b>Шаг {step}/{TUTORIAL_TOTAL_STEPS}:</b> {prompt}")
        header.append("")
        lines = header + lines
    status_notes = []
    if _has_resolve(player):
        status_notes.append("Решимость — урон +20%")
    if last_breath_active:
        status_notes.append("На последнем издыхании — точность 100%")
    if state.get("cursed_ap_ratio"):
        status_notes.append("Проклятие — ОД 3/4")
    if effective_evasion != base_evasion:
        status_notes.append("Приглушение уклонения (50+ этаж)")
    if status_notes:
        lines.append(f"<b>Состояние:</b> <i>{' / '.join(status_notes)}</i>")
    lines.extend([
        f"<b>Оружие:</b> <b>{weapon['name']}</b> (урон {weapon['min_dmg']}-{weapon['max_dmg']})",
        f"<b>Зелий:</b> {len(player.get('potions', []))} | <b>Свитков:</b> {len(player.get('scrolls', []))}",
        "",
    ])

    if state["phase"] in {"battle", "forfeit_confirm", "tutorial"}:
        if enemies:
            lines.append(f"<b>Враги ({len(enemies)}):</b>")
            for enemy in enemies:
                lines.append(f"- <b>{enemy['name']}</b>: {enemy['hp']}/{enemy['max_hp']} HP")
        else:
            lines.append("<i>Враги отсутствуют.</i>")
        info_lines = []
        if state.get("show_info"):
            info_lines = ["", *build_enemy_info_text(state.get("enemies", []), player, state.get("floor", 1)).splitlines()]
        if state["phase"] == "forfeit_confirm":
            lines.append("")
            lines.append("<i>Подтвердите сдачу. Забег будет завершен.</i>")
    elif state["phase"] == "reward":
        if state.get("boss_defeated") and state.get("floor") == BOSS_FLOOR:
            lines.append("<b>Некромант повержен.</b> Его чары рассеялись над залом.")
            lines.append("Королевство вздыхает свободнее, но зелье вечной жизни все еще скрыто.")
            lines.append("<i>Вы продолжаете спуск — руины бесконечны.</i>")
            lines.append("")
        lines.append("<b>Награды:</b>")
        for idx, reward in enumerate(state.get("rewards", []), start=1):
            item = reward["item"]
            details = _format_reward_details(reward["type"], item)
            lines.append(f"{idx}. <b>{item['name']}</b> {details}")
    elif state["phase"] == "boss_prep":
        intro_lines = state.get("boss_intro_lines") or BOSS_INTRO_LINES
        lines.extend(intro_lines)
        lines.append("")
        lines.append("<b>Перед дверью лежат артефакты:</b>")
        for idx, option in enumerate(state.get("boss_artifacts", []), start=1):
            lines.append(f"{idx}. <b>{option['name']}</b> — <i>{option['effect']}</i>")
        lines.append("<i>Выберите артефакт для битвы.</i>")
    elif state["phase"] == "event":
        lines.append("<b>Комнаты между этажами:</b>")
        for idx, option in enumerate(state.get("event_options", []), start=1):
            lines.append(f"{idx}. <b>{option['name']}</b> — <i>{option['effect']}</i>")
    elif state["phase"] == "treasure":
        reward = state.get("treasure_reward")
        if reward:
            item = reward["item"]
            details = _format_reward_details(reward["type"], item)
            lines.append("<b>Сундук древних раскрывает находку:</b>")
            lines.append(f"<b>{item['name']}</b> {details}")
            if reward["type"] == "weapon":
                current = player["weapon"]
                current_details = _format_reward_details("weapon", current)
                lines.append("")
                lines.append("<b>Сравнение оружия:</b>")
                lines.append(f"Текущее: <b>{current['name']}</b> {current_details}")
                lines.append(f"Найденное: <b>{item['name']}</b> {details}")
            lines.append("")
            lines.append("<i>Экипировать находку или оставить?</i>")
        else:
            lines.append("<i>Ничего не найдено.</i>")
    elif state["phase"] == "potion_select":
        small_count = count_potions(player, "potion_small")
        medium_count = count_potions(player, "potion_medium")
        strong_count = count_potions(player, "potion_strong")
        lines.append("<b>Выбор зелья:</b>")
        small_heal, small_ap = _potion_stats(player, "potion_small")
        medium_heal, medium_ap = _potion_stats(player, "potion_medium")
        strong_heal, strong_ap = _potion_stats(player, "potion_strong")
        if small_count > 0:
            small_limit = POTION_LIMITS.get("potion_small", small_count)
            lines.append(
                f"Малое зелье: <b>{small_count}/{small_limit}</b> (+{small_heal} HP, +{small_ap} ОД)"
            )
        if medium_count > 0:
            medium_limit = POTION_LIMITS.get("potion_medium", medium_count)
            lines.append(
                f"Среднее зелье: <b>{medium_count}/{medium_limit}</b> (+{medium_heal} HP, +{medium_ap} ОД)"
            )
        if strong_count > 0:
            strong_limit = POTION_LIMITS.get("potion_strong", strong_count)
            lines.append(
                f"Сильное зелье: <b>{strong_count}/{strong_limit}</b> (+{strong_heal} HP, +{strong_ap} ОД)"
            )
        lines.append("<i>Выберите зелье для использования.</i>")
    elif state["phase"] == "inventory":
        lines.append("<b>Инвентарь:</b>")
        magic_damage = _magic_scroll_damage(player, ap_max=_effective_ap_max(state))
        if tutorial_active:
            config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
            magic_damage = int(config.get("scroll_hit", magic_damage))
        lines.append(f"<b>Магический урон:</b> {magic_damage} | <b>Стоимость:</b> 1 ОД")
        scrolls = player.get("scrolls", [])
        if scrolls:
            grouped = {}
            order = []
            for scroll in scrolls:
                scroll_id = scroll.get("id")
                if not scroll_id:
                    continue
                if scroll_id not in grouped:
                    grouped[scroll_id] = {
                        "name": scroll.get("name", "Свиток"),
                        "desc": scroll.get("desc", "").strip(),
                        "count": 0,
                    }
                    order.append(scroll_id)
                grouped[scroll_id]["count"] += 1
            for idx, scroll_id in enumerate(order, start=1):
                entry = grouped[scroll_id]
                label = entry["name"]
                if entry["count"] > 1:
                    label = f"{label} x{entry['count']}"
                desc_text = f" — <i>{entry['desc']}</i>" if entry["desc"] else ""
                lines.append(f"{idx}. <b>{label}</b>{desc_text}")
            lines.append("")
            lines.append("<i>Выберите свиток для использования.</i>")
        else:
            lines.append("<i>Свитков нет.</i>")
    elif state["phase"] == "dead":
        lines.append("<b>Вы погибли.</b>")

    if state["phase"] in {"battle", "forfeit_confirm", "tutorial"} and enemies:
        total_expected = 0.0
        total_max = 0
        player_evasion = player.get("evasion", 0.0)
        floor = state.get("floor")
        for enemy in enemies:
            hit_damage = _enemy_damage_to_player(enemy, player, floor)
            hit_chance = _enemy_expected_hit_chance(enemy, player_evasion, floor)
            total_expected += hit_damage * hit_chance
            total_max += hit_damage
        expected_display = max(1, int(round(total_expected)))
        lines.append("")
        lines.append(
            f"<b>Сводка:</b> HP {player['hp']}/{player['hp_max']} | "
            f"урон врагов (ожид./макс.): {expected_display}/{total_max}"
        )

    log_lines = []
    if state.get("log"):
        log_lines = ["", "<i>Последние события:</i>", *state["log"]]
    if 'info_lines' in locals() and info_lines:
        base_len = len("\n".join(lines))
        log_len = len("\n".join(log_lines)) if log_lines else 0
        allowed = MESSAGE_LIMIT - base_len - log_len
        info_lines = _trim_lines_to_limit(info_lines, allowed)
        lines.extend(info_lines)
    if log_lines:
        lines.extend(log_lines)

    return "\n".join(lines)

def _format_reward_details(reward_type: str, item: Dict) -> str:
    if reward_type == "weapon":
        parts = [f"урон {item['min_dmg']}-{item['max_dmg']}"]
        if item.get("accuracy_bonus"):
            sign = "+" if item["accuracy_bonus"] > 0 else ""
            parts.append(f"точность {sign}{int(round(item['accuracy_bonus'] * 100))}%")
        if item.get("splash_ratio"):
            parts.append(f"сплэш {int(round(item['splash_ratio'] * 100))}%")
        if item.get("bleed_chance"):
            chance = int(round(item["bleed_chance"] * 100))
            parts.append(f"кровотечение: {chance}% шанс, {item['bleed_damage']} урона/ход")
        if item.get("armor_pierce"):
            parts.append(f"бронепробой {int(round(item['armor_pierce'] * 100))}%")
        return f"({' | '.join(parts)})"
    if reward_type == "upgrade":
        if "(" in item.get("name", ""):
            return ""
        if item["type"] == "stat":
            amount = item["amount"]
            sign = "+" if amount > 0 else ""
            stat_names = {
                "hp_max": "HP",
                "ap_max": "ОД",
                "accuracy": "точность",
                "evasion": "уклонение",
                "armor": "броня",
                "power": "урон",
                "luck": "удача",
            }
            stat_name = stat_names.get(item["stat"], item["stat"])
            if item["stat"] in {"accuracy", "evasion", "luck"}:
                amount_text = f"{int(round(amount * 100))}%"
            else:
                amount_text = str(amount)
            return f"({sign}{amount_text} {stat_name})"
        if item["type"] == "potion":
            return f"(+{item['heal']} HP, +{item['ap_restore']} ОД)"
    if reward_type == "scroll":
        desc = item.get("desc", "").strip()
        return f"(<i>{desc}</i>)" if desc else ""
    return ""
