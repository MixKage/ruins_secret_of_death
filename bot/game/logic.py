import copy
import random
from typing import Dict, List, Tuple

from .characters import (
    CHARACTERS,
    DUELIST_PARRY_COUNTER_RATIO,
    DUELIST_ZONE_CHARGES,
    DUELIST_PARRY_REDUCTION,
    DUELIST_PARRY_REDUCTION_BOSS,
    DUELIST_PARRY_REDUCTION_VIRTUOSO,
    DUELIST_VIRTUOSO_FLOOR,
    DUELIST_VIRTUOSO_ZONE_CHARGES,
    DUELIST_ZONE_TURNS,
    EXECUTIONER_ID,
    EXECUTIONER_BLEED_CHANCE_BONUS,
    RUNE_GUARD_AP_BONUS,
    RUNE_GUARD_RETRIBUTION_PIERCE,
    RUNE_GUARD_RETRIBUTION_THRESHOLD,
    RUNE_GUARD_SHIELD_BONUS,
    _assassin_backstab_bonus,
    _assassin_echo_ratio,
    _assassin_full_hp_bonus,
    _assassin_potion_bonus,
    _assassin_shadow_active,
    _berserk_damage_bonus,
    _berserk_rage_state,
    BERSERK_MEAT_ACCURACY_BONUS,
    _desperate_charge_accuracy_bonus,
    _duelist_blade_pierce_bonus,
    _duelist_duel_accuracy_bonus,
    _duelist_duel_damage_bonus,
    _executioner_damage_bonus,
    _has_last_breath,
    _has_resolve,
    _has_steady_breath,
    _is_assassin,
    _is_berserk,
    BERSERK_ID,
    _is_desperate_charge,
    _is_duelist,
    _is_executioner,
    _is_hunter,
    _is_rune_guard,
    _hunter_first_shot_bonus,
    _hunter_mark_bonus,
    apply_character_starting_stats,
    get_character,
    is_desperate_charge_available,
    potion_full_name,
    potion_label,
    potion_label_with_count,
    potion_menu_title,
    potion_no_match_message,
    potion_noun_genitive_plural,
    potion_noun_plural,
    potion_received_verb,
    potion_empty_message,
    potion_use_label,
    resolve_character_id,
)
from .combat_utils import _alive_enemies, _first_alive, _tally_kills
from .common import MESSAGE_LIMIT, _append_log, _clamp, _percent, _trim_lines_to_limit
from .data import CHEST_LOOT, ENEMIES, SCROLLS, UPGRADES, WEAPONS, get_scroll_by_id, get_upgrade_by_id, get_weapon_by_id
from .effects import _apply_burn, _apply_freeze
from .items import (
    POTION_LIMITS,
    _add_potion,
    _add_scroll,
    _fill_potions,
    _grant_lightning_scroll,
    _grant_medium_potion,
    _grant_random_scroll,
    _grant_small_potion,
    _grant_strong_potion,
    _potion_stats,
    count_potions,
)
from .run_tasks import build_run_tasks, run_tasks_lines, run_tasks_summary
from .tutorial import (
    TUTORIAL_DEFAULT_CONFIG,
    TUTORIAL_SCENE_NAME,
    TUTORIAL_TOTAL_STEPS,
    new_tutorial_state,
    tutorial_apply_action,
    tutorial_expected_action,
    tutorial_force_endturn,
    tutorial_hint,
    tutorial_prompt,
    tutorial_use_scroll,
)

TREASURE_REWARD_XP = 5

ENEMY_DAMAGE_BUDGET_RATIO = 0.4
ENEMY_DAMAGE_BUDGET_RATIO_POST_BOSS = 0.6

LUCK_MAX = 0.7
FULL_HEALTH_DAMAGE_BONUS = 0.2

SECOND_CHANCE_AMULET_ID = "second_chance_amulet"
SECOND_CHANCE_CHEST_CHANCE = 0.02

AP_MAX_BASE_CAP = 4
AP_MAX_STEP_PER_TIER = 2

ARMOR_CAP_BEFORE_50 = 4
ARMOR_CAP_BEFORE_100 = 6
EVASION_CAP_BEFORE_50 = 0.4
EVASION_CAP_BEFORE_100 = 0.8

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

def _effective_ap_max(state: Dict) -> int:
    player = state.get("player", {})
    ap_max = max(1, int(player.get("ap_max", 1)))
    bonus = int(state.get("ap_bonus", 0) or 0)
    effective = ap_max
    ratio = state.get("cursed_ap_ratio")
    if ratio:
        effective = max(1, int(effective * ratio))
    cap = _ap_max_cap_for_floor(state.get("floor", 1))
    effective = min(cap, effective + max(0, bonus))
    return max(1, int(effective))

def _apply_cursed_ap(state: Dict) -> bool:
    player = state.get("player", {})
    effective = _effective_ap_max(state)
    if player.get("ap", 0) > effective:
        player["ap"] = effective
        return True
    return False

def _refresh_turn_ap(state: Dict) -> None:
    player = state.get("player", {})
    if not player:
        return
    state["desperate_charge_used"] = False
    state["berserk_kill_used"] = False
    state["assassin_echo_used"] = False
    state["hunter_first_shot_used"] = False
    state["hunter_kill_used"] = False
    state["executioner_bleed_used"] = False
    state["executioner_onslaught_used"] = False
    state["executioner_heal_count"] = 0
    state["duelist_blade_used"] = False
    state["duelist_parry_used"] = False
    _purge_executioner_strong_potions(state)
    if _has_steady_breath(state, player):
        state["ap_bonus"] = RUNE_GUARD_AP_BONUS
    else:
        state["ap_bonus"] = 0
    player["ap"] = _effective_ap_max(state)
    _apply_executioner_last_breath_penalty(state)
    if state.get("berserk_meat_turns", 0) > 0:
        state["berserk_meat_turns"] = max(0, int(state.get("berserk_meat_turns", 0)) - 1)

def apply_second_chance(
    state: Dict,
    note: str | None = None,
    consume: bool = False,
) -> None:
    player = state.get("player", {})
    if not player:
        return
    if consume:
        player["second_chance"] = False
    player["hp"] = 1
    player["ap"] = _effective_ap_max(state)
    state["phase"] = "battle"
    state.pop("second_chance_offer_type", None)
    _append_log(state, note or "Амулет второго шанса спасает вас: 1 HP и полные ОД.")

def _apply_rune_guard_shield(state: Dict) -> None:
    if not _is_rune_guard(state):
        return
    if state.get("rune_guard_shield_active"):
        return
    player = state.get("player", {})
    if player.get("ap", 0) > 0:
        return
    player["armor"] = float(player.get("armor", 0.0)) + RUNE_GUARD_SHIELD_BONUS
    state["rune_guard_shield_active"] = True
    _append_log(state, "Щит Рун: броня +2 до конца хода врагов.")

def _clear_rune_guard_shield(state: Dict) -> None:
    if not state.get("rune_guard_shield_active"):
        return
    player = state.get("player", {})
    player["armor"] = max(0.0, float(player.get("armor", 0.0)) - RUNE_GUARD_SHIELD_BONUS)
    state["rune_guard_shield_active"] = False

def _maybe_trigger_rune_guard_retribution(state: Dict, damage: int) -> None:
    if not _is_rune_guard(state):
        return
    if state.get("rune_guard_retribution_ready"):
        return
    player = state.get("player", {})
    hp_max = int(player.get("hp_max", 0))
    if hp_max <= 0:
        return
    if damage > hp_max * RUNE_GUARD_RETRIBUTION_THRESHOLD:
        state["rune_guard_retribution_ready"] = True
        _append_log(state, "Каменный Ответ: следующий удар игнорирует 30% брони.")


