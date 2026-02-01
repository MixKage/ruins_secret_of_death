import os


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return token


def get_admin_ids() -> set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    if not raw.strip():
        return set()
    ids = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            continue
    return ids


def is_test_mode() -> bool:
    raw = os.getenv("BOT_TEST_MODE", "") or os.getenv("TEST_MODE", "")
    raw = raw.strip().lower()
    return raw in {"1", "true", "yes", "on"}
