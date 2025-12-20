import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_json(filename: str):
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_weapons():
    return _load_json("weapons.json")


def load_enemies():
    return _load_json("enemies.json")


def load_upgrades():
    return _load_json("upgrades.json")


WEAPONS = load_weapons()
ENEMIES = load_enemies()
UPGRADES = load_upgrades()


def get_weapon_by_id(weapon_id: str):
    return next((item for item in WEAPONS if item["id"] == weapon_id), None)


def get_upgrade_by_id(upgrade_id: str):
    return next((item for item in UPGRADES if item["id"] == upgrade_id), None)
