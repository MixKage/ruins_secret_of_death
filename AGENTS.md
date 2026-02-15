# Repository Guidelines

## Project Structure & Module Organization
- `bot/` contains the Telegram bot code; `bot/main.py` is the entry point and wires aiogram routers.
- `bot/handlers/` holds command and callback handlers grouped by feature.
- `bot/game/` contains game state, combat logic, and data helpers (`logic.py`, `data.py`).
- `bot/utils/` provides Telegram helpers; `bot/texts.py` keeps shared message text.
- `data/` stores JSON content for enemies, weapons, upgrades, scrolls, and loot tables.
- `assets/` contains images used for announcements and history.
- `ruins.db` is the default SQLite database created by `bot/db.py` (keep local).

## Build, Test, and Development Commands
- `python -m venv .venv` and `source .venv/bin/activate` to create and activate a local virtualenv.
- `pip install -r requirements.txt` installs runtime dependencies.
- `export BOT_TOKEN="..."` sets the BotFather token; `export ADMIN_IDS="123,456"` is optional for admin access.
- `python -m bot.main` starts polling and runs the bot locally.

## Coding Style & Naming Conventions
- Python 3.11+, 4-space indentation, and async/await for IO paths.
- `snake_case` for functions and variables, `UpperCamelCase` for classes, `UPPER_SNAKE_CASE` for constants.
- Keep user-facing strings consistent with existing HTML formatting (the bot uses HTML parse mode).
- Update content tables in `data/*.json` alongside any logic changes that depend on them.

## Testing Guidelines
- No automated test suite is configured yet.
- Validate changes by running the bot and exercising the affected flows in Telegram.
- If you add tests, place them under `tests/` and use `test_*.py` naming.

## Commit & Pull Request Guidelines
- Commit messages follow a short prefix style seen in history: `add: ...` or `fix: ...` with a brief description.
- PRs should include a short summary, manual test steps, and call out any data or schema changes.
- For gameplay text or UI tweaks, include a sample message or screenshot.

## Security & Configuration Tips
- Never commit tokens or private IDs; rely on `BOT_TOKEN` and `ADMIN_IDS` env vars.
- Treat `ruins.db` as local state and do not edit it manually unless you are debugging.

## Session Context
- Stars payments: added +1/+5 level purchase flow (`bot/handlers/stars.py`), `star_purchases` table, profile shows purchases; XP added via `bot/progress.py`.
- Hero unlock system: `users.unlocked_heroes_json`, `user_stats.hero_runs_json`, `bot/handlers/heroes.py`, hero selection flow from new run and profile display.
- "Run tasks" moved to a separate button and screen: `action:run_tasks` in `bot/keyboards.py`, `run_tasks` phase in `bot/handlers/game.py`, render in `bot/game/logic.py`.
- Battle summary: when one enemy, show only max damage (`"damage of enemy"` line); when multiple, show expected/max.
