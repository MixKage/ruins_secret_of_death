import copy
import random
from typing import Dict, List, Tuple

from .data import ENEMIES, UPGRADES, WEAPONS, get_upgrade_by_id


MAX_LOG_LINES = 4

ENEMY_DAMAGE_BUDGET_RATIO = 0.4
ENEMY_DAMAGE_BUDGET_RATIO_POST_BOSS = 0.6

LAST_BREATH_THRESHOLDS = [
    (3, 10),
    (6, 13),
    (9, 15),
]
LAST_BREATH_STEP = 2

BOSS_FLOOR = 10

BOSS_ARTIFACT_OPTIONS = [
    {
        "id": "artifact_hp",
        "name": "Печать крови",
        "effect": "+10 к макс. HP",
    },
    {
        "id": "artifact_ap",
        "name": "Печать воли",
        "effect": "+1 к макс. ОД",
    },
    {
        "id": "artifact_potions",
        "name": "Алхимический набор",
        "effect": "2 средних зелья",
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


def _append_log(state: Dict, message: str) -> None:
    state.setdefault("log", []).append(message)
    state["log"] = state["log"][-MAX_LOG_LINES:]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _percent(value: float) -> str:
    return f"{int(round(value * 100))}%"


def _enemy_damage_budget_ratio(floor: int) -> float:
    base = ENEMY_DAMAGE_BUDGET_RATIO_POST_BOSS if floor > BOSS_FLOOR else ENEMY_DAMAGE_BUDGET_RATIO
    if floor > 20:
        steps = (floor - 20) // 10
        base += 0.1 * steps
    return min(base, 1.0)


def _last_breath_threshold(floor: int) -> int:
    for max_floor, threshold in LAST_BREATH_THRESHOLDS:
        if floor <= max_floor:
            return threshold
    extra_zones = (floor - 10) // 3 + 1
    return LAST_BREATH_THRESHOLDS[-1][1] + extra_zones * LAST_BREATH_STEP


def _is_last_breath(player: Dict, floor: int) -> bool:
    return player["hp"] <= _last_breath_threshold(floor)


def _grant_small_potion(player: Dict) -> None:
    potion = copy.deepcopy(get_upgrade_by_id("potion_small"))
    if potion:
        player.setdefault("potions", []).append(potion)


def _grant_medium_potion(player: Dict, count: int = 1) -> None:
    potion = copy.deepcopy(get_upgrade_by_id("potion_medium"))
    if not potion:
        return
    for _ in range(count):
        player.setdefault("potions", []).append(copy.deepcopy(potion))


def _mutate_enemy_template(template: Dict) -> Dict:
    mutated = copy.deepcopy(template)
    name = mutated.get("name", "")
    if not name.startswith("Мутированный "):
        mutated["name"] = f"Мутированный {name}"
    mutated["base_hp"] = int(round(mutated.get("base_hp", 0) * 1.25))
    mutated["base_attack"] = mutated.get("base_attack", 0) * 1.2
    mutated["base_armor"] = mutated.get("base_armor", 0) * 1.1
    mutated["base_accuracy"] = _clamp(mutated.get("base_accuracy", 0.5) + 0.05, 0.4, 0.95)
    mutated["base_evasion"] = _clamp(mutated.get("base_evasion", 0.05) + 0.03, 0.02, 0.3)
    mutated["hp_per_floor"] = mutated.get("hp_per_floor", 0) * 1.15
    mutated["attack_per_floor"] = mutated.get("attack_per_floor", 0) * 1.2
    mutated["armor_per_floor"] = mutated.get("armor_per_floor", 0) * 1.15
    mutated["min_floor"] = BOSS_FLOOR + 1
    mutated["max_floor"] = 999
    info = mutated.get("info", "").strip()
    if info and "Мутировал" not in info:
        mutated["info"] = f"{info} Мутировал в глубине руин."
    elif not info:
        mutated["info"] = "Мутировал в глубине руин."
    return mutated


def _legendary_weapon(weapon: Dict) -> Dict:
    legendary = copy.deepcopy(weapon)
    name = legendary.get("name", "")
    if not name.startswith("Легендарный "):
        legendary["name"] = f"Легендарный {name}"
    legendary["min_dmg"] = legendary.get("min_dmg", 0) + 2
    legendary["max_dmg"] = legendary.get("max_dmg", 0) + 3
    legendary["accuracy_bonus"] = _clamp(legendary.get("accuracy_bonus", 0.0) + 0.05, -0.2, 0.3)
    legendary["splash_ratio"] = _clamp(legendary.get("splash_ratio", 0.0) + 0.05, 0.0, 0.5)
    legendary["bleed_chance"] = _clamp(legendary.get("bleed_chance", 0.0) + 0.05, 0.0, 0.6)
    legendary["bleed_damage"] = legendary.get("bleed_damage", 0) + (1 if legendary.get("bleed_chance", 0) > 0 else 0)
    legendary["armor_pierce"] = _clamp(legendary.get("armor_pierce", 0.0) + 0.05, 0.0, 0.6)
    return legendary


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
        return [_legendary_weapon(item) for item in WEAPONS]
    weapons = _filter_by_floor(WEAPONS, floor)
    return weapons or WEAPONS


def _enemies_for_floor(floor: int) -> List[Dict]:
    if floor > BOSS_FLOOR:
        base_pool = [item for item in ENEMIES if item.get("id") != "necromancer"]
        return [_mutate_enemy_template(item) for item in base_pool]
    enemies = _filter_by_floor(ENEMIES, floor)
    return enemies or ENEMIES


def _upgrades_for_floor(floor: int) -> List[Dict]:
    upgrades = _filter_by_floor(UPGRADES, floor)
    return upgrades or UPGRADES


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
        "effect": "Шанс на награду +2 этажа (зависит от удачи) + малое зелье",
    },
    {
        "id": "campfire",
        "name": "Костер паломника",
        "effect": "+2-3 к макс. HP + малое зелье",
    },
]


