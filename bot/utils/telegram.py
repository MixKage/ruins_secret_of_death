from __future__ import annotations

from typing import Optional

import asyncio
import logging
import time

from aiogram.client.bot import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)
_RATE_LIMIT_UNTIL: dict[int, float] = {}


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
    logger.info("Telegram rate limit: waiting %.2f seconds before retry", retry_after)
    if callback and callback.from_user:
        user_id = callback.from_user.id
        until = time.time() + float(retry_after)
        _RATE_LIMIT_UNTIL[user_id] = max(_RATE_LIMIT_UNTIL.get(user_id, 0.0), until)
    if callback:
        try:
            await callback.answer(
                f"Telegram просит подождать {int(retry_after)} сек.",
                show_alert=True,
            )
        except TelegramBadRequest:
            pass
    await asyncio.sleep(retry_after)


def rate_limit_remaining(user_id: int) -> int:
    until = _RATE_LIMIT_UNTIL.get(user_id, 0.0)
    remaining = int(round(max(0.0, until - time.time())))
    if remaining <= 0 and user_id in _RATE_LIMIT_UNTIL:
        _RATE_LIMIT_UNTIL.pop(user_id, None)
    return remaining


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


_original_send_message = Bot.send_message


async def _bot_send_message_with_retry(self: Bot, *args, **kwargs):
    attempts = 0
    while True:
        try:
            return await _original_send_message(self, *args, **kwargs)
        except TelegramRetryAfter as exc:
            if attempts >= 1:
                raise
            attempts += 1
            await _notify_retry_delay(None, exc.retry_after)


Bot.send_message = _bot_send_message_with_retry

_original_callback_answer = CallbackQuery.answer


async def _callback_answer_with_rate_limit(self: CallbackQuery, *args, **kwargs):
    if self.from_user:
        remaining = rate_limit_remaining(self.from_user.id)
        if remaining > 0:
            return await _original_callback_answer(
                self,
                f"Telegram просит подождать {remaining} сек.",
                show_alert=True,
            )
    return await _original_callback_answer(self, *args, **kwargs)


CallbackQuery.answer = _callback_answer_with_rate_limit
