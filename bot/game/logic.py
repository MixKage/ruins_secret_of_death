import copy
import random
from typing import Dict, List, Tuple

from .data import ENEMIES, UPGRADES, WEAPONS, get_upgrade_by_id


MAX_LOG_LINES = 4


def _append_log(state: Dict, message: str) -> None:
    state.setdefault("log", []).append(message)
    state["log"] = state["log"][-MAX_LOG_LINES:]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _percent(value: float) -> str:
    return f"{int(round(value * 100))}%"


def _filter_by_floor(items: List[Dict], floor: int) -> List[Dict]:
    filtered = []
    for item in items:
        min_floor = item.get("min_floor", 1)
        max_floor = item.get("max_floor", 999)
        if min_floor <= floor <= max_floor:
            filtered.append(item)
    return filtered


def _weapons_for_floor(floor: int) -> List[Dict]:
    weapons = _filter_by_floor(WEAPONS, floor)
    return weapons or WEAPONS


def _enemies_for_floor(floor: int) -> List[Dict]:
    enemies = _filter_by_floor(ENEMIES, floor)
    return enemies or ENEMIES


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
        "effect": "Шанс на награду +2 этажа (зависит от удачи)",
    },
    {
        "id": "campfire",
        "name": "Костер паломника",
        "effect": "+2-3 к макс. HP",
    },
]


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
        "luck": 0.0,
        "weapon": weapon,
        "potions": [potion] if potion else [],
    }
    state = {
        "floor": 1,
        "phase": "battle",
        "player": player,
        "enemies": generate_enemy_group(1),
        "rewards": [],
        "event_options": [],
        "log": [],
    }
    _append_log(state, f"Вы нашли {weapon['name']} и спускаетесь на этаж 1.")
    return state


def generate_enemy_group(floor: int) -> List[Dict]:
    template = random.choice(_enemies_for_floor(floor))
    group_size = random.randint(template["group_min"], template["group_max"])
    if floor >= 3 and group_size < template["group_max"]:
        group_size += random.choice([0, 1])
    enemies = [build_enemy(template, floor) for _ in range(group_size)]
    return enemies


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
    }


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


def _first_alive(enemies: List[Dict]) -> Dict:
    for enemy in enemies:
        if enemy["hp"] > 0:
            return enemy
    return None


def end_turn(state: Dict) -> None:
    if state["phase"] != "battle":
        return
    player = state["player"]
    player["ap"] = player["ap_max"]
    enemy_phase(state)
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

    hit = roll_hit(player["accuracy"] + weapon["accuracy_bonus"], target["evasion"])
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
            _append_log(state, "Вы падаете без сознания. Забег окончен.")
            return


def check_battle_end(state: Dict) -> None:
    if state["phase"] == "dead":
        return
    if not _alive_enemies(state["enemies"]):
        state["phase"] = "reward"
        state["rewards"] = generate_rewards(state["floor"])
        _append_log(state, f"Этаж {state['floor']} зачищен. Выберите награду.")


def generate_event_options() -> List[Dict]:
    return [copy.deepcopy(option) for option in EVENT_OPTIONS]


def generate_rewards(floor: int) -> List[Dict]:
    rewards = []
    used_ids = set()
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [("upgrade", item) for item in UPGRADES]
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
    pool = [("weapon", item) for item in _weapons_for_floor(floor)] + [("upgrade", item) for item in UPGRADES]
    reward_type, item = random.choice(pool)
    reward_item = copy.deepcopy(item)
    if reward_type == "weapon":
        scale_weapon_stats(reward_item, floor)
    return {"type": reward_type, "item": reward_item}


def apply_reward_item(state: Dict, reward: Dict) -> None:
    player = state["player"]
    if reward["type"] == "weapon":
        player["weapon"] = reward["item"]
        _append_log(state, f"Вы берете оружие: {reward['item']['name']}.")
    elif reward["type"] == "upgrade":
        upgrade = reward["item"]
        if upgrade["type"] == "stat":
            stat = upgrade["stat"]
            player[stat] = player.get(stat, 0) + upgrade["amount"]
            if stat == "hp_max":
                player["hp"] = min(player["hp_max"], player["hp"] + upgrade["amount"])
            _append_log(state, f"Апгрейд: {upgrade['name']}.")
        elif upgrade["type"] == "potion":
            player.setdefault("potions", []).append(upgrade)
            _append_log(state, f"Получено зелье: {upgrade['name']}.")

        if upgrade.get("stat") == "luck":
            player["luck"] = _clamp(player["luck"], 0.0, 0.8)