def _apply_executioner_last_breath_penalty(state: Dict) -> None:
    if not _is_executioner(state):
        state["executioner_last_breath_turns"] = 0
        return
    player = state.get("player", {})
    if not player:
        return
    if _has_last_breath(state, player):
        turns = int(state.get("executioner_last_breath_turns", 0)) + 1
        state["executioner_last_breath_turns"] = turns
        if turns > 3:
            player["hp"] -= 10
            _append_log(state, "Цена смерти: -10 HP за затяжное издыхание.")
            if player["hp"] <= 0:
                player["hp"] = 0
                state["phase"] = "dead"
    else:
        state["executioner_last_breath_turns"] = 0


def _executioner_bleed_chance(state: Dict, weapon: Dict) -> float:
    base_chance = float(weapon.get("bleed_chance", 0.0) or 0.0)
    if base_chance <= 0:
        return 0.0
    if _is_executioner(state):
        base_chance = _clamp(base_chance + EXECUTIONER_BLEED_CHANCE_BONUS, 0.0, 1.0)
    return base_chance


def _fill_potions_executioner(player: Dict, ratio: float = 1.0) -> Dict[str, int]:
    added_counts: Dict[str, int] = {}
    for potion_id in ("potion_small", "potion_medium"):
        limit = POTION_LIMITS.get(potion_id, 999)
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


def _purge_executioner_strong_potions(state: Dict) -> None:
    if not _is_executioner(state):
        return
    player = state.get("player", {})
    potions = [potion for potion in player.get("potions", []) if potion.get("id") != "potion_strong"]
    if len(potions) != len(player.get("potions", [])):
        player["potions"] = potions


def _trigger_berserk_meat_buff(state: Dict) -> None:
    if not _is_berserk(state):
        return
    state["berserk_meat_turns"] = max(state.get("berserk_meat_turns", 0), 1)
    _append_log(state, "Сытая ярость: точность +30% на 1 ход.")


def _duel_target(state: Dict) -> Dict | None:
    idx = state.get("duel_target_idx")
    if idx is None:
        return None
    enemies = state.get("enemies", [])
    if not isinstance(idx, int) or idx < 0 or idx >= len(enemies):
        return None
    target = enemies[idx]
    if target.get("hp", 0) <= 0:
        return None
    return target


def _duel_zone_active(state: Dict) -> bool:
    return int(state.get("duel_turns_left", 0) or 0) > 0 and _duel_target(state) is not None


def _duelist_duel_active(state: Dict) -> bool:
    if not _is_duelist(state):
        return False
    if _duel_zone_active(state):
        return True
    alive = _alive_enemies(state.get("enemies", []))
    return len(alive) == 1


def _duelist_virtuoso_active(state: Dict) -> bool:
    return _is_duelist(state) and int(state.get("floor", 0)) >= DUELIST_VIRTUOSO_FLOOR


def _duelist_max_zone_charges(state: Dict) -> int:
    return DUELIST_VIRTUOSO_ZONE_CHARGES if _duelist_virtuoso_active(state) else DUELIST_ZONE_CHARGES


def _is_boss_enemy(state: Dict, enemy: Dict | None = None) -> bool:
    if state.get("boss_kind"):
        return True
    boss_ids = {"necromancer", "fallen_hero", "necromancer_daughter"}
    return bool(enemy and enemy.get("id") in boss_ids)


def _duelist_parry_reduction(state: Dict, enemy: Dict | None = None) -> float:
    if _duelist_virtuoso_active(state):
        return DUELIST_PARRY_REDUCTION_VIRTUOSO
    if _is_boss_enemy(state, enemy):
        return DUELIST_PARRY_REDUCTION_BOSS
    return DUELIST_PARRY_REDUCTION


def _decrement_duel_zone(state: Dict) -> None:
    if not _duel_zone_active(state):
        state["duel_turns_left"] = 0
        state["duel_target_idx"] = None
        return
    state["duel_turns_left"] = max(0, int(state.get("duel_turns_left", 0)) - 1)
    if state["duel_turns_left"] <= 0:
        state["duel_target_idx"] = None


def _hunter_transfer_mark(state: Dict) -> None:
    if not _is_hunter(state):
        return
    marked_dead = next(
        (enemy for enemy in state.get("enemies", []) if enemy.get("hunter_mark") and enemy.get("hp", 0) <= 0),
        None,
    )
    if not marked_dead:
        return
    for enemy in state.get("enemies", []):
        enemy.pop("hunter_mark", None)
    alive = _alive_enemies(state.get("enemies", []))
    if not alive:
        return
    limit = (len(alive) + 1) // 2
    candidates = alive[:limit]
    new_target = random.choice(candidates)
    new_target["hunter_mark"] = True
    _append_log(state, f"Перенос метки: цель {new_target['name']} отмечена.")

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

def _magic_scroll_damage(state: Dict, player: Dict, ap_max: int | None = None) -> int:
    weapon = player.get("weapon", {})
    max_weapon = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    ap_value = int(ap_max if ap_max is not None else player.get("ap_max", 1))
    dmg = max_weapon * ap_value
    dmg = max(20, int(dmg))
    if _has_resolve(state, player):
        dmg = int(round(dmg * (1.0 + FULL_HEALTH_DAMAGE_BONUS)))
    berserk_bonus = _berserk_damage_bonus(state, player)
    if berserk_bonus:
        dmg = int(round(dmg * (1.0 + berserk_bonus)))
    assassin_bonus = _assassin_full_hp_bonus(state, player)
    if assassin_bonus:
        dmg = int(round(dmg * (1.0 + assassin_bonus)))
    duel_bonus = _duelist_duel_damage_bonus(state, _duelist_duel_active(state))
    if duel_bonus:
        dmg = int(round(dmg * (1.0 + duel_bonus)))
    return dmg

def _is_luck_maxed(player: Dict) -> bool:
    return player.get("luck", 0.0) >= LUCK_MAX

def _has_second_chance(player: Dict) -> bool:
    return bool(player.get("second_chance"))

def _can_drop_second_chance(pool: List[Dict], player: Dict | None) -> bool:
    if not player or _has_second_chance(player):
        return False
    return any(
        entry.get("type") == "upgrade" and entry.get("id") == SECOND_CHANCE_AMULET_ID
        for entry in pool
    )


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
    if _has_second_chance(player):
        filtered = [
            item
            for item in filtered
            if not (item.get("type") == "upgrade" and item.get("id") == SECOND_CHANCE_AMULET_ID)
        ]
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


def _filter_upgrades_for_player(
    upgrades: List[Dict],
    player: Dict | None,
    floor: int,
    character_id: str | None = None,
) -> List[Dict]:
    if not player:
        return upgrades
    filtered = upgrades
    if character_id == EXECUTIONER_ID:
        filtered = [item for item in filtered if item.get("id") != "potion_strong"]
    filtered = [item for item in filtered if item.get("id") != SECOND_CHANCE_AMULET_ID]
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

ROOM_NAME_OVERRIDES = {
    EXECUTIONER_ID: {"holy_spring": "Камера Дознания"},
    BERSERK_ID: {"holy_spring": "Очаг ярости"},
}

ROOM_DEFAULT_NAMES = {option["id"]: option["name"] for option in EVENT_OPTIONS}


def _room_name(character_id: str | None, room_id: str) -> str:
    override = ROOM_NAME_OVERRIDES.get(resolve_character_id(character_id), {})
    return override.get(room_id, ROOM_DEFAULT_NAMES.get(room_id, room_id))


def _room_effect_description(character_id: str | None, room_id: str, late_floor: bool) -> str:
    if room_id == "holy_spring":
        if resolve_character_id(character_id) == EXECUTIONER_ID:
            count = 2 if late_floor else 1
            return potion_label_with_count(character_id, "potion_medium", count=count)
        effect = "Полностью восстанавливает здоровье"
        if late_floor:
            small_label = potion_label(character_id, "potion_small")
            effect += f" + {small_label}"
        return effect
    if room_id == "treasure_chest":
        effect = "Шанс на награду +2 этажа или свиток магии + "
        effect += potion_label(character_id, "potion_small")
        if late_floor:
            medium_label = potion_label(character_id, "potion_medium")
            effect += f" и {medium_label}"
        return effect
    if room_id == "campfire":
        effect = "+2-3 к макс. HP + "
        effect += potion_label(character_id, "potion_small")
        if late_floor:
            medium_label = potion_label(character_id, "potion_medium")
            effect += f" и {medium_label}"
        return effect
    return ""

