from __future__ import annotations

from typing import Dict, List


def _alive_enemies(enemies: List[Dict]) -> List[Dict]:
    return [enemy for enemy in enemies if enemy["hp"] > 0]


def _tally_kills(state: Dict) -> None:
    kills = state.setdefault("kills", {})
    for enemy in state.get("enemies", []):
        if enemy["hp"] <= 0 and not enemy.get("counted_dead", False):
            enemy["counted_dead"] = True
            enemy_id = enemy.get("id", "unknown")
            kills[enemy_id] = kills.get(enemy_id, 0) + 1


def _first_alive(enemies: List[Dict]) -> Dict | None:
    for enemy in enemies:
        if enemy.get("hp", 0) > 0:
            return enemy
    return None