def prepare_event(state: Dict) -> None:
    state["phase"] = "event"
    state["event_options"] = generate_event_options()
    _append_log(state, "Между этажами вы находите развилку.")


def apply_reward(state: Dict, reward_index: int) -> None:
    rewards = state.get("rewards", [])
    if reward_index < 0 or reward_index >= len(rewards):
        _append_log(state, "Неверный выбор награды.")
        return

    reward = rewards[reward_index]
    apply_reward_item(state, reward)
    prepare_event(state)


def apply_event_choice(state: Dict, event_id: str) -> None:
    player = state["player"]
    if event_id == "holy_spring":
        player["hp"] = player["hp_max"]
        _append_log(state, "Источник благодати полностью исцеляет вас.")
    elif event_id == "treasure_chest":
        chance = _clamp(0.2 + player["luck"], 0.05, 0.8)
        if random.random() < chance:
            reward = generate_single_reward(state["floor"] + 2)
            _append_log(state, "Сундук раскрывает редкую находку.")
            apply_reward_item(state, reward)
        else:
            _append_log(state, "Сундук пуст. Удача отвернулась.")
    elif event_id == "campfire":
        bonus = random.randint(2, 3)
        player["hp_max"] += bonus
        player["hp"] += bonus
        _append_log(state, f"Костер укрепляет вас: +{bonus} к макс. HP.")
    else:
        _append_log(state, "Неверный выбор комнаты.")

    advance_floor(state)


def advance_floor(state: Dict) -> None:
    state["floor"] += 1
    state["phase"] = "battle"
    state["rewards"] = []
    state["event_options"] = []
    state["enemies"] = generate_enemy_group(state["floor"])
    player = state["player"]
    player["ap"] = player["ap_max"]
    player["hp"] = player["hp_max"]
    _append_log(state, f"Вы спускаетесь на этаж {state['floor']}.")


def render_state(state: Dict) -> str:
    player = state["player"]
    weapon = player["weapon"]
    enemies = _alive_enemies(state["enemies"])

    lines = [
        f"Этаж: {state['floor']}",
        f"HP: {player['hp']}/{player['hp_max']} | ОД: {player['ap']}/{player['ap_max']}",
        (
            f"Точность: {_percent(player['accuracy'])} | "
            f"Уклонение: {_percent(player['evasion'])} | "
            f"Броня: {player['armor']} | "
            f"Удача: {_percent(player.get('luck', 0.0))}"
        ),
        f"Оружие: {weapon['name']} (урон {weapon['min_dmg']}-{weapon['max_dmg']})",
        f"Зелий: {len(player.get('potions', []))}",
        "",
    ]

    if state["phase"] == "battle":
        if enemies:
            lines.append("Враги:")
            for enemy in enemies:
                lines.append(f"- {enemy['name']}: {enemy['hp']}/{enemy['max_hp']} HP")
        else:
            lines.append("Враги отсутствуют.")
    elif state["phase"] == "reward":
        lines.append("Награды:")
        for idx, reward in enumerate(state.get("rewards", []), start=1):
            item = reward["item"]
            details = _format_reward_details(reward["type"], item)
            lines.append(f"{idx}. {item['name']} {details}")
    elif state["phase"] == "event":
        lines.append("Комнаты между этажами:")
        for idx, option in enumerate(state.get("event_options", []), start=1):
            lines.append(f"{idx}. {option['name']} — {option['effect']}")
    elif state["phase"] == "dead":
        lines.append("Вы погибли.")

    if state.get("log"):
        lines.append("")
        lines.append("Последние события:")
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
            parts.append(f"кровотечение {int(round(item['bleed_chance'] * 100))}%/{item['bleed_damage']}")
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
