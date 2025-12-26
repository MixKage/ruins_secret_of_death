import asyncio
from pathlib import Path

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from bot.config import get_admin_ids
from bot.db import get_broadcast_targets, mark_broadcast_sent

router = Router()

BROADCAST_KEY = "magic_update_v1"

MAGIC_UPDATE_TEXT = (
    "<b>В руинах пробудилась магия</b>\n"
    "Стены руин дрожат — стихии вошли в игру.\n"
    "— Свитки огня, льда и молнии теперь можно найти в сундуках.\n"
    "— Ледяной свиток выдается в начале забега.\n"
    "— Магия игнорирует броню, а молния бьет по всем врагам.\n"
    "<i>Время спускаться глубже.</i>"
)

PHOTO_PATH = Path(__file__).resolve().parents[2] / "assets" / "magic_update_ruins.jpg"


async def _send_magic_update(message: Message, telegram_id: int, photo_exists: bool) -> None:
    if photo_exists:
        photo = FSInputFile(str(PHOTO_PATH))
        await message.bot.send_photo(telegram_id, photo, caption=MAGIC_UPDATE_TEXT)
    else:
        await message.bot.send_message(telegram_id, MAGIC_UPDATE_TEXT)


@router.message(Command("magic_update"))
async def magic_update(message: Message) -> None:
    user = message.from_user
    if user is None:
        return

    admins = get_admin_ids()
    if admins and user.id not in admins:
        await message.answer("Команда недоступна.")
        return

    targets = await get_broadcast_targets(BROADCAST_KEY)
    if not targets:
        await message.answer("Нет пользователей для рассылки.")
        return

    photo_exists = PHOTO_PATH.exists()
    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку: {len(targets)} пользователей.")

    for user_id, telegram_id in targets:
        try:
            await _send_magic_update(message, telegram_id, photo_exists)
            await mark_broadcast_sent(user_id, BROADCAST_KEY)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_magic_update(message, telegram_id, photo_exists)
                await mark_broadcast_sent(user_id, BROADCAST_KEY)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")
