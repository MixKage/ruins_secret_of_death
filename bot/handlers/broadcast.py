import asyncio
from pathlib import Path

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from bot.config import get_admin_ids
from bot.db import get_broadcast_targets, mark_broadcast_sent

router = Router()

BROADCAST_KEY = "balance_update_v1"

BALANCE_UPDATE_TEXT = (
    "<b>Balance Update: руины стали опаснее</b>\n"
    "Был пересобран баланс глубин и усилены поздние этажи.\n"
    '- На старте игроку даётся 3 ОД, однако их количество теперь ограничивается максимальным значением ОД для текущего этажа.\n'
    "- Количество зелий ограничено: 10 маленьких, 5 средних, 2 сильных.\n"
    "- После 50 уровня враги подвергаются скверне, также встречаются элитные слуги с особыми механиками.\n"
    "- Проклятые этажи режут ОД до 3/4, а комнаты даруют больше зелий.\n"
    "- Дочь некроманта теперь появляется каждые 50 этажей, павшие герои - каждые 10.\n"
    "- Формулы урона и выживания обновлены для напряженной late‑game игры.\n"
    '- Добавлены новые состояния героя: "Решимость" и "На волоске".\n'
    "- Добавлены новые награды, а также добавлены незначительные улучшения в UI.\n\n"
    "<i>Собери волю в кулак и спускайся - руины ждут нового героя.</i>"
)

PHOTO_PATH = Path(__file__).resolve().parents[2] / "assets" / "balance_update.jpg"


async def _send_balance_update(message: Message, telegram_id: int, photo_exists: bool) -> None:
    if photo_exists:
        photo = FSInputFile(str(PHOTO_PATH))
        await message.bot.send_photo(telegram_id, photo, caption=BALANCE_UPDATE_TEXT)
    else:
        await message.bot.send_message(telegram_id, BALANCE_UPDATE_TEXT)


@router.message(Command("balance_update"))
async def balance_update(message: Message) -> None:
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
            await _send_balance_update(message, telegram_id, photo_exists)
            await mark_broadcast_sent(user_id, BROADCAST_KEY)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_balance_update(message, telegram_id, photo_exists)
                await mark_broadcast_sent(user_id, BROADCAST_KEY)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")
