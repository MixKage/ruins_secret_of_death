from __future__ import annotations

import logging

import httpx
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

router = Router()
logger = logging.getLogger(__name__)

API_CONNECTION_ERROR_TEXT = "Проблема соединения с сервером. Попробуйте ещё раз."


@router.errors()
async def http_error_handler(event: ErrorEvent):
    exception = event.exception
    if not isinstance(exception, httpx.HTTPError):
        return

    logger.warning("HTTP error during update handling", exc_info=exception)
    update = event.update
    callback = update.callback_query
    if callback is not None:
        try:
            await callback.answer(API_CONNECTION_ERROR_TEXT, show_alert=True)
            return True
        except TelegramBadRequest:
            pass
        except Exception:
            pass
        if callback.from_user:
            try:
                await callback.bot.send_message(callback.from_user.id, API_CONNECTION_ERROR_TEXT)
            except Exception:
                pass
        return True

    message = update.message
    if message is not None:
        try:
            await message.answer(API_CONNECTION_ERROR_TEXT)
        except Exception:
            pass
        return True

    return True
