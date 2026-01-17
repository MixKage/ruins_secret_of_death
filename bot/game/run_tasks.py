from __future__ import annotations

import copy
import random
from datetime import datetime, timezone
from typing import Dict, List, Tuple

TASK_XP = 10
TASK_WINDOW_SECONDS = 30 * 60

TASK_POOL: List[Dict] = [
    {
        "id": "kill_any_35",
        "title": "Убить 35 противников за забег",
        "type": "kill_any",
        "target": 35,
        "category": "combat",
    },
    {
        "id": "kill_any_45",
        "title": "Убить 45 противников за забег",
        "type": "kill_any",
        "target": 45,
        "category": "combat",
    },
    {
        "id": "kill_rotting_hound_10",
        "title": "Убить 10 гниющих псов за забег",
        "type": "kill_enemy",
        "enemy_id": "rotting_hound",
        "target": 10,
        "category": "combat",
    },
    {
        "id": "kill_goblin_10",
        "title": "Убить 10 гоблинов за забег",
        "type": "kill_enemy",
        "enemy_id": "cultist",
        "target": 10,
        "category": "combat",
    },
    {
        "id": "kill_skeleton_10",
        "title": "Убить 10 скелетов за забег",
        "type": "kill_enemy",
        "enemy_id": "skeleton",
        "target": 10,
        "category": "combat",
    },
    {
        "id": "kill_zombie_10",
        "title": "Убить 10 зомби за забег",
        "type": "kill_enemy",
        "enemy_id": "zombie",
        "target": 10,
        "category": "combat",
    },
    {
        "id": "kill_ghoul_8",
        "title": "Убить 8 упырей за забег",
        "type": "kill_enemy",
        "enemy_id": "ghoul",
        "target": 8,
        "category": "combat",
    },
    {
        "id": "kill_wraith_8",
        "title": "Убить 8 призраков за забег",
        "type": "kill_enemy",
        "enemy_id": "wraith",
        "target": 8,
        "category": "combat",
    },
    {
        "id": "kill_bone_knight_6",
        "title": "Убить 6 костяных рыцарей за забег",
        "type": "kill_enemy",
        "enemy_id": "bone_knight",
        "target": 6,
        "category": "combat",
    },
    {
        "id": "kill_blackmage_6",
        "title": "Убить 6 чернокнижников за забег",
        "type": "kill_enemy",
        "enemy_id": "plague_mage",
        "target": 6,
        "category": "combat",
    },
    {
        "id": "reach_floor_12",
        "title": "Добраться до 12-го этажа",
        "type": "reach_floor",
        "target": 12,
        "category": "milestone",
    },
    {
        "id": "reach_floor_15",
        "title": "Добраться до 15-го этажа",
        "type": "reach_floor",
        "target": 15,
        "category": "milestone",
    },
    {
        "id": "reach_floor_20",
        "title": "Добраться до 20-го этажа",
        "type": "reach_floor",
        "target": 20,
        "category": "milestone",
    },
    {
        "id": "kill_necromancer",
        "title": "Победить Некроманта",
        "type": "kill_boss",
        "boss_id": "necromancer",
        "target": 1,
        "category": "milestone",
    },
    {
        "id": "kill_fallen_hero",
        "title": "Победить Павшего героя",
        "type": "kill_boss",
        "boss_id": "fallen_hero",
        "target": 1,
        "category": "milestone",
    },
]


def current_task_window(now: datetime | None = None) -> int:
    moment = now or datetime.now(timezone.utc)
    return int(moment.timestamp() // TASK_WINDOW_SECONDS)


def build_run_tasks(window_id: int | None = None) -> Dict:
    window = int(window_id) if window_id is not None else current_task_window()
    rng = random.Random(window)
    combat_pool = [task for task in TASK_POOL if task.get("category") == "combat"]
    milestone_pool = [task for task in TASK_POOL if task.get("category") == "milestone"]
    used = set()
    tasks = []

    def pick(pool: List[Dict]) -> Dict | None:
        candidates = [task for task in pool if task.get("id") not in used]
        if not candidates:
            return None
        chosen = rng.choice(candidates)
        used.add(chosen.get("id"))
        entry = copy.deepcopy(chosen)
        entry["xp"] = int(entry.get("xp", TASK_XP))
        return entry

    tasks.append(pick(combat_pool))
    tasks.append(pick(combat_pool) or pick(milestone_pool))
    tasks.append(pick(milestone_pool) or pick(combat_pool))
    tasks = [task for task in tasks if task]
    return {
        "window_id": window,
        "tasks": tasks,
    }


def run_task_progress(state: Dict, task: Dict) -> Tuple[int, int, bool]:
    kills = state.get("kills", {}) or {}
    task_type = task.get("type")
    target = max(1, int(task.get("target", 1)))
    if task_type == "kill_any":
        current = sum(int(value) for value in kills.values())
    elif task_type == "kill_enemy":
        current = int(kills.get(task.get("enemy_id"), 0))
    elif task_type == "reach_floor":
        current = int(state.get("floor", 0))
    elif task_type == "kill_boss":
        boss_id = task.get("boss_id")
        current = 1 if kills.get(boss_id, 0) else 0
    else:
        current = 0
    done = current >= target
    return current, target, done


def run_tasks_summary(state: Dict) -> Tuple[int, int, int]:
    tasks = state.get("run_tasks", {}).get("tasks", [])
    completed = 0
    total_xp = 0
    for task in tasks:
        _current, _target, done = run_task_progress(state, task)
        if done:
            completed += 1
            total_xp += int(task.get("xp", TASK_XP))
    return completed, len(tasks), total_xp


def run_tasks_xp(state: Dict) -> int:
    _completed, _total, total_xp = run_tasks_summary(state)
    return total_xp


def run_tasks_lines(state: Dict) -> List[str]:
    tasks = state.get("run_tasks", {}).get("tasks", [])
    if not tasks:
        return []
    lines = []
    for task in tasks:
        current, target, done = run_task_progress(state, task)
        status = "[x]" if done else "[ ]"
        progress = min(current, target)
        title = task.get("title", "Испытание")
        lines.append(f"- {status} {title} ({progress}/{target})")
    return lines
