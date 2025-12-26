from __future__ import annotations

from typing import Optional, Tuple

from aiogram.types import CallbackQuery, User

from bot import db
from bot.config import get_admin_ids


async def get_user_row(callback: CallbackQuery) -> Optional[Tuple]:
    user = callback.from_user
    if user is None:
        return None
    user_row = await db.get_user_by_telegram(user.id)
    if not user_row:
        await callback.answer("Сначала нажмите /start", show_alert=True)
        return None
    return user_row


def is_admin_user(user: User | None) -> bool:
    if user is None:
        return False
    return user.id in get_admin_ids()


def is_admin_id(telegram_id: int | None) -> bool:
    if telegram_id is None:
        return False
    return telegram_id in get_admin_ids()