def is_boss_floor(floor: int) -> bool:
    return floor == BOSS_FLOOR


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
        "bleed_turns": 0,
        "bleed_damage": 0,
        "counted_dead": False,
        "info": "Создатель проклятия. Его слова пусты, но воля крепка.",
        "danger": "легендарная",
        "min_floor": BOSS_FLOOR,
        "max_floor": BOSS_FLOOR,
    }


def new_run_state() -> Dict:
    weapon = copy.deepcopy(random.choice(_weapons_for_floor(1)))
    potion = copy.deepcopy(get_upgrade_by_id("potion_small"))
    player = {
        "hp": 30,
        "hp_max": 30,
        "ap": 2,
        "ap_max": 2,
        "armor": 0.0,
        "accuracy": 0.7,
        "evasion": 0.05,
        "power": 1,
        "luck": 0.2,
        "weapon": weapon,
        "potions": [potion] if potion else [],
    }
    state = {
        "floor": 1,
        "phase": "battle",
        "player": player,
        "enemies": generate_enemy_group(1, player["hp_max"], player["ap_max"]),
        "rewards": [],
        "treasure_reward": None,
        "event_options": [],
        "boss_artifacts": [],
        "show_info": False,
        "kills": {},
        "treasures_found": 0,
        "chests_opened": 0,
        "boss_defeated": False,
        "log": [],
    }
    _append_log(state, f"Вы нашли <b>{weapon['name']}</b> и спускаетесь на этаж <b>1</b>.")
    return state


def _max_group_size_for_floor(floor: int) -> int:
    if floor <= 3:
        return 1
    if floor <= 6:
        return 2
    return 3


def generate_enemy_group(floor: int, player_hp_max: int, player_ap_max: int) -> List[Dict]:
    enemies = _enemies_for_floor(floor)
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
        group = [build_enemy(random.choice(enemies), floor) for _ in range(group_size)]
        if _enemy_group_within_budget(group, budget):
            return group

    group = [build_enemy(random.choice(enemies), floor) for _ in range(min_group)]
    _scale_group_attack_to_budget(group, budget)
    return group


def build_enemy(template: Dict, floor: int) -> Dict:
    max_hp = int(template["base_hp"] + template["hp_per_floor"] * floor)
    attack = template["base_attack"] + template["attack_per_floor"] * floor
    armor = template["base_armor"] + template["armor_per_floor"] * floor
    accuracy = _clamp(template["base_accuracy"] + floor * 0.01, 0.4, 0.95)
    evasion = _clamp(template["base_evasion"] + floor * 0.005, 0.02, 0.3)
    return {
        "id": template["id"],
        "name": template["name"],
        "hp": max_hp,
        "max_hp": max_hp,
        "attack": attack,
        "armor": armor,
        "accuracy": accuracy,
        "evasion": evasion,
        "bleed_turns": 0,
        "bleed_damage": 0,
        "counted_dead": False,
        "info": template.get("info", ""),
        "danger": template.get("danger", "неизвестна"),
        "min_floor": template.get("min_floor", 1),
        "max_floor": template.get("max_floor", 999),
    }


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


