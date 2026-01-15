from __future__ import annotations

import copy
import random
from typing import Dict, Tuple

from .data import SCROLLS, get_scroll_by_id, get_upgrade_by_id

POTION_LIMITS = {
    "potion_small": 10,
    "potion_medium": 5,
    "potion_strong": 2,
}


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
