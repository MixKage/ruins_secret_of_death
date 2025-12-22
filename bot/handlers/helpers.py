from __future__ import annotations

from typing import Optional, Tuple

from aiogram.types import CallbackQuery

from bot import db


async def get_user_row(callback: CallbackQuery) -> Optional[Tuple]:
    user = callback.from_user
    if user is None:
        return None
    user_row = await db.get_user_by_telegram(user.id)
    if not user_row:
        await callback.answer("Сначала нажмите /start", show_alert=True)
        return None
    return user_row
