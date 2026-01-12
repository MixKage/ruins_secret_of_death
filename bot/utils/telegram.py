from __future__ import annotations

from typing import Optional

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    message = callback.message
    if message and message.text:
        try:
            await safe_edit_text(message, text, reply_markup=reply_markup)
            return
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if (
                "there is no text in the message to edit" not in error_text
                and "message can't be edited" not in error_text
            ):
                raise
    if callback.from_user:
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            reply_markup=reply_markup,
        )
    elif message:
        await callback.bot.send_message(
            message.chat.id,
            text,
            reply_markup=reply_markup,
        )
