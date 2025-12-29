from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bot import db


@dataclass(frozen=True)
class Badge:
    badge_id: str
    name: str
    seasonal: bool
    xp: int


BADGES: Dict[str, Badge] = {
    "season_top1": Badge("season_top1", "Корона Руин", True, 500),
    "season_top2": Badge("season_top2", "Костяной трон", True, 350),
    "season_top3": Badge("season_top3", "Серебро катакомб", True, 250),
    "season_top10": Badge("season_top10", "Зов глубин", True, 120),
    "season_most_kills": Badge("season_most_kills", "Кровь руин", True, 180),
    "season_most_chests": Badge("season_most_chests", "Собиратель праха", True, 180),
    "season_most_treasures": Badge("season_most_treasures", "Ловец реликвий", True, 180),
    "season_highest_floor": Badge("season_highest_floor", "Легенда спуска", True, 220),
    "season_most_runs": Badge("season_most_runs", "Несгибаемый", True, 150),
    db.PIONEER_BADGE_ID: Badge(db.PIONEER_BADGE_ID, "Первопроходец", False, 100),
}


LEVEL_BASE_XP = 100
LEVEL_STEP_XP = 25
PROGRESS_BAR_WIDTH = 12
SEASON_ZERO_KEY = "2025-12"
SEASON_ONE_YEAR = 2026
SEASON_ONE_MONTH = 1
SEASON_ZERO_START_DATE = datetime(2025, 12, 20, tzinfo=timezone.utc)
SEASON_ONE_START_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
LAST_PROCESSED_SETTING = "last_processed_season"
TREASURE_REWARD_XP = 5
SUMMARY_BADGES = [
    "season_top1",
    "season_top2",
    "season_top3",
    "season_most_kills",
    "season_most_chests",
    "season_most_treasures",
    "season_highest_floor",
    "season_most_runs",
]
MONTH_NAMES = {
    1: "январь",
    2: "февраль",
    3: "март",
    4: "апрель",
    5: "май",
    6: "июнь",
    7: "июль",
    8: "август",
    9: "сентябрь",
    10: "октябрь",
    11: "ноябрь",
    12: "декабрь",
}


def xp_to_level(xp: int) -> Tuple[int, int, int]:
    level = 1
    remaining = max(0, int(xp))
    while True:
        need = LEVEL_BASE_XP + LEVEL_STEP_XP * (level - 1)
        if remaining < need:
            return level, remaining, need
        remaining -= need
        level += 1


def progress_bar(current: int, total: int) -> str:
    if total <= 0:
        return "▮" * PROGRESS_BAR_WIDTH
    ratio = max(0.0, min(1.0, current / total))
    filled = int(round(ratio * PROGRESS_BAR_WIDTH))
    return "▮" * filled + "▯" * (PROGRESS_BAR_WIDTH - filled)


def _parse_season_key(season_key: str) -> tuple[int, int]:
    try:
        year_str, month_str = season_key.split("-", 1)
        return int(year_str), int(month_str)
    except (ValueError, AttributeError):
        return 1970, 1


def season_number(season_key: str) -> int:
    base_year, base_month = _parse_season_key(SEASON_ZERO_KEY)
    year, month = _parse_season_key(season_key)
    base_index = base_year * 12 + base_month
    index = year * 12 + month
    return max(0, index - base_index)


def season_label(season_key: str) -> str:
    return f"Сезон {season_number(season_key)}"


def season_month_label(season_key: str) -> str:
    year, month = _parse_season_key(season_key)
    month_name = MONTH_NAMES.get(month, str(month))
    return f"{month_name} {year}"


def season_key_for_number(number: int) -> str:
    base_year, base_month = _parse_season_key(SEASON_ZERO_KEY)
    base_index = base_year * 12 + base_month
    index = base_index + max(0, int(number))
    year = (index - 1) // 12
    month = index - year * 12
    return f"{year:04d}-{month:02d}"


