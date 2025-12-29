import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "ruins.db"
PIONEER_BADGE_ID = "first_pioneer"
PIONEER_BADGE_CUTOFF = "2026-01-01"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                max_floor INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                max_floor INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                state_json TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                total_runs INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                deaths_by_floor TEXT DEFAULT "{}",
                kills_json TEXT DEFAULT "{}",
                treasures_found INTEGER DEFAULT 0,
                chests_opened INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS user_broadcasts (
                user_id INTEGER NOT NULL,
                broadcast_key TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, broadcast_key),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_key TEXT UNIQUE NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS user_season_stats (
                user_id INTEGER NOT NULL,
                season_id INTEGER NOT NULL,
                max_floor INTEGER DEFAULT 0,
                total_runs INTEGER DEFAULT 0,
                kills_json TEXT DEFAULT "{}",
                treasures_found INTEGER DEFAULT 0,
                chests_opened INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, season_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(season_id) REFERENCES seasons(id)
            );

            CREATE TABLE IF NOT EXISTS user_badges (
                user_id INTEGER NOT NULL,
                badge_id TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_awarded_season TEXT,
                last_awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, badge_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            """
        )
        await _ensure_user_columns(db)
        await db.execute(
            "INSERT OR IGNORE INTO user_badges (user_id, badge_id, count, last_awarded_season) "
            "SELECT id, ?, 1, NULL FROM users WHERE DATE(created_at) < DATE(?)",
            (PIONEER_BADGE_ID, PIONEER_BADGE_CUTOFF),
        )
        await db.commit()


async def _ensure_user_columns(db: aiosqlite.Connection) -> None:
    cursor = await db.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "xp" not in columns:
        await db.execute("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0")
        await db.commit()


def _current_season_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def get_or_create_current_season() -> Tuple[int, str, Optional[Tuple[int, str]]]:
    season_key = _current_season_key()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM seasons WHERE season_key = ?", (season_key,))
        row = await cursor.fetchone()
        if row:
            return row[0], season_key, None
        cursor = await db.execute(
            "SELECT id, season_key FROM seasons WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        prev = await cursor.fetchone()
        if prev:
            await db.execute(
                "UPDATE seasons SET ended_at = CURRENT_TIMESTAMP WHERE id = ?",
                (prev[0],),
            )
        cursor = await db.execute(
            "INSERT INTO seasons (season_key) VALUES (?)",
            (season_key,),
        )
        await db.commit()
        prev_info = (prev[0], prev[1]) if prev else None
        return cursor.lastrowid, season_key, prev_info


async def get_last_season(ended_only: bool = False) -> Optional[Tuple[int, str]]:
    async with aiosqlite.connect(DB_PATH) as db:
        if ended_only:
            cursor = await db.execute(
                "SELECT id, season_key FROM seasons "
                "WHERE ended_at IS NOT NULL ORDER BY started_at DESC LIMIT 1"
            )
        else:
            cursor = await db.execute(
                "SELECT id, season_key FROM seasons ORDER BY started_at DESC LIMIT 1"
            )
        row = await cursor.fetchone()
        if not row:
            return None
        return row[0], row[1]


async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, xp, created_at FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        username, xp, created_at = row
        return {
            "username": username,
            "xp": int(xp or 0),
            "created_at": created_at,
        }


async def add_user_xp(user_id: int, amount: int) -> None:
    if amount <= 0:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET xp = COALESCE(xp, 0) + ? WHERE id = ?",
            (amount, user_id),
        )
        await db.commit()


async def get_user_season_stats(user_id: int, season_id: int) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT max_floor, total_runs, kills_json, treasures_found, chests_opened "
            "FROM user_season_stats WHERE user_id = ? AND season_id = ?",
            (user_id, season_id),
        )
        row = await cursor.fetchone()
        if not row:
            return {
                "max_floor": 0,
                "total_runs": 0,
                "kills": {},
                "treasures_found": 0,
                "chests_opened": 0,
            }
        max_floor, total_runs, kills_json, treasures_found, chests_opened = row
        return {
            "max_floor": max_floor or 0,
            "total_runs": total_runs or 0,
            "kills": json.loads(kills_json or "{}"),
            "treasures_found": treasures_found or 0,
            "chests_opened": chests_opened or 0,
        }


async def record_season_stats(
    user_id: int,
    season_id: int,
    state: Dict[str, Any],
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_season_stats (user_id, season_id) VALUES (?, ?)",
            (user_id, season_id),
        )
        cursor = await db.execute(
            "SELECT max_floor, total_runs, kills_json, treasures_found, chests_opened "
            "FROM user_season_stats WHERE user_id = ? AND season_id = ?",
            (user_id, season_id),
        )
        row = await cursor.fetchone()
        max_floor, total_runs, kills_json, treasures_found, chests_opened = row or (0, 0, "{}", 0, 0)

        max_floor = max(max_floor or 0, int(state.get("floor", 0)))
        total_runs = (total_runs or 0) + 1
        kills = json.loads(kills_json or "{}")
        treasures_found = (treasures_found or 0) + int(state.get("treasures_found", 0))
        chests_opened = (chests_opened or 0) + int(state.get("chests_opened", 0))

        for enemy_id, count in (state.get("kills", {}) or {}).items():
            kills[enemy_id] = kills.get(enemy_id, 0) + int(count)

        await db.execute(
            "UPDATE user_season_stats SET max_floor = ?, total_runs = ?, kills_json = ?, "
            "treasures_found = ?, chests_opened = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND season_id = ?",
            (
                max_floor,
                total_runs,
                json.dumps(kills),
                treasures_found,
                chests_opened,
                user_id,
                season_id,
            ),
        )
        await db.commit()


async def get_season_leaderboard_total(season_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM user_season_stats WHERE season_id = ? AND max_floor > 0",
            (season_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def get_season_leaderboard_page(season_id: int, limit: int, offset: int) -> List[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT users.username, user_season_stats.max_floor "
            "FROM user_season_stats "
            "JOIN users ON users.id = user_season_stats.user_id "
            "WHERE user_season_stats.season_id = ? "
            "ORDER BY user_season_stats.max_floor DESC, users.username ASC "
            "LIMIT ? OFFSET ?",
            (season_id, limit, offset),
        )
        return await cursor.fetchall()


async def get_user_season_rank(user_id: int, season_id: int) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT rank FROM ("
            "SELECT user_id, ROW_NUMBER() OVER (ORDER BY max_floor DESC, user_id ASC) AS rank "
            "FROM user_season_stats WHERE season_id = ? AND max_floor > 0"
            ") WHERE user_id = ?",
            (season_id, user_id),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else None


async def get_season_stats_rows(season_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, max_floor, total_runs, kills_json, treasures_found, chests_opened "
            "FROM user_season_stats WHERE season_id = ?",
            (season_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            user_id, max_floor, total_runs, kills_json, treasures_found, chests_opened = row
            results.append(
                {
                    "user_id": user_id,
                    "max_floor": max_floor or 0,
                    "total_runs": total_runs or 0,
                    "kills": json.loads(kills_json or "{}"),
                    "treasures_found": treasures_found or 0,
                    "chests_opened": chests_opened or 0,
                }
            )
        return results


async def get_user_badges(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT badge_id, count, last_awarded_season FROM user_badges WHERE user_id = ?",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [
            {"badge_id": badge_id, "count": count or 0, "last_awarded_season": last_awarded_season}
            for badge_id, count, last_awarded_season in rows
        ]


async def award_badge(
    user_id: int,
    badge_id: str,
    season_key: Optional[str] = None,
) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT count, last_awarded_season FROM user_badges WHERE user_id = ? AND badge_id = ?",
            (user_id, badge_id),
        )
        row = await cursor.fetchone()
        if row:
            count, last_awarded_season = row
            if season_key and last_awarded_season == season_key:
                return False
            new_count = (count or 0) + 1
            await db.execute(
                "UPDATE user_badges SET count = ?, last_awarded_season = ?, "
                "last_awarded_at = CURRENT_TIMESTAMP WHERE user_id = ? AND badge_id = ?",
                (new_count, season_key, user_id, badge_id),
            )
        else:
            await db.execute(
                "INSERT INTO user_badges (user_id, badge_id, count, last_awarded_season) "
                "VALUES (?, ?, 1, ?)",
                (user_id, badge_id, season_key),
            )
        await db.commit()
        return True
        await db.commit()


async def ensure_user(telegram_id: int, username: Optional[str]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
            (telegram_id, username),
        )
        await db.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        user_id = row[0]
        cursor = await db.execute(
            "SELECT created_at FROM users WHERE id = ?",
            (user_id,),
        )
        created_row = await cursor.fetchone()
        created_at = created_row[0] if created_row else None
        if created_at:
            await db.execute(
                "INSERT OR IGNORE INTO user_badges (user_id, badge_id, count, last_awarded_season) "
                "SELECT ?, ?, 1, NULL WHERE DATE(?) < DATE(?)",
                (user_id, PIONEER_BADGE_ID, created_at, PIONEER_BADGE_CUTOFF),
            )
        await db.commit()
        return user_id


async def get_user(user_id: int) -> Optional[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, telegram_id, username, max_floor FROM users WHERE id = ?",
            (user_id,),
        )
        return await cursor.fetchone()


async def get_user_by_telegram(telegram_id: int) -> Optional[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, telegram_id, username, max_floor FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return await cursor.fetchone()


async def get_active_run(user_id: int) -> Optional[Tuple[int, Dict[str, Any]]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, state_json FROM runs WHERE user_id = ? AND is_active = 1 ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        run_id, state_json = row
        return run_id, json.loads(state_json)


async def create_run(user_id: int, state: Dict[str, Any]) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO runs (user_id, state_json, max_floor, is_active) VALUES (?, ?, ?, 1)",
            (user_id, json.dumps(state), state.get("floor", 0)),
        )
        await db.commit()
        return cursor.lastrowid


async def update_run(run_id: int, state: Dict[str, Any]) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE runs SET state_json = ?, max_floor = ? WHERE id = ?",
            (json.dumps(state), state.get("floor", 0), run_id),
        )
        await db.commit()


async def finish_run(run_id: int, final_floor: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE runs SET is_active = 0, ended_at = CURRENT_TIMESTAMP, max_floor = ? WHERE id = ?",
            (final_floor, run_id),
        )
        await db.commit()


async def update_user_max_floor(user_id: int, floor: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET max_floor = MAX(max_floor, ?) WHERE id = ?",
            (floor, user_id),
        )
        await db.commit()


async def get_leaderboard(limit: int = 10) -> List[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, max_floor FROM users ORDER BY max_floor DESC, username ASC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_leaderboard_page(limit: int, offset: int) -> List[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username, max_floor FROM users "
            "ORDER BY max_floor DESC, username ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()


async def get_leaderboard_total() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def get_last_run(user_id: int) -> Optional[Tuple[int, int, Dict[str, Any]]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, max_floor, state_json FROM runs "
            "WHERE user_id = ? ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        run_id, max_floor, state_json = row
        state = json.loads(state_json) if state_json else {}
        return run_id, max_floor, state


async def get_leaderboard_with_ids(limit: int = 10) -> List[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, username, max_floor FROM users "
            "ORDER BY max_floor DESC, username ASC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_season_leaderboard_with_ids(season_id: int, limit: int = 10) -> List[Tuple]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT users.id, users.username, user_season_stats.max_floor "
            "FROM user_season_stats "
            "JOIN users ON users.id = user_season_stats.user_id "
            "WHERE user_season_stats.season_id = ? AND user_season_stats.max_floor > 0 "
            "ORDER BY user_season_stats.max_floor DESC, users.username ASC LIMIT ?",
            (season_id, limit),
        )
        return await cursor.fetchall()


async def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT total_runs, deaths, deaths_by_floor, kills_json, treasures_found, chests_opened "
            "FROM user_stats WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        total_runs, deaths, deaths_by_floor, kills_json, treasures_found, chests_opened = row
        return {
            "total_runs": total_runs or 0,
            "deaths": deaths or 0,
            "deaths_by_floor": json.loads(deaths_by_floor or "{}"),
            "kills": json.loads(kills_json or "{}"),
            "treasures_found": treasures_found or 0,
            "chests_opened": chests_opened or 0,
        }


async def record_run_stats(user_id: int, state: Dict[str, Any], died: bool) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)",
            (user_id,),
        )
        cursor = await db.execute(
            "SELECT total_runs, deaths, deaths_by_floor, kills_json, treasures_found, chests_opened "
            "FROM user_stats WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        total_runs, deaths, deaths_by_floor, kills_json, treasures_found, chests_opened = row or (0, 0, "{}", "{}", 0, 0)

        total_runs = (total_runs or 0) + 1
        deaths = deaths or 0
        deaths_by_floor = json.loads(deaths_by_floor or "{}")
        kills = json.loads(kills_json or "{}")
        treasures_found = (treasures_found or 0) + int(state.get("treasures_found", 0))
        chests_opened = (chests_opened or 0) + int(state.get("chests_opened", 0))

        if died:
            deaths += 1
            floor = str(state.get("floor", 0))
            deaths_by_floor[floor] = deaths_by_floor.get(floor, 0) + 1

        for enemy_id, count in (state.get("kills", {}) or {}).items():
            kills[enemy_id] = kills.get(enemy_id, 0) + int(count)

        await db.execute(
            "UPDATE user_stats SET total_runs = ?, deaths = ?, deaths_by_floor = ?, "
            "kills_json = ?, treasures_found = ?, chests_opened = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ?",
            (
                total_runs,
                deaths,
                json.dumps(deaths_by_floor),
                json.dumps(kills),
                treasures_found,
                chests_opened,
                user_id,
            ),
        )
        await db.commit()

async def get_broadcast_targets(broadcast_key: str) -> List[Tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, telegram_id FROM users WHERE id NOT IN ("
            "SELECT user_id FROM user_broadcasts WHERE broadcast_key = ?)",
            (broadcast_key,),
        )
        return await cursor.fetchall()


async def get_all_user_targets() -> List[Tuple[int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, telegram_id FROM users")
        return await cursor.fetchall()


async def mark_broadcast_sent(user_id: int, broadcast_key: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_broadcasts (user_id, broadcast_key) VALUES (?, ?)",
            (user_id, broadcast_key),
        )
        await db.commit()


async def get_admin_stats(broadcast_key: Optional[str] = None) -> Dict[str, object]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        total_users = int(row[0]) if row else 0

        cursor = await db.execute("SELECT COUNT(*) FROM runs WHERE is_active = 1")
        row = await cursor.fetchone()
        active_runs = int(row[0]) if row else 0

        cursor = await db.execute("SELECT COUNT(*) FROM runs")
        row = await cursor.fetchone()
        total_runs = int(row[0]) if row else 0

        cursor = await db.execute(
            "SELECT COALESCE(SUM(deaths), 0), COALESCE(SUM(treasures_found), 0), "
            "COALESCE(SUM(chests_opened), 0) FROM user_stats"
        )
        row = await cursor.fetchone()
        total_deaths = int(row[0]) if row else 0
        total_treasures = int(row[1]) if row else 0
        total_chests = int(row[2]) if row else 0

        cursor = await db.execute("SELECT COALESCE(MAX(max_floor), 0) FROM users")
        row = await cursor.fetchone()
        max_floor = int(row[0]) if row else 0

        cursor = await db.execute(
            "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM runs "
            "WHERE started_at >= datetime('now', '-1 day')"
        )
        row = await cursor.fetchone()
        runs_24h = int(row[0]) if row else 0
        users_24h = int(row[1]) if row else 0

        cursor = await db.execute("SELECT deaths_by_floor FROM user_stats")
        rows = await cursor.fetchall()
        weighted_sum = 0
        death_total = 0
        for (deaths_by_floor,) in rows:
            data = json.loads(deaths_by_floor or "{}")
            for floor_str, count in data.items():
                try:
                    floor = int(floor_str)
                except (TypeError, ValueError):
                    continue
                count_int = int(count)
                weighted_sum += floor * count_int
                death_total += count_int
        avg_death_floor = (weighted_sum / death_total) if death_total else 0.0

        cursor = await db.execute("SELECT user_id, kills_json FROM user_stats")
        rows = await cursor.fetchall()
        kill_totals = []
        user_ids = []
        for user_id, kills_json in rows:
            kills = json.loads(kills_json or "{}")
            total_kills = sum(int(value) for value in kills.values())
            if total_kills > 0:
                kill_totals.append((user_id, total_kills))
                user_ids.append(user_id)

        username_map = {}
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            cursor = await db.execute(
                f"SELECT id, username FROM users WHERE id IN ({placeholders})",
                tuple(user_ids),
            )
            for user_id, username in await cursor.fetchall():
                username_map[user_id] = username

        top_killers = sorted(kill_totals, key=lambda item: item[1], reverse=True)[:3]
        top_killers = [
            (username_map.get(user_id) or "Без имени", total)
            for user_id, total in top_killers
        ]

        broadcast_sent = 0
        if broadcast_key:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM user_broadcasts WHERE broadcast_key = ?",
                (broadcast_key,),
            )
            row = await cursor.fetchone()
            broadcast_sent = int(row[0]) if row else 0
        broadcast_pending = max(0, total_users - broadcast_sent)

        return {
            "total_users": total_users,
            "active_runs": active_runs,
            "total_runs": total_runs,
            "total_deaths": total_deaths,
            "total_treasures": total_treasures,
            "total_chests": total_chests,
            "max_floor": max_floor,
            "runs_24h": runs_24h,
            "users_24h": users_24h,
            "avg_death_floor": avg_death_floor,
            "top_killers": top_killers,
            "broadcast_sent": broadcast_sent,
            "broadcast_pending": broadcast_pending,
        }

async def get_random_boss_name(min_floor: int = 10) -> Optional[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT username FROM users "
            "WHERE username IS NOT NULL AND TRIM(username) != '' AND max_floor >= ? "
            "ORDER BY RANDOM() LIMIT 1",
            (min_floor,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None