def is_boss_floor(floor: int) -> bool:
    return floor == BOSS_FLOOR

def is_ultimate_boss_floor(floor: int) -> bool:
    return floor >= ULTIMATE_BOSS_FLOOR_STEP and floor % ULTIMATE_BOSS_FLOOR_STEP == 0

def is_late_boss_floor(floor: int) -> bool:
    return floor > BOSS_FLOOR and floor % LATE_BOSS_FLOOR_STEP == 0 and not is_ultimate_boss_floor(floor)

def is_any_boss_floor(floor: int) -> bool:
    return is_boss_floor(floor) or is_late_boss_floor(floor) or is_ultimate_boss_floor(floor)

def generate_boss_artifacts(character_id: str | None = None) -> List[Dict]:
    options = [copy.deepcopy(option) for option in BOSS_ARTIFACT_OPTIONS]
    if character_id:
        for option in options:
            if option.get("id") == "artifact_potions":
                label = potion_label_with_count(character_id, "potion_medium", count=2)
                option["effect"] = f"{label} + случайный свиток"
    return options

def build_boss(player: Dict) -> Dict:
    ap_max = int(player.get("ap_max", 2))
    potions = len(player.get("potions", []))
    ap_bonus = max(0, ap_max - 2)
    potion_bonus = min(potions, 5)
    scale = 1.0 + ap_bonus * 0.08 + potion_bonus * 0.04
    scale = _clamp(scale, 1.0, 1.4)

    hp_max = max(80, int(player["hp_max"] * 2.2 * scale * 2))
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

def build_late_boss(player: Dict, floor: int, boss_name: str, character_id: str | None = None) -> Dict:
    steps = max(1, (floor - BOSS_FLOOR) // LATE_BOSS_FLOOR_STEP)
    weapon = player.get("weapon", {})
    max_hit = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    avg_hit = (int(weapon.get("min_dmg", 0)) + int(weapon.get("max_dmg", 0))) / 2 + int(player.get("power", 0))
    state_stub = {"character_id": character_id}
    resolve_mult = 1.2 if _has_resolve(state_stub, player) else 1.0
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
        "always_hit": True,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "burn_turns": 0,
        "burn_damage": 0,
        "skip_turns": 0,
        "counted_dead": False,
        "info": "Павший авантюрист, поднятый темной силой. Полностью игнорирует уклонение. Каждый удар неизбежен.",
        "danger": "легендарная",
        "min_floor": floor,
        "max_floor": floor,
    }