def roll_hit(attacker_accuracy: float, defender_evasion: float) -> bool:
    chance = _clamp(attacker_accuracy - defender_evasion, 0.15, 0.95)
    return random.random() < chance


def roll_damage(weapon: Dict, player: Dict, target: Dict) -> int:
    base = random.randint(weapon["min_dmg"], weapon["max_dmg"]) + player["power"]
    armor = max(0.0, target["armor"] * (1.0 - weapon["armor_pierce"]))
    dmg = int(max(1, base - armor))
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
    if not enemies:
        return "Справка недоступна: врагов нет."
    seen = set()
    lines = ["<b>Справка по противникам:</b>"]
    if player:
        lines.append("<i>Урон рассчитан с учетом ваших характеристик.</i>")
    for enemy in enemies:
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
            armor = player.get("armor", 0)
            hit_damage = max(1, int(round(attack - armor)))
            player_accuracy = player.get("accuracy", 0.0) + weapon.get("accuracy_bonus", 0.0)
            enemy_evasion = enemy.get("evasion", 0.0)
            if floor is not None and _is_last_breath(player, floor):
                hit_chance = 1.0
            else:
                hit_chance = _clamp(player_accuracy - enemy_evasion, 0.15, 0.95)
            hit_chance_pct = int(round(hit_chance * 100))
            damage_text = f"<b>Урон при попадании:</b> {hit_damage} | <b>Шанс попадания:</b> {hit_chance_pct}%"
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
    player["ap"] = player["ap_max"]
    enemy_phase(state)
    _tally_kills(state)
    check_battle_end(state)


def player_attack(state: Dict) -> None:
    player = state["player"]
    if player["ap"] <= 0:
        _append_log(state, "Нет ОД для атаки.")
        return

    player["ap"] -= 1
    weapon = player["weapon"]
    target = _first_alive(state["enemies"])
    if target is None:
        return

    last_breath = _is_last_breath(player, state["floor"])
    hit = True if last_breath else roll_hit(player["accuracy"] + weapon["accuracy_bonus"], target["evasion"])
    if hit:
        damage = roll_damage(weapon, player, target)
        target["hp"] -= damage
        _append_log(state, f"Вы наносите {damage} урона по {target['name']}.")

        if weapon["splash_ratio"] > 0:
            splash_targets = [enemy for enemy in state["enemies"] if enemy is not target and enemy["hp"] > 0]
            if splash_targets:
                splash_damage = max(1, int(damage * weapon["splash_ratio"]))
                for enemy in splash_targets:
                    enemy["hp"] -= splash_damage
                _append_log(state, f"Сплэш урон: {splash_damage} по всем оставшимся врагам.")

        if weapon["bleed_chance"] > 0 and random.random() < weapon["bleed_chance"]:
            target["bleed_turns"] = max(target["bleed_turns"], 2)
            target["bleed_damage"] = max(target["bleed_damage"], weapon["bleed_damage"])
            _append_log(state, f"{target['name']} истекает кровью.")
    else:
        _append_log(state, "Вы промахиваетесь.")

    check_battle_end(state)


def player_use_potion(state: Dict) -> None:
    player = state["player"]
    if not player["potions"]:
        _append_log(state, "Зелий нет.")
        return

    potion = player["potions"].pop()
    player["hp"] = min(player["hp_max"], player["hp"] + potion["heal"])
    player["ap"] = min(player["ap_max"], player["ap"] + potion["ap_restore"])
    _append_log(state, f"Вы используете зелье: +{potion['heal']} HP, +{potion['ap_restore']} ОД.")

    check_battle_end(state)


