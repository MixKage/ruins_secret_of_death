import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent / "ruins.db"


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
            """
        )
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
        return row[0]


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
