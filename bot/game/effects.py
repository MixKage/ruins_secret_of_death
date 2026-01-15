from __future__ import annotations

from typing import Dict


def _apply_burn(enemy: Dict, damage: int) -> None:
    enemy["burn_turns"] = max(enemy.get("burn_turns", 0), 1)
    enemy["burn_damage"] = max(enemy.get("burn_damage", 0), damage)


def _apply_freeze(enemy: Dict) -> None:
    enemy["skip_turns"] = max(enemy.get("skip_turns", 0), 1)
