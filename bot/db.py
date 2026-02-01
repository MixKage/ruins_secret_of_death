import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Tuple

import asyncpg

DB_DSN_ENV = ("DATABASE_URL", "POSTGRES_DSN", "POSTGRES_URL")
PG_POOL_MIN = max(1, int(os.getenv("PG_POOL_MIN", "1")))
PG_POOL_MAX = max(PG_POOL_MIN, int(os.getenv("PG_POOL_MAX", "10")))
PG_COMMAND_TIMEOUT = float(os.getenv("PG_COMMAND_TIMEOUT", "30"))
_POOL: asyncpg.Pool | None = None
_POOL_LOCK = asyncio.Lock()
PIONEER_BADGE_ID = "first_pioneer"
PIONEER_BADGE_CUTOFF = "2026-01-01"
SEASON0_KEY = "2025-12"
SEASON0_START = "2025-12-20"
SEASON0_BACKFILL_SETTING = "season0_backfill_done"
TREASURE_REWARD_XP = 5


def _get_db_dsn() -> str:
    for key in DB_DSN_ENV:
        value = os.getenv(key, "").strip()
        if value:
            return value
    raise RuntimeError("DATABASE_URL is not set")


async def _get_pool() -> asyncpg.Pool:
    global _POOL
    if _POOL:
        return _POOL
    async with _POOL_LOCK:
        if _POOL:
            return _POOL
        _POOL = await asyncpg.create_pool(
            dsn=_get_db_dsn(),
            min_size=PG_POOL_MIN,
            max_size=PG_POOL_MAX,
            command_timeout=PG_COMMAND_TIMEOUT,
            server_settings={"timezone": "UTC"},
        )
        return _POOL


class _PgConn:
    def __init__(self, conn: asyncpg.Connection) -> None:
        self._conn = conn

    async def execute(self, sql: str, *params):
        return await self._conn.execute(sql, *params)

    async def fetch(self, sql: str, *params):
        return await self._conn.fetch(sql, *params)

    async def fetchrow(self, sql: str, *params):
        return await self._conn.fetchrow(sql, *params)

    async def fetchval(self, sql: str, *params):
        return await self._conn.fetchval(sql, *params)

    async def executemany(self, sql: str, seq_of_params):
        return await self._conn.executemany(sql, seq_of_params)

    async def commit(self) -> None:
        return None


@asynccontextmanager
async def _connect() -> _PgConn:
    pool = await _get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield _PgConn(conn)


def _translate_sql(sql: str) -> str:
    index = 0
    out = []
    in_single = False
    in_double = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_double:
            out.append(ch)
            if in_single:
                if i + 1 < len(sql) and sql[i + 1] == "'":
                    out.append("'")
                    i += 1
                else:
                    in_single = False
            else:
                in_single = True
        elif ch == '"' and not in_single:
            out.append(ch)
            in_double = not in_double
        elif ch == "?" and not in_single and not in_double:
            index += 1
            out.append(f"${index}")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _returns_rows(sql: str) -> bool:
    cleaned = sql.lstrip().lower()
    if cleaned.startswith("select") or cleaned.startswith("with"):
        return True
    return " returning " in cleaned


class _Cursor:
    def __init__(self, rows=None, status: str | None = None, lastrowid: int | None = None):
        self._rows = rows or []
        self._index = 0
        self.status = status
        self.lastrowid = lastrowid

    async def fetchone(self):
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    async def fetchall(self):
        if self._index == 0:
            return list(self._rows)
        remaining = self._rows[self._index :]
        self._index = len(self._rows)
        return remaining


async def _execute(db: _PgConn, sql: str, params: tuple = ()):
    translated = _translate_sql(sql)
    params = params or ()
    if not isinstance(params, (tuple, list)):
        params = (params,)
    if _returns_rows(translated):
        rows = await db.fetch(translated, *params)
        lastrowid = None
        if rows and "returning" in translated.lower():
            try:
                lastrowid = int(rows[0][0])
            except (TypeError, ValueError, IndexError):
                lastrowid = None
        return _Cursor(rows, lastrowid=lastrowid)
    status = await db.execute(translated, *params)
    return _Cursor([], status=status)


async def _executemany(db: _PgConn, sql: str, seq_of_params):
    translated = _translate_sql(sql)
    return await db.executemany(translated, seq_of_params)


