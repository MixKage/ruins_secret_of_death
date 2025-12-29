import asyncio
from pathlib import Path

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot import db
from bot.config import get_admin_ids
from bot.db import get_all_user_targets, get_broadcast_targets, mark_broadcast_sent
from bot.handlers.helpers import is_admin_user
from bot.keyboards import broadcast_menu_kb, main_menu_kb

router = Router()

BALANCE_BROADCAST_KEY = "balance_update_v1"
SEASON_BROADCAST_KEY = "season_update_v1"
BROADCAST_KEY = BALANCE_BROADCAST_KEY

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

SEASON_UPDATE_TEXT = (
    "<b>Season Update: руины вспоминают героев</b>\n"
    "Добавлен сезонный прогресс и личный кабинет героя.\n"
    "- Ежемесячные сезоны сбрасывают рейтинговую таблицу 1-го числа.\n"
    "- Сезонные значки за топовые места в рейтинге,а также (убийства, сундуки, сокровища).\n"
    "- Опыт за забеги и награды, уровни и прогресс-бар.\n"
    "- Личный кабинет с вашей историей, статистикой и коллекцией значков.\n"
    "- Расширенные правила и справки по механикам.\n\n"
    "<i>Сезон открыт. Время вернуть себе имя в руинах.</i>"
)

SERVER_CRASH_TEXT = (
    "<b>Внимание, путники руин</b>\n"
    "В недрах произошли технические неполадки, но сейчас они полностью устранены.\n"
    "Благодарим за терпение — руины снова открыты для охоты.\n\n"
    "<i>Если заметите странности, сообщите смотрителям.</i>"
)

BALANCE_PHOTO_PATH = Path(__file__).resolve().parents[2] / "assets" / "balance_update.jpg"
SEASON_PHOTO_PATH = Path(__file__).resolve().parents[2] / "assets" / "season_update.jpg"
SERVER_CRASH_PHOTO_PATH = Path(__file__).resolve().parents[2] / "assets" / "server_crashed.jpg"


async def _send_balance_update(message: Message, telegram_id: int, photo_exists: bool) -> None:
    markup = broadcast_menu_kb()
    if photo_exists:
        photo = FSInputFile(str(BALANCE_PHOTO_PATH))
        await message.bot.send_photo(
            telegram_id,
            photo,
            caption=BALANCE_UPDATE_TEXT,
            reply_markup=markup,
        )
    else:
        await message.bot.send_message(telegram_id, BALANCE_UPDATE_TEXT, reply_markup=markup)

async def _send_season_update(message: Message, telegram_id: int, photo_exists: bool) -> None:
    markup = broadcast_menu_kb()
    if photo_exists:
        photo = FSInputFile(str(SEASON_PHOTO_PATH))
        await message.bot.send_photo(
            telegram_id,
            photo,
            caption=SEASON_UPDATE_TEXT,
            reply_markup=markup,
        )
    else:
        await message.bot.send_message(telegram_id, SEASON_UPDATE_TEXT, reply_markup=markup)


@router.message(Command("balance_update"))
async def balance_update(message: Message) -> None:
    user = message.from_user
    if user is None:
        return

    admins = get_admin_ids()
    if admins and user.id not in admins:
        await message.answer("Команда недоступна.")
        return

    targets = await get_broadcast_targets(BALANCE_BROADCAST_KEY)
    if not targets:
        await message.answer("Нет пользователей для рассылки.")
        return

    photo_exists = BALANCE_PHOTO_PATH.exists()
    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку: {len(targets)} пользователей.")

    for user_id, telegram_id in targets:
        try:
            await _send_balance_update(message, telegram_id, photo_exists)
            await mark_broadcast_sent(user_id, BALANCE_BROADCAST_KEY)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_balance_update(message, telegram_id, photo_exists)
                await mark_broadcast_sent(user_id, BALANCE_BROADCAST_KEY)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")


@router.message(Command("season_update"))
async def season_update(message: Message) -> None:
    user = message.from_user
    if user is None:
        return

    admins = get_admin_ids()
    if admins and user.id not in admins:
        await message.answer("Команда недоступна.")
        return

    targets = await get_broadcast_targets(SEASON_BROADCAST_KEY)
    if not targets:
        await message.answer("Нет пользователей для рассылки.")
        return

    photo_exists = SEASON_PHOTO_PATH.exists()
    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку: {len(targets)} пользователей.")

    for user_id, telegram_id in targets:
        try:
            await _send_season_update(message, telegram_id, photo_exists)
            await mark_broadcast_sent(user_id, SEASON_BROADCAST_KEY)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_season_update(message, telegram_id, photo_exists)
                await mark_broadcast_sent(user_id, SEASON_BROADCAST_KEY)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")


async def send_server_crash_broadcast(bot) -> tuple[int, int, int]:
    targets = await get_all_user_targets()
    if not targets:
        return 0, 0, 0
    photo_exists = SERVER_CRASH_PHOTO_PATH.exists()
    sent = 0
    failed = 0

    for _, telegram_id in targets:
        try:
            if photo_exists:
                photo = FSInputFile(str(SERVER_CRASH_PHOTO_PATH))
                await bot.send_photo(telegram_id, photo, caption=SERVER_CRASH_TEXT)
            else:
                await bot.send_message(telegram_id, SERVER_CRASH_TEXT)
            sent += 1
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
            try:
                if photo_exists:
                    photo = FSInputFile(str(SERVER_CRASH_PHOTO_PATH))
                    await bot.send_photo(telegram_id, photo, caption=SERVER_CRASH_TEXT)
                else:
                    await bot.send_message(telegram_id, SERVER_CRASH_TEXT)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    return sent, failed, len(targets)


@router.callback_query(F.data == "menu:broadcast")
async def broadcast_menu_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    user_row = await db.get_user_by_telegram(user.id)
    has_active = False
    if user_row:
        has_active = bool(await db.get_active_run(user_row[0]))
    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await callback.bot.send_message(
        user.id,
        "Главное меню",
        reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin),
    )
