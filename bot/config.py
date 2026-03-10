import os


def _strip_wrapping_quotes(value: str) -> str:
    text = (value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1].strip()
    return text


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")
    return token


def get_admin_ids() -> set[int]:
    raw = _strip_wrapping_quotes(os.getenv("ADMIN_IDS", ""))
    if not raw.strip():
        return set()
    ids = set()
    for part in raw.split(","):
        part = _strip_wrapping_quotes(part)
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


def is_image_sending_enabled() -> bool:
    raw = _strip_wrapping_quotes(os.getenv("BOT_SEND_IMAGES", "0"))
    return raw.strip().lower() in {"1", "true", "yes", "on"}
