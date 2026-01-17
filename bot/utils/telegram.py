from __future__ import annotations

from typing import Optional

import asyncio

from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
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


async def _notify_retry_delay(callback: CallbackQuery | None, retry_after: float) -> None:
    if callback:
        try:
            await callback.answer(
                f"Telegram просит подождать {int(retry_after)} сек.",
                show_alert=True,
            )
        except TelegramBadRequest:
            pass
    await asyncio.sleep(retry_after)


async def _edit_with_retry(
    callback: CallbackQuery,
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup],
) -> None:
    attempts = 0
    while True:
        try:
            await safe_edit_text(message, text, reply_markup=reply_markup)
            return
        except TelegramRetryAfter as exc:
            if attempts >= 1:
                raise
            attempts += 1
            await _notify_retry_delay(callback, exc.retry_after)
        except TelegramBadRequest:
            raise


async def edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
) -> None:
    message = callback.message
    if message and message.text:
        try:
            await _edit_with_retry(callback, message, text, reply_markup)
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
