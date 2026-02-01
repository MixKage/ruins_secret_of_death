from __future__ import annotations

from typing import Dict

from bot.config import is_test_mode

SECOND_CHANCE_STARS = 5
STARS_PACKAGES: Dict[int, Dict[str, int | str]] = {
    1: {"stars": 50, "label": "Уровень +1"},
    5: {"stars": 200, "label": "Уровень +5"},
}


def effective_stars(stars: int) -> int:
    return 1 if is_test_mode() else stars


def get_pack_price(levels: int) -> int:
    pack = STARS_PACKAGES.get(levels)
    if not pack:
        return 0
    return effective_stars(int(pack["stars"]))


def get_second_chance_price() -> int:
    return effective_stars(SECOND_CHANCE_STARS)