def build_daughter_boss(player: Dict, floor: int, character_id: str | None = None) -> Dict:
    steps = max(1, floor // ULTIMATE_BOSS_FLOOR_STEP)
    power_mult = DAUGHTER_BOSS_BASE_MULT + (steps - 1) * DAUGHTER_BOSS_STEP_BONUS
    weapon = player.get("weapon", {})
    max_hit = int(weapon.get("max_dmg", 0)) + int(player.get("power", 0))
    avg_hit = (int(weapon.get("min_dmg", 0)) + int(weapon.get("max_dmg", 0))) / 2 + int(player.get("power", 0))
    state_stub = {"character_id": character_id}
    resolve_mult = 1.2 if _has_resolve(state_stub, player) else 1.0
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

def new_run_state(character_id: str | None = None) -> Dict:
    weapon = copy.deepcopy(random.choice(_weapons_for_floor(1)))
    potion = copy.deepcopy(get_upgrade_by_id("potion_small"))
    ice_scroll = copy.deepcopy(get_scroll_by_id("scroll_ice"))
    chosen_id = resolve_character_id(character_id)
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
        "second_chance": False,
        "weapon": weapon,
        "potions": [],
        "scrolls": [],
    }
    apply_character_starting_stats(player, chosen_id)
    if potion:
        _add_potion(player, potion, count=1)
    if ice_scroll:
        _add_scroll(player, ice_scroll)
    state = {
        "floor": 1,
        "phase": "battle",
        "character_id": chosen_id,
        "ap_bonus": 0,
        "desperate_charge_used": False,
        "berserk_kill_used": False,
        "assassin_echo_used": False,
        "hunter_first_shot_used": False,
        "hunter_kill_used": False,
        "executioner_bleed_used": False,
        "executioner_onslaught_used": False,
        "executioner_heal_count": 0,
        "executioner_last_breath_turns": 0,
        "duel_zone_charges": (
            _duelist_max_zone_charges({"character_id": chosen_id, "floor": 1})
            if _is_duelist({"character_id": chosen_id})
            else 0
        ),
        "duel_turns_left": 0,
        "duel_target_idx": None,
        "duelist_blade_used": False,
        "duelist_parry_used": False,
        "berserk_second_wind_used": False,
        "berserk_meat_turns": 0,
        "rune_guard_shield_active": False,
        "rune_guard_retribution_ready": False,
        "run_tasks": build_run_tasks(),
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
    _refresh_turn_ap(state)
    _append_log(state, f"Вы нашли <b>{weapon['name']}</b> и спускаетесь на этаж <b>1</b>.")
    return state


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
    if floor >= 11 and _is_duelist(player):
        min_group += 1
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

def roll_damage(
    weapon: Dict,
    player: Dict,
    target: Dict,
    state: Dict,
    armor_pierce_bonus: float = 0.0,
) -> int:
    base = random.randint(weapon["min_dmg"], weapon["max_dmg"]) + player["power"]
    pierce = min(1.0, weapon.get("armor_pierce", 0.0) + max(0.0, armor_pierce_bonus))
    armor = max(0.0, target["armor"] * (1.0 - pierce))
    reduced_portion = base * ENEMY_ARMOR_REDUCED_RATIO
    bypass_portion = base * (1.0 - ENEMY_ARMOR_REDUCED_RATIO)
    dmg = int(max(1, round(max(0.0, reduced_portion - armor) + bypass_portion)))
    if _has_resolve(state, player):
        dmg = max(1, int(round(dmg * (1.0 + FULL_HEALTH_DAMAGE_BONUS))))
    berserk_bonus = _berserk_damage_bonus(state, player)
    if berserk_bonus:
        dmg = max(1, int(round(dmg * (1.0 + berserk_bonus))))
    assassin_bonus = _assassin_full_hp_bonus(state, player)
    if assassin_bonus:
        dmg = max(1, int(round(dmg * (1.0 + assassin_bonus))))
    backstab_bonus = _assassin_backstab_bonus(state, target)
    if backstab_bonus:
        dmg = max(1, int(round(dmg * (1.0 + backstab_bonus))))
    hunter_bonus = _hunter_mark_bonus(state, target)
    if hunter_bonus:
        dmg = max(1, int(round(dmg * (1.0 + hunter_bonus))))
    executioner_bonus = _executioner_damage_bonus(state, target)
    if executioner_bonus:
        dmg = max(1, int(round(dmg * (1.0 + executioner_bonus))))
    duel_bonus = _duelist_duel_damage_bonus(state, _duelist_duel_active(state))
    if duel_bonus:
        dmg = max(1, int(round(dmg * (1.0 + duel_bonus))))
    return dmg

def _floor_range_label(min_floor: int, max_floor: int) -> str:
    if max_floor >= 999:
        return f"{min_floor}+"
    if min_floor == max_floor:
        return f"{min_floor}"
    return f"{min_floor}-{max_floor}"

def build_enemy_info_text(
    enemies: List[Dict],
    player: Dict | None = None,
    floor: int | None = None,
    character_id: str | None = None,
) -> str:
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
            state_stub = {"character_id": character_id}
            is_rune_guard = _is_rune_guard(state_stub)
            is_duelist = _is_duelist(state_stub)
            duel_active = is_duelist and len(alive) == 1
            assassin_shadow = _assassin_shadow_active(state_stub, player)
            accuracy_bonus = _desperate_charge_accuracy_bonus(state_stub, player)
            accuracy_bonus += _duelist_duel_accuracy_bonus(state_stub, duel_active)
            player_accuracy = player.get("accuracy", 0.0) + weapon.get("accuracy_bonus", 0.0) + accuracy_bonus
            enemy_evasion = _effective_evasion(enemy.get("evasion", 0.0), floor)
            if _has_last_breath(state_stub, player) or assassin_shadow:
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
            if assassin_shadow:
                armor_pierce = max(armor_pierce, 1.0)
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
    _apply_rune_guard_shield(state)
    enemy_phase(state)
    _decrement_duel_zone(state)
    _tally_kills(state)
    _clear_rune_guard_shield(state)
    if state.get("phase") != "dead":
        _refresh_turn_ap(state)
    check_battle_end(state)

def player_attack(state: Dict, log_kills: bool = True) -> None:
    player = state["player"]
    desperate_active = _is_desperate_charge(state, player)
    free_attack = desperate_active and not state.get("desperate_charge_used", False)
    duel_active = _duelist_duel_active(state)
    if (
        _is_executioner(state)
        and not state.get("executioner_onslaught_used")
        and any(
            enemy.get("hp", 0) > 0 and enemy.get("bleed_turns", 0) > 0
            for enemy in state.get("enemies", [])
        )
    ):
        state["executioner_onslaught_used"] = True
        ap_before = player.get("ap", 0)
        player["ap"] = min(_effective_ap_max(state), ap_before + 1)
        if player["ap"] > ap_before:
            _append_log(state, "Натиск: +1 ОД.")
    if player["ap"] <= 0 and not free_attack:
        _append_log(state, "Нет ОД для атаки.")
        return

    if free_attack:
        state["desperate_charge_used"] = True
        _append_log(state, "Рывок Чести: атака без затрат ОД.")
    else:
        player["ap"] -= 1
    weapon = player["weapon"]
    target = _first_alive(state["enemies"])
    if target is None:
        return

    alive_before = len(_alive_enemies(state["enemies"]))
    bleeding_before = [
        enemy
        for enemy in state.get("enemies", [])
        if enemy.get("hp", 0) > 0 and enemy.get("bleed_turns", 0) > 0
    ]

    shadow_evaded = False
    target_killed = False
    last_breath = _has_last_breath(state, player)
    is_rune_guard = _is_rune_guard(state)
    is_assassin = _is_assassin(state)
    is_executioner = _is_executioner(state)
    is_hunter = _is_hunter(state)
    is_duelist = _is_duelist(state)
    assassin_shadow = _assassin_shadow_active(state, player)
    is_berserk = _is_berserk(state)
    hunter_first_shot = is_hunter and not state.get("hunter_first_shot_used")
    if hunter_first_shot:
        state["hunter_first_shot_used"] = True
    hunter_accuracy_bonus = _hunter_first_shot_bonus(state) if hunter_first_shot else 0.0
    duelist_accuracy_bonus = _duelist_duel_accuracy_bonus(state, duel_active)
    blade_bonus = _duelist_blade_pierce_bonus(state, state.get("duelist_blade_used", False))
    berserk_meat_bonus = BERSERK_MEAT_ACCURACY_BONUS if state.get("berserk_meat_turns", 0) > 0 else 0.0
    if blade_bonus:
        state["duelist_blade_used"] = True
    has_hunter_mark = any(enemy.get("hunter_mark") for enemy in state.get("enemies", []))
    base_accuracy = (
        player["accuracy"]
        + weapon["accuracy_bonus"]
        + hunter_accuracy_bonus
        + duelist_accuracy_bonus
        + berserk_meat_bonus
    )
    if _has_trait(target, ELITE_TRAIT_SHADOW) and not target.get("shadow_dodge_used"):
        target["shadow_dodge_used"] = True
        shadow_evaded = True
        hit = False
    else:
        if assassin_shadow:
            hit = True
        elif is_rune_guard:
            accuracy_bonus = _desperate_charge_accuracy_bonus(state, player)
            hit = roll_hit(
                base_accuracy + accuracy_bonus,
                target["evasion"],
                state.get("floor"),
            )
        else:
            hit = True if last_breath else roll_hit(
                base_accuracy,
                target["evasion"],
                state.get("floor"),
            )
    if hit:
        retribution_ready = state.get("rune_guard_retribution_ready", False)
        armor_pierce_bonus = (
            RUNE_GUARD_RETRIBUTION_PIERCE if retribution_ready else 0.0
        )
        if assassin_shadow:
            armor_pierce_bonus = max(armor_pierce_bonus, 1.0)
        if blade_bonus:
            armor_pierce_bonus += blade_bonus
        damage = roll_damage(weapon, player, target, state, armor_pierce_bonus=armor_pierce_bonus)
        target["hp"] -= damage
        _append_log(state, f"Вы наносите {damage} урона по {target['name']}.")
        if is_hunter and not has_hunter_mark:
            for enemy in state.get("enemies", []):
                enemy.pop("hunter_mark", None)
            target["hunter_mark"] = True
            _append_log(state, f"Охотничья метка: цель {target['name']} отмечена.")
        if retribution_ready and armor_pierce_bonus > 0:
            state["rune_guard_retribution_ready"] = False
            _append_log(state, "Каменный Ответ усиливает удар — броня частично игнорирована.")
        _apply_stone_skin(state, target)
        target_killed = target["hp"] <= 0
        if target_killed and state.get("duel_turns_left") and _duel_target(state) is None:
            state["duel_turns_left"] = 0
            state["duel_target_idx"] = None

        if weapon["splash_ratio"] > 0 and not _is_duelist(state):
            splash_targets = [enemy for enemy in state["enemies"] if enemy is not target and enemy["hp"] > 0]
            if splash_targets:
                splash_damage = max(1, int(damage * weapon["splash_ratio"]))
                hit_targets = splash_targets[:3]
                for enemy in hit_targets:
                    enemy["hp"] -= splash_damage
                    _apply_stone_skin(state, enemy)
                _append_log(state, f"Сплэш урон: {splash_damage} по {len(hit_targets)} врагам.")

        bleed_chance = _executioner_bleed_chance(state, weapon)
        if bleed_chance > 0 and random.random() < bleed_chance:
            target["bleed_turns"] = max(target["bleed_turns"], 2)
            target["bleed_damage"] = max(target["bleed_damage"], weapon["bleed_damage"])
            _append_log(state, f"{target['name']} истекает кровью.")
        _hunter_transfer_mark(state)
    else:
        if shadow_evaded:
            _append_log(state, f"{target['name']} растворяется в тени и избегает удара.")
        else:
            _append_log(state, "Вы промахиваетесь.")

    alive_after = len(_alive_enemies(state["enemies"]))
    killed = max(0, alive_before - alive_after)
    if (
        is_assassin
        and target_killed
        and not state.get("assassin_echo_used")
        and _assassin_echo_ratio(state) > 0
    ):
        state["assassin_echo_used"] = True
        echo_damage = max(1, int(round(damage * _assassin_echo_ratio(state))))
        echo_targets = [enemy for enemy in state["enemies"] if enemy is not target and enemy["hp"] > 0]
        if echo_targets:
            for enemy in echo_targets:
                enemy["hp"] -= echo_damage
                _apply_stone_skin(state, enemy)
            _append_log(state, f"Эхо убийства: {echo_damage} урона по {len(echo_targets)} врагам.")
        alive_after = len(_alive_enemies(state["enemies"]))
        killed = max(0, alive_before - alive_after)
    if is_executioner and bleeding_before:
        for enemy in bleeding_before:
            if enemy.get("hp", 0) <= 0 and state.get("executioner_heal_count", 0) < 2:
                state["executioner_heal_count"] = int(state.get("executioner_heal_count", 0)) + 1
                player["hp"] = min(player.get("hp_max", 0), player.get("hp", 0) + 5)
                _append_log(state, "Приговор: +5 HP за убийство кровоточащего врага.")
    if killed > 0 and is_berserk and not state.get("berserk_kill_used"):
        state["berserk_kill_used"] = True
        ap_before = player.get("ap", 0)
        player["ap"] = min(_effective_ap_max(state), ap_before + 1)
        if player["ap"] > ap_before:
            _append_log(state, "Кровавая добыча: +1 ОД за первое убийство в ход.")
    if killed > 0 and is_hunter and not state.get("hunter_kill_used"):
        state["hunter_kill_used"] = True
        ap_before = player.get("ap", 0)
        player["ap"] = min(_effective_ap_max(state), ap_before + 1)
        if player["ap"] > ap_before:
            _append_log(state, "Гон по следу: +1 ОД за первое убийство в ход.")

    check_battle_end(state)

    if log_kills and alive_before > 3:
        _append_log(state, f"Побеждено врагов за ход: {killed}.")

def player_use_potion(state: Dict) -> None:
    player = state["player"]
    if not player["potions"]:
        _append_log(state, potion_empty_message(state.get("character_id")))
        return

    potion = player["potions"].pop()
    bonus_heal = _assassin_potion_bonus(state)
    heal = int(potion.get("heal", 0)) + bonus_heal
    player["hp"] = min(player["hp_max"], player["hp"] + heal)
    player["ap"] = min(_effective_ap_max(state), player["ap"] + potion["ap_restore"])
    used_label = potion_use_label(state.get("character_id"))
    _append_log(state, f"Вы используете {used_label}: +{heal} HP, +{potion['ap_restore']} ОД.")
    _trigger_berserk_meat_buff(state)

    check_battle_end(state)

def player_use_potion_by_id(state: Dict, potion_id: str) -> None:
    player = state["player"]
    potions = player.get("potions", [])
    for idx, potion in enumerate(potions):
        if potion.get("id") == potion_id:
            potion = potions.pop(idx)
            bonus_heal = _assassin_potion_bonus(state)
            heal = int(potion.get("heal", 0)) + bonus_heal
            player["hp"] = min(player["hp_max"], player["hp"] + heal)
            player["ap"] = min(_effective_ap_max(state), player["ap"] + potion["ap_restore"])
            used_label = potion_use_label(state.get("character_id"))
            _append_log(state, f"Вы используете {used_label}: +{heal} HP, +{potion['ap_restore']} ОД.")
            _trigger_berserk_meat_buff(state)
            check_battle_end(state)
            return
    _append_log(state, potion_no_match_message(state.get("character_id")))


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

    alive_before = len(_alive_enemies(state["enemies"]))
    scroll = scrolls.pop(scroll_index)
    player["ap"] -= 1
    damage = _magic_scroll_damage(state, player, ap_max=_effective_ap_max(state))
    element = scroll.get("element")

    if element == "lightning":
        targets = _alive_enemies(state["enemies"])
        for enemy in targets:
            enemy_damage = damage
            mark_bonus = _hunter_mark_bonus(state, enemy)
            if mark_bonus:
                enemy_damage = max(1, int(round(enemy_damage * (1.0 + mark_bonus))))
            exec_bonus = _executioner_damage_bonus(state, enemy)
            if exec_bonus:
                enemy_damage = max(1, int(round(enemy_damage * (1.0 + exec_bonus))))
            enemy["hp"] -= enemy_damage
            _apply_stone_skin(state, enemy)
        _append_log(state, f"Вы читаете {scroll['name']}: молнии бьют по всем врагам на {damage} урона.")
    elif element == "ice":
        target_damage = damage
        mark_bonus = _hunter_mark_bonus(state, target)
        if mark_bonus:
            target_damage = max(1, int(round(target_damage * (1.0 + mark_bonus))))
        exec_bonus = _executioner_damage_bonus(state, target)
        if exec_bonus:
            target_damage = max(1, int(round(target_damage * (1.0 + exec_bonus))))
        target["hp"] -= target_damage
        _apply_stone_skin(state, target)
        _apply_freeze(target)
        _append_log(state, f"Вы читаете {scroll['name']}: {target['name']} получает {target_damage} урона и скован льдом.")
    else:
        target_damage = damage
        mark_bonus = _hunter_mark_bonus(state, target)
        if mark_bonus:
            target_damage = max(1, int(round(target_damage * (1.0 + mark_bonus))))
        exec_bonus = _executioner_damage_bonus(state, target)
        if exec_bonus:
            target_damage = max(1, int(round(target_damage * (1.0 + exec_bonus))))
        target["hp"] -= target_damage
        _apply_stone_skin(state, target)
        _apply_burn(target, target_damage)
        _append_log(state, f"Вы читаете {scroll['name']}: {target['name']} получает {target_damage} урона и горит.")

    _hunter_transfer_mark(state)
    if state.get("duel_turns_left") and _duel_target(state) is None:
        state["duel_turns_left"] = 0
        state["duel_target_idx"] = None

    if (
        _is_assassin(state)
        and not state.get("assassin_echo_used")
        and _assassin_echo_ratio(state) > 0
    ):
        alive_after = len(_alive_enemies(state["enemies"]))
        if alive_after < alive_before:
            state["assassin_echo_used"] = True
            echo_damage = max(1, int(round(damage * _assassin_echo_ratio(state))))
            echo_targets = [enemy for enemy in state["enemies"] if enemy.get("hp", 0) > 0]
            for enemy in echo_targets:
                enemy["hp"] -= echo_damage
                _apply_stone_skin(state, enemy)
            if echo_targets:
                _append_log(state, f"Эхо убийства: {echo_damage} урона по {len(echo_targets)} врагам.")
    bleeding_before = [
        enemy
        for enemy in state.get("enemies", [])
        if enemy.get("hp", 0) > 0 and enemy.get("bleed_turns", 0) > 0
    ]
    if _is_executioner(state) and bleeding_before:
        player = state.get("player", {})
        for enemy in bleeding_before:
            if enemy.get("hp", 0) <= 0 and state.get("executioner_heal_count", 0) < 2:
                state["executioner_heal_count"] = int(state.get("executioner_heal_count", 0)) + 1
                player["hp"] = min(player.get("hp_max", 0), player.get("hp", 0) + 5)
                _append_log(state, "Приговор: +5 HP за убийство кровоточащего врага.")

    check_battle_end(state)


def use_duel_zone(state: Dict) -> None:
    if not _is_duelist(state):
        _append_log(state, "Дуэльная зона доступна только дуэлянту.")
        return
    charges = int(state.get("duel_zone_charges", 0))
    if charges <= 0:
        _append_log(state, "Заряды дуэльной зоны закончились.")
        return
    enemies = state.get("enemies", [])
    target_idx = None
    for idx, enemy in enumerate(enemies):
        if enemy.get("hp", 0) > 0:
            target_idx = idx
            break
    if target_idx is None:
        _append_log(state, "Нет врагов для дуэли.")
        return
    state["duel_zone_charges"] = charges - 1
    state["duel_turns_left"] = DUELIST_ZONE_TURNS
    state["duel_target_idx"] = target_idx
    target = enemies[target_idx]
    _append_log(
        state,
        f"Дуэльная зона: {target['name']} вызван на дуэль на {DUELIST_ZONE_TURNS} хода.",
    )

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
    _hunter_transfer_mark(state)
    if state.get("duel_turns_left") and _duel_target(state) is None:
        state["duel_turns_left"] = 0
        state["duel_target_idx"] = None
    enemies = _alive_enemies(state["enemies"])
    if not enemies:
        return
    group_size = len(enemies)
    duel_target = _duel_target(state)
    duel_active = _duel_zone_active(state)
    if duel_active and duel_target and len(enemies) > 1:
        _append_log(state, "Дуэльная зона: остальные враги не могут атаковать.")

    for enemy in enemies:
        if duel_active and duel_target is not enemy:
            continue
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
            if _is_duelist(state) and not state.get("duelist_parry_used"):
                state["duelist_parry_used"] = True
                reduction = _duelist_parry_reduction(state, enemy)
                reduced_damage = max(0, int(round(damage * (1.0 - reduction))))
                prevented = max(0, damage - reduced_damage)
                damage = reduced_damage
                if prevented > 0:
                    counter = max(1, int(round(prevented * DUELIST_PARRY_COUNTER_RATIO)))
                    enemy["hp"] -= counter
                    _apply_stone_skin(state, enemy)
                    _append_log(state, f"Парирование: {enemy['name']} получает {counter} урона.")
            player["hp"] -= damage
            total_damage += damage
            _append_log(state, f"{enemy['name']} бьет вас на {damage} урона.")
            _maybe_trigger_rune_guard_retribution(state, damage)
        else:
            _append_log(state, f"{enemy['name']} промахивается.")
        if player["hp"] <= 0:
            if _is_berserk(state) and not state.get("berserk_second_wind_used"):
                state["berserk_second_wind_used"] = True
                player["hp"] = max(1, int(player.get("hp_max", 1)))
                _append_log(
                    state,
                    "Неистовая живучесть: смертельный удар пережит, HP полностью восстановлено.",
                )
                continue
            player["hp"] = 0
            state["phase"] = "dead"
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
            if _is_executioner(state):
                added = _fill_potions_executioner(state["player"], ratio=0.5)
            else:
                added = _fill_potions(state["player"], ratio=0.5)
            noun = potion_noun_genitive_plural(state.get("character_id"))
            if added:
                _append_log(state, f"Запас {noun} пополнен до половины.")
            else:
                _append_log(state, f"Запас {noun} уже полон.")
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
            if _is_executioner(state):
                added, dropped = _grant_medium_potion(state["player"], count=1)
                if added:
                    label = potion_label(state.get("character_id"), "potion_medium", title=True)
                    _append_log(state, f"Награда: <b>{label}</b>.")
                if dropped:
                    noun = potion_noun_genitive_plural(state.get("character_id"))
                    _append_log(state, f"Нет места для {noun} — награда сгорает.")
            else:
                added, dropped = _grant_strong_potion(state["player"], count=1)
                if added:
                    label = potion_label(state.get("character_id"), "potion_strong", title=True)
                    _append_log(state, f"Награда: <b>{label}</b>.")
                if dropped:
                    noun = potion_noun_genitive_plural(state.get("character_id"))
                    _append_log(state, f"Нет места для {noun} — награда сгорает.")
        state["phase"] = "reward"
        state["rewards"] = generate_rewards(
            state["floor"],
            state.get("player"),
            state.get("character_id"),
        )
        _append_log(state, f"<b>Этаж {state['floor']}</b> зачищен. Выберите награду.")

def generate_event_options() -> List[Dict]:
    return [copy.deepcopy(option) for option in EVENT_OPTIONS]

def _event_options_for_floor(floor: int, character_id: str | None = None) -> List[Dict]:
    options = generate_event_options()
    late_floor = floor >= CURSED_FLOOR_MIN_FLOOR
    for option in options:
        option["name"] = _room_name(character_id, option.get("id", ""))
        option["effect"] = _room_effect_description(character_id, option.get("id", ""), late_floor)
    return options

def _build_chest_reward(
    floor: int,
    player: Dict | None = None,
    character_id: str | None = None,
) -> Dict | None:
    pool = _filter_chest_loot_for_player(_chest_loot_for_floor(floor), player, floor)
    if character_id == EXECUTIONER_ID:
        pool = [item for item in pool if item.get("id") != "potion_strong"]
    if not pool:
        return None
    if _can_drop_second_chance(pool, player):
        pool = [
            item
            for item in pool
            if not (item.get("type") == "upgrade" and item.get("id") == SECOND_CHANCE_AMULET_ID)
        ]
        if random.random() < SECOND_CHANCE_CHEST_CHANCE:
            upgrade = copy.deepcopy(get_upgrade_by_id(SECOND_CHANCE_AMULET_ID))
            if upgrade:
                return {"type": "upgrade", "item": upgrade}
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

def generate_rewards(
    floor: int,
    player: Dict | None = None,
    character_id: str | None = None,
) -> List[Dict]:
    rewards = []
    used_ids = set()
    upgrades = _filter_upgrades_for_player(_upgrades_for_floor(floor), player, floor, character_id)
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [
        ("upgrade", item) for item in upgrades
    ]
    weapon_limit = 2
    weapon_count = 0
    while len(rewards) < 3 and pool:
        available_pool = [
            entry for entry in pool if not (weapon_count >= weapon_limit and entry[0] == "weapon")
        ]
        if not available_pool:
            break
        reward_type, item = random.choice(available_pool)
        item_id = item["id"]
        if item_id in used_ids:
            continue
        used_ids.add(item_id)
        reward_item = copy.deepcopy(item)
        if reward_type == "weapon":
            scale_weapon_stats(reward_item, floor)
            weapon_count += 1
        rewards.append({"type": reward_type, "item": reward_item})
    return rewards

def generate_single_reward(
    floor: int,
    player: Dict | None = None,
    character_id: str | None = None,
) -> Dict:
    upgrades = _filter_upgrades_for_player(_upgrades_for_floor(floor), player, floor, character_id)
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
        if upgrade["type"] == "special":
            if upgrade.get("id") == SECOND_CHANCE_AMULET_ID:
                if _has_second_chance(player):
                    _append_log(state, "Амулет второго шанса уже у вас.")
                    return False
                player["second_chance"] = True
                _append_log(state, f"Вы нашли <b>{upgrade['name']}</b>.")
                return True
        if upgrade["type"] == "potion":
            potion = upgrade
            if _is_executioner(state) and potion.get("id") == "potion_strong":
                potion = copy.deepcopy(get_upgrade_by_id("potion_medium")) or potion
            added, dropped = _add_potion(player, potion, count=1)
            if added:
                character_id = state.get("character_id")
                verb = potion_received_verb(character_id)
                name = potion_full_name(character_id, potion)
                _append_log(state, f"{verb} <b>{name}</b>.")
            if dropped:
                noun = potion_noun_genitive_plural(state.get("character_id"))
                _append_log(state, f"Нет места для {noun} — находка сгорает.")
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
    options = _event_options_for_floor(state.get("floor", 1), state.get("character_id"))
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
        if _is_executioner(state):
            count = 2 if late_floor else 1
            added, dropped = _grant_medium_potion(player, count=count)
            if added == 1:
                label = potion_label(state.get("character_id"), "potion_medium")
                _append_log(state, f"{_room_name(state.get('character_id'), event_id)} приносит <b>{label}</b>.")
            elif added > 1:
                label = potion_label_with_count(state.get("character_id"), "potion_medium", count=added)
                _append_log(state, f"{_room_name(state.get('character_id'), event_id)} приносит <b>{label}</b>.")
            if dropped:
                noun = potion_noun_genitive_plural(state.get("character_id"))
                _append_log(state, f"Нет места для {noun} — находка сгорает.")
        else:
            player["hp"] = player["hp_max"]
            room_name = _room_name(state.get("character_id"), event_id)
            _append_log(state, f"{room_name} полностью <b>исцеляет</b> вас.")
            if late_floor:
                added, dropped = _grant_small_potion(player)
                if added:
                    label = potion_label(state.get("character_id"), "potion_small")
                    _append_log(state, f"Вы находите <b>{label}</b>.")
                if dropped:
                    noun = potion_noun_genitive_plural(state.get("character_id"))
                    _append_log(state, f"Нет места для {noun} — находка сгорает.")
    elif event_id == "treasure_chest":
        state["chests_opened"] = state.get("chests_opened", 0) + 1
        chance = _clamp(player["luck"], 0.05, 0.7)
        if random.random() < chance:
            reward = _build_chest_reward(
                state["floor"] + 2,
                player,
                state.get("character_id"),
            )
            if not reward:
                reward = generate_single_reward(
                    state["floor"] + 2,
                    player,
                    state.get("character_id"),
                )
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
            label = potion_label(state.get("character_id"), "potion_small")
            _append_log(state, f"Вы находите <b>{label}</b>.")
        dropped_any = dropped_any or dropped
        if late_floor:
            added, dropped = _grant_medium_potion(player, count=1)
            if added:
                label = potion_label(state.get("character_id"), "potion_medium")
                _append_log(state, f"Вы находите <b>{label}</b>.")
            dropped_any = dropped_any or dropped
        if dropped_any:
            noun = potion_noun_genitive_plural(state.get("character_id"))
            _append_log(state, f"Нет места для {noun} — находка сгорает.")
    elif event_id == "campfire":
        bonus = random.randint(2, 3)
        player["hp_max"] += bonus
        player["hp"] += bonus
        _append_log(state, f"Костер укрепляет вас: <b>+{bonus}</b> к макс. HP.")
        dropped_any = False
        added, dropped = _grant_small_potion(player)
        if added:
            label = potion_label(state.get("character_id"), "potion_small")
            _append_log(state, f"Вы находите <b>{label}</b>.")
        dropped_any = dropped_any or dropped
        if late_floor:
            added, dropped = _grant_medium_potion(player, count=1)
            if added:
                label = potion_label(state.get("character_id"), "potion_medium")
                _append_log(state, f"Вы находите <b>{label}</b>.")
            dropped_any = dropped_any or dropped
        if dropped_any:
            noun = potion_noun_genitive_plural(state.get("character_id"))
            _append_log(state, f"Нет места для {noun} — находка сгорает.")
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
            label = potion_label(state.get("character_id"), "potion_medium")
            _append_log(state, f"Алхимический набор дарует <b>{label}</b>.")
        elif added > 1:
            label = potion_label_with_count(state.get("character_id"), "potion_medium", count=added)
            _append_log(state, f"Алхимический набор дарует <b>{label}</b>.")
        if scroll:
            _append_log(state, f"Также вы получаете свиток <b>{scroll['name']}</b>.")
        if dropped:
            noun = potion_noun_plural(state.get("character_id"))
            _append_log(state, f"Лишние {noun} сгорают.")
    else:
        _append_log(state, "Вы не смогли выбрать артефакт.")

    player["hp"] = player["hp_max"]
    _refresh_turn_ap(state)
    state["boss_artifacts"] = []
    boss_kind = state.get("boss_kind")
    if boss_kind == "daughter":
        state["enemies"] = [
            build_daughter_boss(player, state.get("floor", BOSS_FLOOR), state.get("character_id"))
        ]
        state["phase"] = "battle"
        _append_log(state, "Дочь некроманта выходит из тени. Битва начинается.")
    elif boss_kind == "fallen":
        boss_name = state.get("boss_name") or LATE_BOSS_NAME_FALLBACK
        state["boss_name"] = boss_name
        state["enemies"] = [
            build_late_boss(player, state.get("floor", BOSS_FLOOR), boss_name, state.get("character_id"))
        ]
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
    if _is_duelist(state):
        state["duel_zone_charges"] = _duelist_max_zone_charges(state)
    else:
        state["duel_zone_charges"] = 0
    state["duel_turns_left"] = 0
    state["duel_target_idx"] = None
    player = state["player"]
    _enforce_ap_max_cap(player, state["floor"])
    if is_any_boss_floor(state["floor"]):
        player["hp"] = player["hp_max"]
        _refresh_turn_ap(state)
        state["phase"] = "boss_prep"
        state["boss_artifacts"] = generate_boss_artifacts(state.get("character_id"))
        if is_boss_floor(state["floor"]):
            state["boss_kind"] = "necromancer"
            state["boss_name"] = "Некромант"
            state["boss_intro_lines"] = BOSS_INTRO_LINES
            state["enemies"] = [build_boss(player)]
        elif is_ultimate_boss_floor(state["floor"]):
            state["boss_kind"] = "daughter"
            state["boss_name"] = DAUGHTER_BOSS_NAME
            state["boss_intro_lines"] = DAUGHTER_INTRO_LINES
            state["enemies"] = [build_daughter_boss(player, state["floor"], state.get("character_id"))]
        else:
            state["boss_kind"] = "fallen"
            state["boss_name"] = None
            state["boss_intro_lines"] = None
            state["enemies"] = [build_boss(player)]
        return
    if _roll_cursed_floor(state["floor"]):
        state["cursed_ap_ratio"] = CURSED_AP_RATIO
    _refresh_turn_ap(state)
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
    character = get_character(state.get("character_id")) if state.get("character_id") else None

    is_rune_guard = _is_rune_guard(state)
    last_breath_active = _has_last_breath(state, player)
    is_duelist = _is_duelist(state)
    duel_active = _duelist_duel_active(state)
    assassin_shadow_active = _assassin_shadow_active(state, player)
    desperate_charge_active = _is_desperate_charge(state, player)
    base_accuracy = player["accuracy"]
    accuracy_bonus = _desperate_charge_accuracy_bonus(state, player)
    accuracy_bonus += _duelist_duel_accuracy_bonus(state, duel_active)
    effective_accuracy = _clamp(base_accuracy + accuracy_bonus, 0.0, 0.95)
    if last_breath_active or assassin_shadow_active:
        accuracy_display = "∞"
    elif accuracy_bonus > 0:
        accuracy_display = (
            f"{_percent(base_accuracy, show_percent=False)} "
            f"(эфф. {_percent(effective_accuracy, show_percent=False)})"
        )
    else:
        accuracy_display = _percent(base_accuracy, show_percent=False)

    base_evasion = player.get("evasion", 0.0)
    effective_evasion = _effective_evasion(base_evasion, state.get("floor"))
    if effective_evasion != base_evasion:
        evasion_text = f"{_percent(base_evasion)} (эфф. {_percent(effective_evasion)})"
    else:
        evasion_text = _percent(base_evasion)

    lines = [
        f"<b>Этаж:</b> {state['floor']}",
    ]
    if character:
        lines.append(f"<b>Герой:</b> {character['name']}")
    lines.extend(
        [
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
    )
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
    if _has_resolve(state, player):
        status_notes.append("Решимость — урон +20%")
    if _assassin_full_hp_bonus(state, player):
        status_notes.append("Безупречный удар — урон +40%")
    if assassin_shadow_active:
        status_notes.append("Последняя тень — игнор брони и уклонения")
    if _is_assassin(state) and not state.get("assassin_echo_used"):
        status_notes.append("Эхо убийства — готово")
    if _is_assassin(state):
        noun = potion_noun_plural(state.get("character_id"))
        status_notes.append(f"Мастер зельеварения — {noun} +2 HP")
    if is_duelist and duel_active:
        status_notes.append("Дуэль — урон +25%, точность +15%")
    if is_duelist and state.get("duel_turns_left"):
        turns_left = int(state.get("duel_turns_left", 0))
        status_notes.append(f"Дуэльная зона — {turns_left} ход.")
    if is_duelist and _duelist_virtuoso_active(state):
        status_notes.append("Виртуоз — дуэльная зона 3 заряда, парирование 60%")
    if is_duelist and not state.get("duelist_parry_used"):
        status_notes.append("Парирование — готово")
    if is_duelist and not state.get("duelist_blade_used"):
        status_notes.append("Клинок чести — бронепробой 25%")
    if _is_hunter(state) and not state.get("hunter_first_shot_used"):
        status_notes.append("Выверенный выстрел — +10% точности")
    if _is_hunter(state) and not state.get("hunter_kill_used"):
        status_notes.append("Гон по следу — +1 ОД за первое убийство")
    if _is_hunter(state) and any(enemy.get("hunter_mark") for enemy in state.get("enemies", [])):
        status_notes.append("Охотничья метка — активна")
    if _is_executioner(state):
        status_notes.append("Точность мясника — +20% к шансу кровотечения")
    if (
        _is_executioner(state)
        and not state.get("executioner_onslaught_used")
        and any(
            enemy.get("hp", 0) > 0 and enemy.get("bleed_turns", 0) > 0
            for enemy in state.get("enemies", [])
        )
    ):
        status_notes.append("Натиск — +1 ОД на следующую атаку")
    if _is_executioner(state):
        heals_left = max(0, 2 - int(state.get("executioner_heal_count", 0)))
        status_notes.append(f"Приговор — лечений {heals_left}/2")
    if _is_executioner(state):
        turns = int(state.get("executioner_last_breath_turns", 0))
        if turns > 0:
            status_notes.append(f"Цена смерти — {turns}/3")
    rage_state = _berserk_rage_state(state, player)
    if rage_state:
        rage_name, rage_bonus = rage_state
        status_notes.append(f"{rage_name} — урон +{int(round(rage_bonus * 100))}%")
    if is_rune_guard and desperate_charge_active:
        status_notes.append("Рывок Чести — 1-я атака 0 ОД, точность +25%")
    if last_breath_active:
        status_notes.append("На последнем издыхании — точность 100%")
    if state.get("rune_guard_shield_active"):
        status_notes.append("Щит Рун — броня +2")
    if state.get("rune_guard_retribution_ready"):
        status_notes.append("Каменный Ответ — бронепробой +30%")
    if state.get("ap_bonus"):
        status_notes.append("Стойкая Воля — ОД +1")
    if _is_berserk(state) and state.get("berserk_meat_turns", 0) > 0:
        status_notes.append("Сытая ярость — точность +30%")
    if _is_berserk(state) and not state.get("berserk_second_wind_used"):
        status_notes.append("Неистовая живучесть — готово")
    if _has_second_chance(player):
        status_notes.append("Амулет второго шанса — готов")
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
            duel_target = _duel_target(state)
            for enemy in enemies:
                name = enemy["name"]
                tags = []
                if enemy.get("hunter_mark"):
                    tags.append("метка")
                if duel_target is enemy:
                    tags.append("дуэль")
                if tags:
                    name = f"{name} ({', '.join(tags)})"
                lines.append(f"- <b>{name}</b>: {enemy['hp']}/{enemy['max_hp']} HP")
        else:
            lines.append("<i>Враги отсутствуют.</i>")
        info_lines = []
        if state.get("show_info"):
            info_lines = [
                "",
                *build_enemy_info_text(
                    state.get("enemies", []),
                    player,
                    state.get("floor", 1),
                    character_id=state.get("character_id"),
                ).splitlines(),
            ]
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
        show_splash = not _is_duelist(state)
        for idx, reward in enumerate(state.get("rewards", []), start=1):
            item = reward["item"]
            details = _format_reward_details(reward["type"], item, show_splash=show_splash)
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
            show_splash = not _is_duelist(state)
            details = _format_reward_details(reward["type"], item, show_splash=show_splash)
            lines.append("<b>Сундук древних раскрывает находку:</b>")
            lines.append(f"<b>{item['name']}</b> {details}")
            if reward["type"] == "weapon":
                current = player["weapon"]
                current_details = _format_reward_details("weapon", current, show_splash=show_splash)
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
        title = potion_menu_title(state.get("character_id"))
        lines.append(f"<b>{title}:</b>")
        small_heal, small_ap = _potion_stats(player, "potion_small")
        medium_heal, medium_ap = _potion_stats(player, "potion_medium")
        strong_heal, strong_ap = _potion_stats(player, "potion_strong")
        potion_bonus = _assassin_potion_bonus(state)
        if potion_bonus:
            small_heal += potion_bonus
            medium_heal += potion_bonus
            strong_heal += potion_bonus
        small_label = potion_label(state.get("character_id"), "potion_small", title=True)
        medium_label = potion_label(state.get("character_id"), "potion_medium", title=True)
        strong_label = potion_label(state.get("character_id"), "potion_strong", title=True)
        if small_count > 0:
            small_limit = POTION_LIMITS.get("potion_small", small_count)
            lines.append(
                f"{small_label}: <b>{small_count}/{small_limit}</b> (+{small_heal} HP, +{small_ap} ОД)"
            )
        if medium_count > 0:
            medium_limit = POTION_LIMITS.get("potion_medium", medium_count)
            lines.append(
                f"{medium_label}: <b>{medium_count}/{medium_limit}</b> (+{medium_heal} HP, +{medium_ap} ОД)"
            )
        if strong_count > 0 and not _is_executioner(state):
            strong_limit = POTION_LIMITS.get("potion_strong", strong_count)
            lines.append(
                f"{strong_label}: <b>{strong_count}/{strong_limit}</b> (+{strong_heal} HP, +{strong_ap} ОД)"
            )
        use_label = potion_use_label(state.get("character_id"))
        lines.append(f"<i>Выберите {use_label} для использования.</i>")
    elif state["phase"] == "inventory":
        lines.append("<b>Инвентарь:</b>")
        magic_damage = _magic_scroll_damage(state, player, ap_max=_effective_ap_max(state))
        if tutorial_active:
            config = state.get("tutorial_config", TUTORIAL_DEFAULT_CONFIG)
            magic_damage = int(config.get("scroll_hit", magic_damage))
        lines.append(f"<b>Магический урон:</b> {magic_damage} | <b>Стоимость:</b> 1 ОД")
        if _is_duelist(state):
            max_charges = _duelist_max_zone_charges(state)
            charges = int(state.get("duel_zone_charges", 0))
            lines.append(
                f"<b>Дуэльная зона:</b> {charges}/{max_charges} "
                f"(эффект {DUELIST_ZONE_TURNS} хода)",
            )
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
    elif state["phase"] == "run_tasks":
        lines.append("<b>Испытания руин:</b>")
        completed, total, _xp = run_tasks_summary(state)
        lines.append(f"<b>Прогресс:</b> {completed}/{total}")
        lines.append("<b>Награда:</b> +20 XP за задачу")
        lines.append("")
        task_lines = run_tasks_lines(state)
        if task_lines:
            lines.extend(task_lines)
        else:
            lines.append("<i>Испытания недоступны.</i>")
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
        lines.append("")
        parry_multiplier = 1.0
        if len(enemies) == 1 and _is_duelist(state) and not state.get("duelist_parry_used"):
            reduction = _duelist_parry_reduction(state, enemies[0])
            parry_multiplier = max(0.0, 1.0 - reduction)
        single_max_display = max(1, int(round(total_max * parry_multiplier)))
        if len(enemies) == 1:
            lines.append(
                f"<b>Сводка:</b> HP {player['hp']}/{player['hp_max']} | "
                f"урон врага: {single_max_display}"
            )
        else:
            expected_display = max(1, int(round(total_expected)))
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

def _format_reward_details(reward_type: str, item: Dict, show_splash: bool = True) -> str:
    if reward_type == "weapon":
        parts = [f"урон {item['min_dmg']}-{item['max_dmg']}"]
        if item.get("accuracy_bonus"):
            sign = "+" if item["accuracy_bonus"] > 0 else ""
            parts.append(f"точность {sign}{int(round(item['accuracy_bonus'] * 100))}%")
        if show_splash and item.get("splash_ratio"):
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
