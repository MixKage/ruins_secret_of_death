from __future__ import annotations

from aiogram.types import User

from bot.config import get_admin_ids


def is_admin_user(user: User | None) -> bool:
    if user is None:
        return False
    return user.id in get_admin_ids()


def is_admin_id(telegram_id: int | None) -> bool:
    if telegram_id is None:
        return False
    return telegram_id in get_admin_ids()