def enemy_phase(state: Dict) -> None:
    player = state["player"]
    enemies = _alive_enemies(state["enemies"])

    for enemy in list(enemies):
        if enemy["bleed_turns"] > 0:
            enemy["hp"] -= enemy["bleed_damage"]
            enemy["bleed_turns"] -= 1
            _append_log(state, f"{enemy['name']} теряет {enemy['bleed_damage']} HP от кровотечения.")

    _tally_kills(state)
    enemies = _alive_enemies(state["enemies"])
    if not enemies:
        return

    for enemy in enemies:
        if roll_hit(enemy["accuracy"], player["evasion"]):
            damage = max(1, int(enemy["attack"] - player["armor"]))
            player["hp"] -= damage
            _append_log(state, f"{enemy['name']} бьет вас на {damage} урона.")
        else:
            _append_log(state, f"{enemy['name']} промахивается.")
        if player["hp"] <= 0:
            player["hp"] = 0
            state["phase"] = "dead"
            _append_log(state, "<b>Вы падаете без сознания.</b> Забег окончен.")
            return


def check_battle_end(state: Dict) -> None:
    if state["phase"] == "dead":
        return
    _tally_kills(state)
    if not _alive_enemies(state["enemies"]):
        if state.get("floor") == BOSS_FLOOR and any(enemy.get("id") == "necromancer" for enemy in state.get("enemies", [])):
            state["boss_defeated"] = True
            _append_log(state, "<b>Некромант пал.</b> Руины на миг затихли.")
            _append_log(state, "Но зелье вечной жизни все еще не найдено — путь продолжается.")
        state["phase"] = "reward"
        state["rewards"] = generate_rewards(state["floor"])
        _append_log(state, f"<b>Этаж {state['floor']}</b> зачищен. Выберите награду.")


def generate_event_options() -> List[Dict]:
    return [copy.deepcopy(option) for option in EVENT_OPTIONS]


