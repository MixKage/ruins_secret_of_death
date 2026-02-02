import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_json(filename: str, default):
    path = DATA_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, type(default)) else default


def load_weapons():
    return _load_json("weapons.json", [])


def load_enemies():
    return _load_json("enemies.json", [])


def load_upgrades():
    return _load_json("upgrades.json", [])


def load_treasures():
    return _load_json("chest_loot.json", [])


def load_scrolls():
    return _load_json("scrolls.json", [])


WEAPONS = load_weapons()
ENEMIES = load_enemies()
UPGRADES = load_upgrades()
CHEST_LOOT = load_treasures()
SCROLLS = load_scrolls()


def get_weapon_by_id(weapon_id: str):
    return next((item for item in WEAPONS if item["id"] == weapon_id), None)


def get_upgrade_by_id(upgrade_id: str):
    return next((item for item in UPGRADES if item["id"] == upgrade_id), None)


def get_treasure_by_id(treasure_id: str):
    return next((item for item in CHEST_LOOT if item.get("id") == treasure_id), None)


def get_scroll_by_id(scroll_id: str):
    return next((item for item in SCROLLS if item.get("id") == scroll_id), None)