def expected_season_number(now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    if current < SEASON_ZERO_START_DATE:
        return 0
    if current < SEASON_ONE_START_DATE:
        return 0
    year = current.year
    month = current.month
    expected = 1 + (year - SEASON_ONE_YEAR) * 12 + (month - SEASON_ONE_MONTH)
    return max(0, expected)


async def ensure_current_season() -> Tuple[int, str]:
    season_id, season_key, _prev = await db.get_or_create_current_season()
    return season_id, season_key


async def get_last_processed_season() -> int:
    value = await db.get_setting(LAST_PROCESSED_SETTING)
    if value is not None:
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
    season_id, season_key = await ensure_current_season()
    number = season_number(season_key)
    await db.set_setting(LAST_PROCESSED_SETTING, str(number))
    return number


async def set_last_processed_season(value: int) -> None:
    await db.set_setting(LAST_PROCESSED_SETTING, str(int(value)))


async def ensure_season_for_number(number: int) -> Tuple[int, str]:
    season_key = season_key_for_number(number)
    season = await db.get_season_by_key(season_key)
    if season:
        return season[0], season[1]
    season_id = await db.create_season(season_key)
    return season_id, season_key


async def advance_season_once() -> Tuple[int, str, int, str]:
    last_processed = await get_last_processed_season()
    closed_id, closed_key = await ensure_season_for_number(last_processed)
    active = await db.get_active_season()
    if active:
        await db.close_season(active[0])
    await db.close_season(closed_id)
    new_number = last_processed + 1
    new_id, new_key = await ensure_season_for_number(new_number)
    await db.reopen_season(new_id)
    await set_last_processed_season(new_number)
    return closed_id, closed_key, new_id, new_key


async def award_latest_closed_season_badges() -> str | None:
    last = await db.get_last_season(ended_only=True)
    if not last:
        return None
    season_id, season_key = last
    await award_season_badges(season_id, season_key)
    return season_key


async def award_current_season_badges() -> str:
    season_id, season_key = await ensure_current_season()
    await award_season_badges(season_id, season_key)
    return season_key


async def record_run_progress(user_id: int, state: Dict, died: bool | None = None) -> None:
    season_id, _ = await ensure_current_season()
    treasure_xp = int(state.get("treasure_xp", 0))
    if treasure_xp <= 0:
        treasure_xp = int(state.get("treasures_found", 0)) * TREASURE_REWARD_XP
    bonus_xp = treasure_xp
    state_with_bonus = dict(state)
    if bonus_xp > 0:
        state_with_bonus["xp_bonus"] = bonus_xp
    await db.record_season_stats(user_id, season_id, state_with_bonus, died=died)
    floor = int(state.get("floor", 0))
    total_xp = floor + bonus_xp
    if total_xp > 0:
        await db.add_user_xp(user_id, total_xp)


async def award_season_badges(season_id: int, season_key: str) -> None:
    rows = await db.get_season_stats_rows(season_id)
    if not rows:
        return

    def by_max_floor(item: dict) -> int:
        return int(item.get("max_floor", 0))

    def by_runs(item: dict) -> int:
        return int(item.get("total_runs", 0))

    def by_chests(item: dict) -> int:
        return int(item.get("chests_opened", 0))

    def by_treasures(item: dict) -> int:
        return int(item.get("treasures_found", 0))

    def by_kills(item: dict) -> int:
        return sum((item.get("kills") or {}).values())

    ranked = sorted(rows, key=lambda item: (-by_max_floor(item), item["user_id"]))
    top10 = ranked[:10]
    for idx, entry in enumerate(top10, start=1):
        if idx == 1:
            await _award_badge_with_xp(entry["user_id"], "season_top1", season_key)
        elif idx == 2:
            await _award_badge_with_xp(entry["user_id"], "season_top2", season_key)
        elif idx == 3:
            await _award_badge_with_xp(entry["user_id"], "season_top3", season_key)
        await _award_badge_with_xp(entry["user_id"], "season_top10", season_key)

    await _award_best(rows, season_key, by_kills, "season_most_kills")
    await _award_best(rows, season_key, by_chests, "season_most_chests")
    await _award_best(rows, season_key, by_treasures, "season_most_treasures")
    await _award_best(rows, season_key, by_max_floor, "season_highest_floor")
    await _award_best(rows, season_key, by_runs, "season_most_runs")


def compute_season_winners(rows: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    winners: Dict[str, List[int]] = {badge_id: [] for badge_id in SUMMARY_BADGES}
    if not rows:
        return winners

    def by_max_floor(item: dict) -> int:
        return int(item.get("max_floor", 0))

    def by_runs(item: dict) -> int:
        return int(item.get("total_runs", 0))

    def by_chests(item: dict) -> int:
        return int(item.get("chests_opened", 0))

    def by_treasures(item: dict) -> int:
        return int(item.get("treasures_found", 0))

    def by_kills(item: dict) -> int:
        return sum((item.get("kills") or {}).values())

    ranked = sorted(rows, key=lambda item: (-by_max_floor(item), item["user_id"]))
    if ranked:
        if len(ranked) >= 1:
            winners["season_top1"] = [ranked[0]["user_id"]]
        if len(ranked) >= 2:
            winners["season_top2"] = [ranked[1]["user_id"]]
        if len(ranked) >= 3:
            winners["season_top3"] = [ranked[2]["user_id"]]

    winners["season_most_kills"] = _best_winners(rows, by_kills)
    winners["season_most_chests"] = _best_winners(rows, by_chests)
    winners["season_most_treasures"] = _best_winners(rows, by_treasures)
    winners["season_highest_floor"] = _best_winners(rows, by_max_floor)
    winners["season_most_runs"] = _best_winners(rows, by_runs)
    return winners


def _best_winners(rows: Iterable[dict], metric) -> List[int]:
    best_value = None
    winners: List[int] = []
    for entry in rows:
        value = metric(entry)
        if best_value is None or value > best_value:
            best_value = value
            winners = [entry["user_id"]]
        elif value == best_value:
            winners.append(entry["user_id"])
    if best_value is None or best_value <= 0:
        return []
    return winners


async def _award_best(
    rows: Iterable[dict],
    season_key: str,
    metric,
    badge_id: str,
) -> None:
    best_value = None
    winners: List[int] = []
    for entry in rows:
        value = metric(entry)
        if best_value is None or value > best_value:
            best_value = value
            winners = [entry["user_id"]]
        elif value == best_value:
            winners.append(entry["user_id"])
    if best_value is None or best_value <= 0:
        return
    for user_id in winners:
        await _award_badge_with_xp(user_id, badge_id, season_key)


async def _award_badge_with_xp(user_id: int, badge_id: str, season_key: Optional[str]) -> None:
    badge = BADGES.get(badge_id)
    if not badge:
        return
    awarded = await db.award_badge(user_id, badge_id, season_key if badge.seasonal else None)
    if awarded and badge.xp:
        await db.add_user_xp(user_id, badge.xp)