def generate_rewards(floor: int) -> List[Dict]:
    rewards = []
    used_ids = set()
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [
        ("upgrade", item) for item in _upgrades_for_floor(floor)
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


def generate_single_reward(floor: int) -> Dict:
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [
        ("upgrade", item) for item in _upgrades_for_floor(floor)
    ]
    reward_type, item = random.choice(pool)
    reward_item = copy.deepcopy(item)
    if reward_type == "weapon":
        scale_weapon_stats(reward_item, floor)
    return {"type": reward_type, "item": reward_item}


def apply_reward_item(state: Dict, reward: Dict) -> None:
    player = state["player"]
    if reward["type"] == "weapon":
        player["weapon"] = reward["item"]
        _append_log(state, f"Вы берете оружие: <b>{reward['item']['name']}</b>.")
    elif reward["type"] == "upgrade":
        upgrade = reward["item"]
        if upgrade["type"] == "stat":
            stat = upgrade["stat"]
            player[stat] = player.get(stat, 0) + upgrade["amount"]
            if stat == "hp_max":
                player["hp"] = min(player["hp_max"], player["hp"] + upgrade["amount"])
            _append_log(state, f"Апгрейд: <b>{upgrade['name']}</b>.")
        elif upgrade["type"] == "potion":
            player.setdefault("potions", []).append(upgrade)
            _append_log(state, f"Получено зелье: <b>{upgrade['name']}</b>.")

        if upgrade.get("stat") == "luck":
            player["luck"] = _clamp(player["luck"], 0.0, 0.8)


def prepare_event(state: Dict) -> None:
    state["phase"] = "event"
    state["event_options"] = generate_event_options()
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
    apply_reward_item(state, reward)
    next_floor = state.get("floor", 0) + 1
    if is_boss_floor(next_floor):
        advance_floor(state)
    else:
        prepare_event(state)


def apply_event_choice(state: Dict, event_id: str) -> None:
    player = state["player"]
    advance = True
    if event_id == "holy_spring":
        player["hp"] = player["hp_max"]
        _append_log(state, "Источник благодати полностью <b>исцеляет</b> вас.")
    elif event_id == "treasure_chest":
        state["chests_opened"] = state.get("chests_opened", 0) + 1
        chance = _clamp(player["luck"], 0.05, 0.8)
        if random.random() < chance:
            reward = generate_single_reward(state["floor"] + 2)
            _append_log(state, "Сундук раскрывает <b>редкую</b> находку.")
            state["phase"] = "treasure"
            state["treasure_reward"] = reward
            state["event_options"] = []
            state["treasures_found"] = state.get("treasures_found", 0) + 1
            advance = False
        else:
            _append_log(state, "<i>Сундук пуст. Удача отвернулась.</i>")
        _grant_small_potion(player)
        _append_log(state, "Вы находите <b>малое зелье</b>.")
    elif event_id == "campfire":
        bonus = random.randint(2, 3)
        player["hp_max"] += bonus
        player["hp"] += bonus
        _append_log(state, f"Костер укрепляет вас: <b>+{bonus}</b> к макс. HP.")
        _grant_small_potion(player)
        _append_log(state, "Вы находите <b>малое зелье</b>.")
    else:
        _append_log(state, "Неверный выбор комнаты.")

    if advance:
        advance_floor(state)


def apply_boss_artifact_choice(state: Dict, artifact_id: str) -> None:
    player = state["player"]
    if artifact_id == "artifact_hp":
        player["hp_max"] += 10
        player["hp"] += 10
        _append_log(state, "Артефакт крови наполняет вас: <b>+10</b> к макс. HP.")
    elif artifact_id == "artifact_ap":
        player["ap_max"] += 1
        _append_log(state, "Артефакт воли укрепляет дух: <b>+1</b> к макс. ОД.")
    elif artifact_id == "artifact_potions":
        _grant_medium_potion(player, count=2)
        _append_log(state, "Алхимический набор дарует <b>2 средних зелья</b>.")
    else:
        _append_log(state, "Вы не смогли выбрать артефакт.")

    player["hp"] = player["hp_max"]
    player["ap"] = player["ap_max"]
    state["boss_artifacts"] = []
    state["enemies"] = [build_boss(player)]
    state["phase"] = "battle"
    _append_log(state, "Вы распахиваете двери. Некромант поднимает посох.")


def apply_treasure_choice(state: Dict, equip: bool) -> None:
    reward = state.get("treasure_reward")
    if not reward:
        _append_log(state, "Награда сундука недоступна.")
        advance_floor(state)
        return
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
    player = state["player"]
    player["ap"] = player["ap_max"]
    if is_boss_floor(state["floor"]):
        player["hp"] = player["hp_max"]
        state["phase"] = "boss_prep"
        state["boss_artifacts"] = generate_boss_artifacts()
        state["enemies"] = [build_boss(player)]
        return
    state["phase"] = "battle"
    state["enemies"] = generate_enemy_group(state["floor"], player["hp_max"], player["ap_max"])
    _append_log(state, f"Вы спускаетесь на этаж <b>{state['floor']}</b>.")


def render_state(state: Dict) -> str:
    player = state["player"]
    weapon = player["weapon"]
    enemies = _alive_enemies(state["enemies"])

    last_breath_active = _is_last_breath(player, state["floor"])
    accuracy_value = 1.0 if last_breath_active else player["accuracy"]

    lines = [
        f"<b>Этаж:</b> {state['floor']}",
        f"<b>HP:</b> {player['hp']}/{player['hp_max']} | <b>ОД:</b> {player['ap']}/{player['ap_max']}",
        (
            f"<b>Точность:</b> {_percent(accuracy_value)} | "
            f"<b>Уклонение:</b> {_percent(player['evasion'])} | "
            f"<b>Броня:</b> {int(round(player['armor']))} | "
            f"<b>Удача:</b> {_percent(player.get('luck', 0.0))}"
        ),
        f"<b>Сила:</b> +{player.get('power', 0)} урона",
    ]
    if last_breath_active:
        lines.append("<b>Состояние:</b> <i>На последнем издыхании — точность 100%</i>")
    lines.extend([
        f"<b>Оружие:</b> <b>{weapon['name']}</b> (урон {weapon['min_dmg']}-{weapon['max_dmg']})",
        f"<b>Зелий:</b> {len(player.get('potions', []))}",
        "",
    ])

    if state["phase"] == "battle":
        if enemies:
            lines.append("<b>Враги:</b>")
            for enemy in enemies:
                lines.append(f"- <b>{enemy['name']}</b>: {enemy['hp']}/{enemy['max_hp']} HP")
        else:
            lines.append("<i>Враги отсутствуют.</i>")
        if state.get("show_info"):
            lines.append("")
            lines.append(build_enemy_info_text(state.get("enemies", []), player, state.get("floor", 1)))
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
        lines.extend(BOSS_INTRO_LINES)
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
    elif state["phase"] == "dead":
        lines.append("<b>Вы погибли.</b>")

    if state.get("log"):
        lines.append("")
        lines.append("<i>Последние события:</i>")
        lines.extend(state["log"])

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
    return ""