async def init_db() -> None:
    async with _connect() as db:
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username TEXT,
                max_floor INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                tutorial_done INTEGER DEFAULT 0,
                unlocked_heroes_json TEXT DEFAULT '["wanderer"]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS runs (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                max_floor INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_tutorial INTEGER DEFAULT 0,
                state_json TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id BIGINT PRIMARY KEY,
                total_runs INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                deaths_by_floor TEXT DEFAULT '{}',
                kills_json TEXT DEFAULT '{}',
                hero_runs_json TEXT DEFAULT '{}',
                treasures_found INTEGER DEFAULT 0,
                chests_opened INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS user_broadcasts (
                user_id BIGINT NOT NULL,
                broadcast_key TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, broadcast_key),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS seasons (
                id BIGSERIAL PRIMARY KEY,
                season_key TEXT UNIQUE NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS user_season_stats (
                user_id BIGINT NOT NULL,
                season_id BIGINT NOT NULL,
                max_floor INTEGER DEFAULT 0,
                max_floor_character TEXT DEFAULT 'wanderer',
                total_runs INTEGER DEFAULT 0,
                deaths INTEGER DEFAULT 0,
                deaths_by_floor TEXT DEFAULT '{}',
                kills_json TEXT DEFAULT '{}',
                treasures_found INTEGER DEFAULT 0,
                chests_opened INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, season_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(season_id) REFERENCES seasons(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS user_badges (
                user_id BIGINT NOT NULL,
                badge_id TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                last_awarded_season TEXT,
                last_awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, badge_id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS star_purchases (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                telegram_payment_charge_id TEXT UNIQUE NOT NULL,
                provider_payment_charge_id TEXT,
                levels INTEGER NOT NULL,
                stars INTEGER NOT NULL,
                xp_added INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS star_actions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                telegram_payment_charge_id TEXT UNIQUE NOT NULL,
                provider_payment_charge_id TEXT,
                action TEXT NOT NULL,
                stars INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        )
        await _execute(
            db,
            """
            CREATE TABLE IF NOT EXISTS season_history (
                season_id BIGINT PRIMARY KEY,
                season_number INTEGER NOT NULL,
                season_key TEXT NOT NULL,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                winners_json TEXT DEFAULT '{}',
                summary_json TEXT DEFAULT '{}',
                FOREIGN KEY(season_id) REFERENCES seasons(id)
            )
            """,
        )
        await _ensure_user_columns(db)
        await _ensure_run_columns(db)
        await _ensure_user_stats_columns(db)
        await _ensure_user_season_columns(db)
        await _backfill_season0_stats(db)
        await _execute(db, 
            "INSERT INTO user_badges (user_id, badge_id, count, last_awarded_season) "
            "SELECT id, ?, 1, NULL FROM users WHERE created_at::date < ?::date "
            "ON CONFLICT DO NOTHING",
            (PIONEER_BADGE_ID, PIONEER_BADGE_CUTOFF),
        )


async def _ensure_user_columns(db: _PgConn) -> None:
    await _execute(db, "ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0")
    await _execute(db, "ALTER TABLE users ADD COLUMN IF NOT EXISTS tutorial_done INTEGER DEFAULT 0")
    await _execute(
        db,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS unlocked_heroes_json TEXT DEFAULT '[\"wanderer\"]'",
    )
    await _execute(
        db,
        "UPDATE users SET unlocked_heroes_json = '[\"wanderer\"]' "
        "WHERE unlocked_heroes_json IS NULL OR unlocked_heroes_json = '' OR unlocked_heroes_json = '[]'",
    )


async def _ensure_run_columns(db: _PgConn) -> None:
    await _execute(db, "ALTER TABLE runs ADD COLUMN IF NOT EXISTS is_tutorial INTEGER DEFAULT 0")


async def _ensure_user_stats_columns(db: _PgConn) -> None:
    await _execute(
        db,
        "ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS hero_runs_json TEXT DEFAULT '{}'",
    )
    cursor = await _execute(
        db,
        "SELECT user_id, total_runs, hero_runs_json FROM user_stats",
    )
    rows = await cursor.fetchall()
    for user_id, total_runs, hero_runs_json in rows:
        if hero_runs_json and hero_runs_json != "{}":
            continue
        hero_runs = {"wanderer": int(total_runs or 0)}
        await _execute(
            db,
            "UPDATE user_stats SET hero_runs_json = ? WHERE user_id = ?",
            (json.dumps(hero_runs), user_id),
        )


async def _ensure_user_season_columns(db: _PgConn) -> None:
    await _execute(
        db,
        "ALTER TABLE user_season_stats ADD COLUMN IF NOT EXISTS xp_gained INTEGER DEFAULT 0",
    )
    await _execute(
        db,
        "ALTER TABLE user_season_stats ADD COLUMN IF NOT EXISTS deaths INTEGER DEFAULT 0",
    )
    await _execute(
        db,
        "ALTER TABLE user_season_stats ADD COLUMN IF NOT EXISTS deaths_by_floor TEXT DEFAULT '{}'",
    )
    await _execute(
        db,
        "ALTER TABLE user_season_stats ADD COLUMN IF NOT EXISTS max_floor_character TEXT DEFAULT 'wanderer'",
    )
    await _execute(
        db,
        "UPDATE user_season_stats SET max_floor_character = 'wanderer' "
        "WHERE max_floor_character IS NULL OR max_floor_character = ''",
    )


async def _backfill_season0_stats(db: _PgConn) -> None:
    cursor = await _execute(db, "SELECT value FROM settings WHERE key = ?", (SEASON0_BACKFILL_SETTING,))
    row = await cursor.fetchone()
    if row and row[0] == "1":
        return

    cursor = await _execute(db, "SELECT id FROM seasons WHERE season_key = ?", (SEASON0_KEY,))
    row = await cursor.fetchone()
    if row:
        season_id = int(row[0])
    else:
        cursor = await _execute(
            db,
            "INSERT INTO seasons (season_key, started_at) VALUES (?, ?) RETURNING id",
            (SEASON0_KEY, SEASON0_START),
        )
        row = await cursor.fetchone()
        season_id = int(row[0]) if row else 0

    cursor = await _execute(db, 
        "SELECT user_id, state_json, max_floor FROM runs "
        "WHERE is_active = 0 AND is_tutorial = 0 AND started_at >= ?",
        (SEASON0_START,),
    )
    rows = await cursor.fetchall()
    if not rows:
        await _execute(
            db,
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (SEASON0_BACKFILL_SETTING, "1"),
        )
        return

    aggregates: Dict[int, Dict[str, Any]] = {}
    for user_id, state_json, max_floor in rows:
        agg = aggregates.setdefault(
            user_id,
            {
                "max_floor": 0,
                "max_floor_character": "wanderer",
                "total_runs": 0,
                "kills": {},
                "treasures_found": 0,
                "chests_opened": 0,
                "xp_gained": 0,
            },
        )
        agg["total_runs"] += 1
        state = {}
        if state_json:
            try:
                state = json.loads(state_json)
            except json.JSONDecodeError:
                state = {}
        floor_value = int(state.get("floor", 0) or max_floor or 0)
        if floor_value > agg["max_floor"]:
            agg["max_floor"] = floor_value
            agg["max_floor_character"] = state.get("character_id") or "wanderer"
        agg["treasures_found"] += int(state.get("treasures_found", 0))
        agg["chests_opened"] += int(state.get("chests_opened", 0))
        treasure_xp = int(state.get("treasure_xp", 0))
        if treasure_xp <= 0:
            treasure_xp = int(state.get("treasures_found", 0)) * TREASURE_REWARD_XP
        agg["xp_gained"] += max(0, floor_value) + treasure_xp
        for enemy_id, count in (state.get("kills", {}) or {}).items():
            agg["kills"][enemy_id] = agg["kills"].get(enemy_id, 0) + int(count)

    for user_id, data in aggregates.items():
        await _execute(
            db,
            "INSERT INTO user_season_stats (user_id, season_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (user_id, season_id),
        )
        await _execute(
            db,
            "UPDATE user_season_stats SET max_floor = ?, max_floor_character = ?, total_runs = ?, kills_json = ?, "
            "treasures_found = ?, chests_opened = ?, xp_gained = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND season_id = ?",
            (
                data["max_floor"],
                data.get("max_floor_character", "wanderer"),
                data["total_runs"],
                json.dumps(data["kills"]),
                data["treasures_found"],
                data["chests_opened"],
                data["xp_gained"],
                user_id,
                season_id,
            ),
        )

    await _execute(
        db,
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
        (SEASON0_BACKFILL_SETTING, "1"),
    )


def _current_season_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def get_or_create_current_season() -> Tuple[int, str, Optional[Tuple[int, str]]]:
    season_key = _current_season_key()
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, season_key FROM seasons WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        active = await cursor.fetchone()
        if active:
            return active[0], active[1], None
        cursor = await _execute(
            db,
            "INSERT INTO seasons (season_key) VALUES (?) RETURNING id",
            (season_key,),
        )
        row = await cursor.fetchone()
        season_id = int(row[0]) if row else 0
        return season_id, season_key, None


async def get_active_season() -> Optional[Tuple[int, str]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, season_key FROM seasons WHERE ended_at IS NULL ORDER BY started_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return row[0], row[1]


async def get_season_by_key(season_key: str) -> Optional[Tuple[int, str]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, season_key FROM seasons WHERE season_key = ?",
            (season_key,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return row[0], row[1]


async def close_season(season_id: int) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE seasons SET ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (season_id,),
        )
        await db.commit()


async def reopen_season(season_id: int) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE seasons SET ended_at = NULL WHERE id = ?",
            (season_id,),
        )
        await db.commit()


async def create_season(season_key: str) -> int:
    async with _connect() as db:
        cursor = await _execute(
            db,
            "INSERT INTO seasons (season_key) VALUES (?) "
            "ON CONFLICT (season_key) DO NOTHING RETURNING id",
            (season_key,),
        )
        row = await cursor.fetchone()
        if row:
            return int(row[0])
        cursor = await _execute(db, 
            "SELECT id FROM seasons WHERE season_key = ?",
            (season_key,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def get_last_season(ended_only: bool = False) -> Optional[Tuple[int, str]]:
    async with _connect() as db:
        if ended_only:
            cursor = await _execute(db, 
                "SELECT id, season_key FROM seasons "
                "WHERE ended_at IS NOT NULL ORDER BY started_at DESC LIMIT 1"
            )
        else:
            cursor = await _execute(db, 
                "SELECT id, season_key FROM seasons ORDER BY started_at DESC LIMIT 1"
            )
        row = await cursor.fetchone()
        if not row:
            return None
        return row[0], row[1]


async def save_season_history(
    season_id: int,
    season_number: int,
    season_key: str,
    winners_json: str,
    summary_json: str,
) -> None:
    async with _connect() as db:
        await _execute(
            db,
            "INSERT INTO season_history "
            "(season_id, season_number, season_key, processed_at, winners_json, summary_json) "
            "VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?) "
            "ON CONFLICT (season_id) DO UPDATE SET "
            "season_number = EXCLUDED.season_number, "
            "season_key = EXCLUDED.season_key, "
            "processed_at = CURRENT_TIMESTAMP, "
            "winners_json = EXCLUDED.winners_json, "
            "summary_json = EXCLUDED.summary_json",
            (season_id, season_number, season_key, winners_json, summary_json),
        )


async def get_season_history(season_number: int) -> Optional[Tuple[int, str, str, str]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT season_id, season_key, winners_json, summary_json "
            "FROM season_history WHERE season_number = ?",
            (season_number,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return row[0], row[1], row[2], row[3]


async def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    async with _connect() as db:
        cursor = await _execute(db, 
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


async def get_unlocked_heroes(user_id: int) -> List[str]:
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT unlocked_heroes_json FROM users WHERE id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return ["wanderer"]
        raw = row[0] or ""
        try:
            heroes = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            heroes = []
        if not isinstance(heroes, list):
            heroes = []
        if "wanderer" not in heroes:
            heroes.append("wanderer")
        return heroes


async def set_unlocked_heroes(user_id: int, heroes: List[str]) -> None:
    unique = []
    seen = set()
    for hero_id in heroes:
        if not hero_id or hero_id in seen:
            continue
        seen.add(hero_id)
        unique.append(hero_id)
    if "wanderer" not in seen:
        unique.append("wanderer")
    async with _connect() as db:
        await _execute(
            db,
            "UPDATE users SET unlocked_heroes_json = ? WHERE id = ?",
            (json.dumps(unique), user_id),
        )
        await db.commit()


async def unlock_hero(user_id: int, hero_id: str) -> bool:
    heroes = await get_unlocked_heroes(user_id)
    if hero_id in heroes:
        return False
    heroes.append(hero_id)
    await set_unlocked_heroes(user_id, heroes)
    return True


async def add_user_xp(user_id: int, amount: int) -> None:
    if amount <= 0:
        return
    async with _connect() as db:
        await _execute(db, 
            "UPDATE users SET xp = COALESCE(xp, 0) + ? WHERE id = ?",
            (amount, user_id),
        )
        await db.commit()


async def add_season_xp(user_id: int, season_id: int, amount: int) -> None:
    if amount <= 0:
        return
    async with _connect() as db:
        await _execute(
            db,
            "INSERT INTO user_season_stats (user_id, season_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (user_id, season_id),
        )
        await _execute(
            db,
            "UPDATE user_season_stats "
            "SET xp_gained = COALESCE(xp_gained, 0) + ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND season_id = ?",
            (amount, user_id, season_id),
        )
        await db.commit()


async def has_star_purchase(telegram_payment_charge_id: str) -> bool:
    if not telegram_payment_charge_id:
        return False
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT 1 FROM star_purchases WHERE telegram_payment_charge_id = ?",
            (telegram_payment_charge_id,),
        )
        row = await cursor.fetchone()
        return bool(row)

async def has_star_action(telegram_payment_charge_id: str) -> bool:
    if not telegram_payment_charge_id:
        return False
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT 1 FROM star_actions WHERE telegram_payment_charge_id = ?",
            (telegram_payment_charge_id,),
        )
        row = await cursor.fetchone()
        return bool(row)


async def record_star_purchase(
    user_id: int,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: str | None,
    levels: int,
    stars: int,
    xp_added: int,
) -> None:
    if not telegram_payment_charge_id:
        return
    async with _connect() as db:
        await _execute(
            db,
            "INSERT INTO star_purchases "
            "(user_id, telegram_payment_charge_id, provider_payment_charge_id, levels, stars, xp_added) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (
                user_id,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                levels,
                stars,
                xp_added,
            ),
        )
        await db.commit()

async def record_star_action(
    user_id: int,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: str | None,
    action: str,
    stars: int,
) -> None:
    if not telegram_payment_charge_id:
        return
    async with _connect() as db:
        await _execute(
            db,
            "INSERT INTO star_actions "
            "(user_id, telegram_payment_charge_id, provider_payment_charge_id, action, stars) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            (
                user_id,
                telegram_payment_charge_id,
                provider_payment_charge_id,
                action,
                stars,
            ),
        )
        await db.commit()


async def get_star_purchase_summary(user_id: int) -> List[Dict[str, int]]:
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT levels, COUNT(*), COALESCE(SUM(stars), 0), COALESCE(SUM(xp_added), 0) "
            "FROM star_purchases WHERE user_id = ? GROUP BY levels ORDER BY levels ASC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        summary = []
        for levels, count, stars, xp_added in rows:
            summary.append(
                {
                    "levels": int(levels),
                    "count": int(count),
                    "stars": int(stars),
                    "xp_added": int(xp_added),
                }
            )
        return summary


async def get_user_season_stats(user_id: int, season_id: int) -> Dict[str, Any]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT max_floor, total_runs, deaths, deaths_by_floor, kills_json, treasures_found, "
            "chests_opened, xp_gained "
            "FROM user_season_stats WHERE user_id = ? AND season_id = ?",
            (user_id, season_id),
        )
        row = await cursor.fetchone()
        if not row:
            return {
                "max_floor": 0,
                "total_runs": 0,
                "deaths": 0,
                "deaths_by_floor": {},
                "kills": {},
                "treasures_found": 0,
                "chests_opened": 0,
                "xp_gained": 0,
            }
        (
            max_floor,
            total_runs,
            deaths,
            deaths_by_floor,
            kills_json,
            treasures_found,
            chests_opened,
            xp_gained,
        ) = row
        return {
            "max_floor": max_floor or 0,
            "total_runs": total_runs or 0,
            "deaths": deaths or 0,
            "deaths_by_floor": json.loads(deaths_by_floor or "{}"),
            "kills": json.loads(kills_json or "{}"),
            "treasures_found": treasures_found or 0,
            "chests_opened": chests_opened or 0,
            "xp_gained": xp_gained or 0,
        }


async def record_season_stats(
    user_id: int,
    season_id: int,
    state: Dict[str, Any],
    died: bool | None = None,
) -> None:
    async with _connect() as db:
        await _execute(db, 
            "INSERT INTO user_season_stats (user_id, season_id) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (user_id, season_id),
        )
        cursor = await _execute(db, 
            "SELECT max_floor, max_floor_character, total_runs, deaths, deaths_by_floor, kills_json, "
            "treasures_found, chests_opened, xp_gained "
            "FROM user_season_stats WHERE user_id = ? AND season_id = ?",
            (user_id, season_id),
        )
        row = await cursor.fetchone()
        (
            max_floor,
            max_floor_character,
            total_runs,
            deaths,
            deaths_by_floor,
            kills_json,
            treasures_found,
            chests_opened,
            xp_gained,
        ) = row or (
            0,
            "wanderer",
            0,
            0,
            "{}",
            "{}",
            0,
            0,
            0,
        )

        old_max_floor = max_floor or 0
        floor_value = int(state.get("floor", 0))
        max_floor = max(old_max_floor, floor_value)
        max_floor_character = max_floor_character or "wanderer"
        if floor_value > old_max_floor:
            max_floor_character = state.get("character_id") or "wanderer"
        total_runs = (total_runs or 0) + 1
        deaths = deaths or 0
        deaths_by_floor = json.loads(deaths_by_floor or "{}")
        kills = json.loads(kills_json or "{}")
        treasures_found = (treasures_found or 0) + int(state.get("treasures_found", 0))
        chests_opened = (chests_opened or 0) + int(state.get("chests_opened", 0))
        xp_bonus = int(state.get("xp_bonus", 0))
        xp_gained = (xp_gained or 0) + int(state.get("floor", 0)) + xp_bonus

        if died:
            deaths += 1
            floor = str(state.get("floor", 0))
            deaths_by_floor[floor] = deaths_by_floor.get(floor, 0) + 1

        for enemy_id, count in (state.get("kills", {}) or {}).items():
            kills[enemy_id] = kills.get(enemy_id, 0) + int(count)

        await _execute(db, 
            "UPDATE user_season_stats SET max_floor = ?, max_floor_character = ?, total_runs = ?, deaths = ?, "
            "deaths_by_floor = ?, kills_json = ?, treasures_found = ?, chests_opened = ?, "
            "xp_gained = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ? AND season_id = ?",
            (
                max_floor,
                max_floor_character,
                total_runs,
                deaths,
                json.dumps(deaths_by_floor),
                json.dumps(kills),
                treasures_found,
                chests_opened,
                xp_gained,
                user_id,
                season_id,
            ),
        )
        await db.commit()


async def get_season_death_stats(season_id: int) -> tuple[int, float]:
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT COALESCE(SUM(deaths), 0) FROM user_season_stats WHERE season_id = ?",
            (season_id,),
        )
        row = await cursor.fetchone()
        total_deaths = int(row[0]) if row else 0

        cursor = await _execute(
            db,
            "SELECT deaths_by_floor FROM user_season_stats WHERE season_id = ?",
            (season_id,),
        )
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
        return total_deaths, avg_death_floor


async def get_season_leaderboard_total(season_id: int) -> int:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT COUNT(*) FROM user_season_stats WHERE season_id = ? AND max_floor > 0",
            (season_id,),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def get_season_leaderboard_page(season_id: int, limit: int, offset: int) -> List[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT users.username, user_season_stats.max_floor, users.xp, user_season_stats.max_floor_character "
            "FROM user_season_stats "
            "JOIN users ON users.id = user_season_stats.user_id "
            "WHERE user_season_stats.season_id = ? "
            "ORDER BY user_season_stats.max_floor DESC, users.username ASC "
            "LIMIT ? OFFSET ?",
            (season_id, limit, offset),
        )
        return await cursor.fetchall()


async def get_user_season_rank(user_id: int, season_id: int) -> Optional[int]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT rank FROM ("
            "SELECT user_id, ROW_NUMBER() OVER (ORDER BY max_floor DESC, user_id ASC) AS rank "
            "FROM user_season_stats WHERE season_id = ? AND max_floor > 0"
            ") WHERE user_id = ?",
            (season_id, user_id),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else None


async def get_season_stats_rows(season_id: int) -> List[Dict[str, Any]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT user_id, max_floor, total_runs, kills_json, treasures_found, chests_opened, xp_gained "
            "FROM user_season_stats WHERE season_id = ?",
            (season_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            user_id, max_floor, total_runs, kills_json, treasures_found, chests_opened, xp_gained = row
            results.append(
                {
                    "user_id": user_id,
                    "max_floor": max_floor or 0,
                    "total_runs": total_runs or 0,
                    "kills": json.loads(kills_json or "{}"),
                    "treasures_found": treasures_found or 0,
                    "chests_opened": chests_opened or 0,
                    "xp_gained": xp_gained or 0,
                }
            )
        return results


async def get_season_player_rows(season_id: int) -> List[Dict[str, Any]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT users.id, users.telegram_id, users.username, "
            "user_season_stats.max_floor, user_season_stats.total_runs, "
            "user_season_stats.kills_json, user_season_stats.treasures_found, "
            "user_season_stats.chests_opened, user_season_stats.xp_gained "
            "FROM user_season_stats "
            "JOIN users ON users.id = user_season_stats.user_id "
            "WHERE user_season_stats.season_id = ?",
            (season_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            (
                user_id,
                telegram_id,
                username,
                max_floor,
                total_runs,
                kills_json,
                treasures_found,
                chests_opened,
                xp_gained,
            ) = row
            results.append(
                {
                    "user_id": user_id,
                    "telegram_id": telegram_id,
                    "username": username,
                    "max_floor": max_floor or 0,
                    "total_runs": total_runs or 0,
                    "kills": json.loads(kills_json or "{}"),
                    "treasures_found": treasures_found or 0,
                    "chests_opened": chests_opened or 0,
                    "xp_gained": xp_gained or 0,
                }
            )
        return results


async def get_users_by_ids(user_ids: List[int]) -> Dict[int, Tuple[Optional[str], int]]:
    if not user_ids:
        return {}
    placeholders = ",".join("?" for _ in user_ids)
    async with _connect() as db:
        cursor = await _execute(db, 
            f"SELECT id, username, telegram_id FROM users WHERE id IN ({placeholders})",
            tuple(user_ids),
        )
        rows = await cursor.fetchall()
        return {user_id: (username, telegram_id) for user_id, username, telegram_id in rows}


async def get_user_badges(user_id: int) -> List[Dict[str, Any]]:
    async with _connect() as db:
        cursor = await _execute(db, 
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
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT count, last_awarded_season FROM user_badges WHERE user_id = ? AND badge_id = ?",
            (user_id, badge_id),
        )
        row = await cursor.fetchone()
        if row:
            count, last_awarded_season = row
            if season_key and last_awarded_season == season_key:
                return False
            new_count = (count or 0) + 1
            await _execute(db, 
                "UPDATE user_badges SET count = ?, last_awarded_season = ?, "
                "last_awarded_at = CURRENT_TIMESTAMP WHERE user_id = ? AND badge_id = ?",
                (new_count, season_key, user_id, badge_id),
            )
        else:
            await _execute(db, 
                "INSERT INTO user_badges (user_id, badge_id, count, last_awarded_season) "
                "VALUES (?, ?, 1, ?)",
                (user_id, badge_id, season_key),
            )
        await db.commit()
        return True
        await db.commit()


async def ensure_user(telegram_id: int, username: Optional[str]) -> int:
    async with _connect() as db:
        await _execute(db, 
            "INSERT INTO users (telegram_id, username) VALUES (?, ?) ON CONFLICT (telegram_id) DO NOTHING",
            (telegram_id, username),
        )
        await _execute(db, 
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        await db.commit()
        cursor = await _execute(db, 
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        user_id = row[0]
        cursor = await _execute(db, 
            "SELECT created_at FROM users WHERE id = ?",
            (user_id,),
        )
        created_row = await cursor.fetchone()
        created_at = created_row[0] if created_row else None
        if created_at:
            await _execute(db, 
                "INSERT INTO user_badges (user_id, badge_id, count, last_awarded_season) "
                "SELECT ?, ?, 1, NULL WHERE ?::date < ?::date "
                "ON CONFLICT DO NOTHING",
                (user_id, PIONEER_BADGE_ID, created_at, PIONEER_BADGE_CUTOFF),
            )
        await db.commit()
        return user_id


async def get_user(user_id: int) -> Optional[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, telegram_id, username, max_floor FROM users WHERE id = ?",
            (user_id,),
        )
        return await cursor.fetchone()


async def get_user_by_telegram(telegram_id: int) -> Optional[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, telegram_id, username, max_floor FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return await cursor.fetchone()


async def get_tutorial_done(telegram_id: int) -> bool:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT tutorial_done FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return False
        return bool(row[0])


async def set_tutorial_done(telegram_id: int, done: bool) -> None:
    value = 1 if done else 0
    async with _connect() as db:
        await _execute(db, 
            "UPDATE users SET tutorial_done = ? WHERE telegram_id = ?",
            (value, telegram_id),
        )
        await db.commit()


async def get_active_run(user_id: int) -> Optional[Tuple[int, Dict[str, Any]]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, state_json FROM runs "
            "WHERE user_id = ? AND is_active = 1 AND is_tutorial = 0 "
            "ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        run_id, state_json = row
        return run_id, json.loads(state_json)

async def get_active_tutorial(user_id: int) -> Optional[Tuple[int, Dict[str, Any]]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, state_json FROM runs "
            "WHERE user_id = ? AND is_active = 1 AND is_tutorial = 1 "
            "ORDER BY started_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        run_id, state_json = row
        return run_id, json.loads(state_json)

async def get_run_by_id(run_id: int) -> Optional[Tuple[int, bool, Dict[str, Any]]]:
    async with _connect() as db:
        cursor = await _execute(
            db,
            "SELECT user_id, is_active, state_json FROM runs WHERE id = ?",
            (run_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        user_id, is_active, state_json = row
        state = json.loads(state_json) if state_json else {}
        return int(user_id), bool(is_active), state


async def create_run(user_id: int, state: Dict[str, Any]) -> int:
    async with _connect() as db:
        cursor = await _execute(db, 
            "INSERT INTO runs (user_id, state_json, max_floor, is_active, is_tutorial) "
            "VALUES (?, ?, ?, 1, 0) RETURNING id",
            (user_id, json.dumps(state), state.get("floor", 0)),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0

async def create_tutorial_run(user_id: int, state: Dict[str, Any]) -> int:
    async with _connect() as db:
        cursor = await _execute(db, 
            "INSERT INTO runs (user_id, state_json, max_floor, is_active, is_tutorial) "
            "VALUES (?, ?, ?, 1, 1) RETURNING id",
            (user_id, json.dumps(state), state.get("floor", 0)),
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def update_run(run_id: int, state: Dict[str, Any]) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE runs SET state_json = ?, max_floor = ? WHERE id = ?",
            (json.dumps(state), state.get("floor", 0), run_id),
        )
        await db.commit()


async def finish_run(run_id: int, final_floor: int) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE runs SET is_active = 0, ended_at = CURRENT_TIMESTAMP, max_floor = ? WHERE id = ?",
            (final_floor, run_id),
        )
        await db.commit()

async def finish_tutorial_run(run_id: int) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE runs SET is_active = 0, ended_at = CURRENT_TIMESTAMP WHERE id = ?",
            (run_id,),
        )
        await db.commit()


async def update_user_max_floor(user_id: int, floor: int) -> None:
    async with _connect() as db:
        await _execute(db, 
            "UPDATE users SET max_floor = GREATEST(max_floor, ?) WHERE id = ?",
            (floor, user_id),
        )
        await db.commit()


async def get_leaderboard(limit: int = 10) -> List[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT username, max_floor FROM users ORDER BY max_floor DESC, username ASC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_leaderboard_page(limit: int, offset: int) -> List[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT username, max_floor FROM users "
            "ORDER BY max_floor DESC, username ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return await cursor.fetchall()


async def get_leaderboard_total() -> int:
    async with _connect() as db:
        cursor = await _execute(db, "SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return int(row[0]) if row else 0


async def get_last_run(user_id: int) -> Optional[Tuple[int, int, Dict[str, Any]]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, max_floor, state_json FROM runs "
            "WHERE user_id = ? AND is_tutorial = 0 "
            "ORDER BY COALESCE(ended_at, started_at) DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        run_id, max_floor, state_json = row
        state = json.loads(state_json) if state_json else {}
        return run_id, max_floor, state


async def get_leaderboard_with_ids(limit: int = 10) -> List[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, username, max_floor FROM users "
            "ORDER BY max_floor DESC, username ASC LIMIT ?",
            (limit,),
        )
        return await cursor.fetchall()


async def get_season_leaderboard_with_ids(season_id: int, limit: int = 10) -> List[Tuple]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT users.id, users.username, user_season_stats.max_floor, user_season_stats.max_floor_character "
            "FROM user_season_stats "
            "JOIN users ON users.id = user_season_stats.user_id "
            "WHERE user_season_stats.season_id = ? AND user_season_stats.max_floor > 0 "
            "ORDER BY user_season_stats.max_floor DESC, users.username ASC LIMIT ?",
            (season_id, limit),
        )
        return await cursor.fetchall()


async def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT total_runs, deaths, deaths_by_floor, kills_json, hero_runs_json, "
            "treasures_found, chests_opened "
            "FROM user_stats WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        total_runs, deaths, deaths_by_floor, kills_json, hero_runs_json, treasures_found, chests_opened = row
        return {
            "total_runs": total_runs or 0,
            "deaths": deaths or 0,
            "deaths_by_floor": json.loads(deaths_by_floor or "{}"),
            "kills": json.loads(kills_json or "{}"),
            "hero_runs": json.loads(hero_runs_json or "{}"),
            "treasures_found": treasures_found or 0,
            "chests_opened": chests_opened or 0,
        }


async def record_run_stats(user_id: int, state: Dict[str, Any], died: bool) -> None:
    async with _connect() as db:
        await _execute(db, 
            "INSERT INTO user_stats (user_id) VALUES (?) ON CONFLICT DO NOTHING",
            (user_id,),
        )
        cursor = await _execute(db, 
            "SELECT total_runs, deaths, deaths_by_floor, kills_json, hero_runs_json, treasures_found, chests_opened "
            "FROM user_stats WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        total_runs, deaths, deaths_by_floor, kills_json, hero_runs_json, treasures_found, chests_opened = row or (
            0,
            0,
            "{}",
            "{}",
            "{}",
            0,
            0,
        )

        total_runs = (total_runs or 0) + 1
        deaths = deaths or 0
        deaths_by_floor = json.loads(deaths_by_floor or "{}")
        kills = json.loads(kills_json or "{}")
        hero_runs = json.loads(hero_runs_json or "{}")
        treasures_found = (treasures_found or 0) + int(state.get("treasures_found", 0))
        chests_opened = (chests_opened or 0) + int(state.get("chests_opened", 0))
        hero_id = state.get("character_id") or "wanderer"
        hero_runs[hero_id] = hero_runs.get(hero_id, 0) + 1

        if died:
            deaths += 1
            floor = str(state.get("floor", 0))
            deaths_by_floor[floor] = deaths_by_floor.get(floor, 0) + 1

        for enemy_id, count in (state.get("kills", {}) or {}).items():
            kills[enemy_id] = kills.get(enemy_id, 0) + int(count)

        await _execute(db, 
            "UPDATE user_stats SET total_runs = ?, deaths = ?, deaths_by_floor = ?, "
            "kills_json = ?, hero_runs_json = ?, treasures_found = ?, chests_opened = ?, "
            "updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ?",
            (
                total_runs,
                deaths,
                json.dumps(deaths_by_floor),
                json.dumps(kills),
                json.dumps(hero_runs),
                treasures_found,
                chests_opened,
                user_id,
            ),
        )
        await db.commit()

async def get_broadcast_targets(broadcast_key: str) -> List[Tuple[int, int]]:
    async with _connect() as db:
        cursor = await _execute(db, 
            "SELECT id, telegram_id FROM users WHERE id NOT IN ("
            "SELECT user_id FROM user_broadcasts WHERE broadcast_key = ?)",
            (broadcast_key,),
        )
        return await cursor.fetchall()


async def get_all_user_targets() -> List[Tuple[int, int]]:
    async with _connect() as db:
        cursor = await _execute(db, "SELECT id, telegram_id FROM users")
        return await cursor.fetchall()


async def get_setting(key: str) -> Optional[str]:
    async with _connect() as db:
        cursor = await _execute(db, "SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with _connect() as db:
        await _execute(db, 
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = EXCLUDED.value",
            (key, value),
        )
        await db.commit()


async def mark_broadcast_sent(user_id: int, broadcast_key: str) -> None:
    async with _connect() as db:
        await _execute(db, 
            "INSERT INTO user_broadcasts (user_id, broadcast_key) VALUES (?, ?) ON CONFLICT DO NOTHING",
            (user_id, broadcast_key),
        )
        await db.commit()


async def get_admin_stats(broadcast_key: Optional[str] = None) -> Dict[str, object]:
    async with _connect() as db:
        cursor = await _execute(db, "SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        total_users = int(row[0]) if row else 0

        cursor = await _execute(db, "SELECT COUNT(*) FROM runs WHERE is_active = 1 AND is_tutorial = 0")
        row = await cursor.fetchone()
        active_runs = int(row[0]) if row else 0

        cursor = await _execute(db, "SELECT COUNT(*) FROM runs WHERE is_tutorial = 0")
        row = await cursor.fetchone()
        total_runs = int(row[0]) if row else 0

        cursor = await _execute(db, 
            "SELECT COALESCE(SUM(deaths), 0), COALESCE(SUM(treasures_found), 0), "
            "COALESCE(SUM(chests_opened), 0) FROM user_stats"
        )
        row = await cursor.fetchone()
        total_deaths = int(row[0]) if row else 0
        total_treasures = int(row[1]) if row else 0
        total_chests = int(row[2]) if row else 0

        cursor = await _execute(db, "SELECT COALESCE(MAX(max_floor), 0) FROM users")
        row = await cursor.fetchone()
        max_floor = int(row[0]) if row else 0

        cursor = await _execute(db, 
            "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM runs "
            "WHERE started_at >= (CURRENT_TIMESTAMP - INTERVAL '1 day') AND is_tutorial = 0"
        )
        row = await cursor.fetchone()
        runs_24h = int(row[0]) if row else 0
        users_24h = int(row[1]) if row else 0

        cursor = await _execute(db, "SELECT deaths_by_floor FROM user_stats")
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

        cursor = await _execute(db, "SELECT user_id, kills_json FROM user_stats")
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
            cursor = await _execute(db, 
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
            cursor = await _execute(db, 
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

async def get_random_boss_name(
    min_floor: int = 10,
    exclude_telegram_id: int | None = None,
) -> Optional[str]:
    async with _connect() as db:
        if exclude_telegram_id is None:
            cursor = await _execute(db, 
                "SELECT username FROM users "
                "WHERE username IS NOT NULL AND TRIM(username) != '' "
                "AND LOWER(TRIM(username)) != 'без имени' "
                "AND max_floor >= ? "
                "ORDER BY RANDOM() LIMIT 1",
                (min_floor,),
            )
        else:
            cursor = await _execute(db, 
                "SELECT username FROM users "
                "WHERE username IS NOT NULL AND TRIM(username) != '' "
                "AND LOWER(TRIM(username)) != 'без имени' "
                "AND max_floor >= ? "
                "AND telegram_id != ? "
                "ORDER BY RANDOM() LIMIT 1",
                (min_floor, exclude_telegram_id),
            )
        row = await cursor.fetchone()
        return row[0] if row else None
