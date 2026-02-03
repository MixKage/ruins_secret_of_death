from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any, Literal

import asyncpg

JsonKind = Literal["dict", "list"]

# table, primary_key, column, expected json type
JSON_COLUMNS: list[tuple[str, str, str, JsonKind]] = [
    ("users", "id", "unlocked_heroes_json", "list"),
    ("runs", "id", "state_json", "dict"),
    ("user_stats", "user_id", "deaths_by_floor", "dict"),
    ("user_stats", "user_id", "kills_json", "dict"),
    ("user_stats", "user_id", "hero_runs_json", "dict"),
    ("user_season_stats", "user_id, season_id", "deaths_by_floor", "dict"),
    ("user_season_stats", "user_id, season_id", "kills_json", "dict"),
    ("season_history", "season_id", "winners_json", "dict"),
    ("season_history", "season_id", "summary_json", "dict"),
]


def _decode_nested_json(value: Any) -> Any:
    parsed = value
    for _ in range(12):
        if isinstance(parsed, memoryview):
            parsed = parsed.tobytes()
            continue
        if isinstance(parsed, (bytes, bytearray)):
            parsed = bytes(parsed).decode("utf-8", errors="ignore")
            continue
        if isinstance(parsed, str):
            raw = parsed.strip()
            if not raw:
                return parsed
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return parsed
            continue
        return parsed
    return parsed


def _normalize_json(raw: Any, kind: JsonKind) -> str:
    parsed = _decode_nested_json(raw)
    if kind == "dict":
        data = parsed if isinstance(parsed, dict) else {}
    else:
        data = parsed if isinstance(parsed, list) else []
    return json.dumps(data, ensure_ascii=False)


async def _fix_column(
    conn: asyncpg.Connection,
    table: str,
    pk_expr: str,
    column: str,
    kind: JsonKind,
    apply_changes: bool,
) -> tuple[int, int]:
    rows = await conn.fetch(f"SELECT {pk_expr}, {column} FROM {table}")
    checked = 0
    changed = 0

    for row in rows:
        checked += 1
        raw = row[column]
        normalized = _normalize_json(raw, kind)
        if isinstance(raw, str):
            same = _normalize_json(raw, kind) == normalized and raw == normalized
        else:
            same = False
        if same:
            continue

        changed += 1
        if not apply_changes:
            continue

        if "," in pk_expr:
            pk_cols = [part.strip() for part in pk_expr.split(",")]
            where = " AND ".join(f"{col} = ${idx + 2}" for idx, col in enumerate(pk_cols))
            values = [row[col] for col in pk_cols]
            await conn.execute(
                f"UPDATE {table} SET {column} = $1 WHERE {where}",
                normalized,
                *values,
            )
        else:
            pk_col = pk_expr.strip()
            await conn.execute(
                f"UPDATE {table} SET {column} = $1 WHERE {pk_col} = $2",
                normalized,
                row[pk_col],
            )
    return checked, changed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fix double-encoded JSON fields in PostgreSQL.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    parser.add_argument("--dry-run", action="store_true", help="Only report changes without updating rows.")
    args = parser.parse_args()

    if not args.database_url.strip():
        raise RuntimeError("DATABASE_URL is not set. Pass --database-url or export DATABASE_URL.")

    conn = await asyncpg.connect(args.database_url)
    try:
        async with conn.transaction():
            total_checked = 0
            total_changed = 0
            for table, pk_expr, column, kind in JSON_COLUMNS:
                checked, changed = await _fix_column(
                    conn,
                    table=table,
                    pk_expr=pk_expr,
                    column=column,
                    kind=kind,
                    apply_changes=not args.dry_run,
                )
                total_checked += checked
                total_changed += changed
                print(f"{table}.{column}: checked={checked}, changed={changed}")
            if args.dry_run:
                raise RuntimeError(
                    f"Dry run complete. checked={total_checked}, would_change={total_changed}. "
                    "No rows were updated."
                )
            print(f"Done. checked={total_checked}, changed={total_changed}")
    finally:
        await conn.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        print(str(exc))
