import asyncio
import logging

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import CallbackQuery, BufferedInputFile, Message

from bot.config import get_admin_ids
from bot.handlers.helpers import is_admin_user
from bot.keyboards import broadcast_menu_kb, main_menu_kb
from bot.api_client import (
    admin_news_mark_sent as api_admin_news_mark_sent,
    admin_news_start as api_admin_news_start,
    get_active_run as api_get_active_run,
    get_all_broadcast_targets as api_get_all_broadcast_targets,
    get_broadcast_targets as api_get_broadcast_targets,
    get_broadcast_photo as api_get_broadcast_photo,
    get_season_summary as api_get_season_summary,
    mark_broadcast_sent as api_mark_broadcast_sent,
)

logger = logging.getLogger(__name__)
router = Router()

BALANCE_BROADCAST_KEY = "balance_update_v1"
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
    "<b>Сезон 3 в Руинах уже близко.</b>\n"
    "Мы не просто обновили цифры, мы пересобрали игру изнутри:\n"
    "- <b>Ребаланс прогрессии</b> — ранние и средние этажи стали ровнее по темпу, меньше “автопилота”, больше решений в бою.\n"
    "- <b>Новый босс: Хранитель Барьера</b> — встретит тех, кто заходит слишком глубоко и проверит, достоин ли ты идти дальше.\n"
    "- <b>Система отзывов</b> — теперь можно оставлять фидбек прямо в игре, чтобы мы быстрее правили баланс и UX по живым данным.\n"
    "- <b>Полностью переписанная архитектура</b> — проект переведён на новую backend-основу, API вынесено отдельно для стабильности и масштабирования.\n"
    "- <b>Что дальше</b> — скоро новые клиенты: <b>VK</b> и <b>Web</b>.\n\n"    
    "Сезон 3 — это новый фундамент Руин.\n"
    "<i>Поднимешься в таблице лидеров или пополнишь ряды павших?</i>"
)

SERVER_CRASH_TEXT = (
    "<b>Внимание, путники руин</b>\n"
    "В недрах произошли технические неполадки, но сейчас они полностью устранены.\n"
    "Благодарим за терпение — руины снова открыты для охоты.\n\n"
    "<i>Если заметите странности, сообщите смотрителям.</i>"
)

BALANCE_PHOTO_KEY = "balance_update"
SEASON_PHOTO_KEY = "season3"
SERVER_CRASH_PHOTO_KEY = "server_crash"


async def _send_balance_update(message: Message, telegram_id: int, photo_bytes: bytes | None) -> None:
    markup = broadcast_menu_kb()
    if photo_bytes:
        photo = BufferedInputFile(photo_bytes, filename="balance_update.jpg")
        await message.bot.send_photo(
            telegram_id,
            photo,
            caption=BALANCE_UPDATE_TEXT,
            reply_markup=markup,
        )
    else:
        await message.bot.send_message(telegram_id, BALANCE_UPDATE_TEXT, reply_markup=markup)

async def _send_season_update(message: Message, telegram_id: int, photo_bytes: bytes | None) -> None:
    markup = broadcast_menu_kb()
    if photo_bytes:
        photo = BufferedInputFile(photo_bytes, filename="season2.jpg")
        await message.bot.send_photo(
            telegram_id,
            photo,
            caption=SEASON_UPDATE_TEXT,
            reply_markup=markup,
        )
    else:
        await message.bot.send_message(telegram_id, SEASON_UPDATE_TEXT, reply_markup=markup)


async def _run_news_broadcast(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    logger.info("news command received: telegram_id=%s", user.id)

    admins = get_admin_ids()
    if admins and user.id not in admins:
        logger.info("news command denied: telegram_id=%s is not admin", user.id)
        await message.answer("Команда недоступна.")
        return

    await message.answer("Запускаю рассылку новостей...")

    try:
        response = await api_admin_news_start(user.id)
    except Exception:
        logger.exception("news command failed: admin/news request failed")
        await message.answer("Не удалось запустить рассылку: API недоступен.")
        return

    targets = response.get("targets", [])
    logger.info(
        "news command targets loaded: telegram_id=%s count=%s",
        user.id,
        len(targets),
    )
    if not targets:
        await message.answer("Нет пользователей для рассылки.")
        return

    photo_key = response.get("photo_key") or SEASON_PHOTO_KEY
    try:
        season_photo_bytes = await api_get_broadcast_photo(photo_key)
    except Exception:
        season_photo_bytes = None
    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку: {len(targets)} пользователей.")

    for entry in targets:
        user_id = entry.get("user_id")
        telegram_id = entry.get("telegram_id")
        if not user_id or not telegram_id:
            continue
        try:
            await _send_season_update(message, telegram_id, season_photo_bytes)
            await api_admin_news_mark_sent(user.id, user_id)
            sent += 1
        except TelegramRetryAfter as exc:
            logger.info(
                "Broadcast rate limit: waiting %.2f seconds before retry (telegram_id=%s)",
                exc.retry_after,
                telegram_id,
            )
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_season_update(message, telegram_id, season_photo_bytes)
                await api_admin_news_mark_sent(user.id, user_id)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            logger.exception("news broadcast unexpected error: user_id=%s telegram_id=%s", user_id, telegram_id)
            failed += 1
        await asyncio.sleep(0.05)

    logger.info("news command done: telegram_id=%s sent=%s failed=%s", user.id, sent, failed)
    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")


@router.message(Command("balance_update"))
async def balance_update(message: Message) -> None:
    user = message.from_user
    if user is None:
        return

    admins = get_admin_ids()
    if admins and user.id not in admins:
        await message.answer("Команда недоступна.")
        return

    response = await api_get_broadcast_targets(BALANCE_BROADCAST_KEY)
    targets = response.get("targets", [])
    if not targets:
        await message.answer("Нет пользователей для рассылки.")
        return

    try:
        balance_photo_bytes = await api_get_broadcast_photo(BALANCE_PHOTO_KEY)
    except Exception:
        balance_photo_bytes = None
    sent = 0
    failed = 0

    await message.answer(f"Начинаю рассылку: {len(targets)} пользователей.")

    for entry in targets:
        user_id = entry.get("user_id")
        telegram_id = entry.get("telegram_id")
        if not user_id or not telegram_id:
            continue
        try:
            await _send_balance_update(message, telegram_id, balance_photo_bytes)
            await api_mark_broadcast_sent(user_id, BALANCE_BROADCAST_KEY)
            sent += 1
        except TelegramRetryAfter as exc:
            logger.info(
                "Broadcast rate limit: waiting %.2f seconds before retry (telegram_id=%s)",
                exc.retry_after,
                telegram_id,
            )
            await asyncio.sleep(exc.retry_after)
            try:
                await _send_balance_update(message, telegram_id, balance_photo_bytes)
                await api_mark_broadcast_sent(user_id, BALANCE_BROADCAST_KEY)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"Рассылка завершена: отправлено {sent}, ошибок {failed}.")


@router.message(Command(commands=["news", "season_update"]))
async def news(message: Message) -> None:
    await _run_news_broadcast(message)


async def send_server_crash_broadcast(bot) -> tuple[int, int, int]:
    response = await api_get_all_broadcast_targets()
    targets = response.get("targets", [])
    if not targets:
        return 0, 0, 0
    try:
        crash_photo_bytes = await api_get_broadcast_photo(SERVER_CRASH_PHOTO_KEY)
    except Exception:
        crash_photo_bytes = None
    sent = 0
    failed = 0

    for entry in targets:
        telegram_id = entry.get("telegram_id")
        if not telegram_id:
            continue
        try:
            if crash_photo_bytes:
                photo = BufferedInputFile(crash_photo_bytes, filename="server_crashed.jpg")
                await bot.send_photo(telegram_id, photo, caption=SERVER_CRASH_TEXT)
            else:
                await bot.send_message(telegram_id, SERVER_CRASH_TEXT)
            sent += 1
        except TelegramRetryAfter as exc:
            logger.info(
                "Broadcast rate limit: waiting %.2f seconds before retry (telegram_id=%s)",
                exc.retry_after,
                telegram_id,
            )
            await asyncio.sleep(exc.retry_after)
            try:
                if crash_photo_bytes:
                    photo = BufferedInputFile(crash_photo_bytes, filename="server_crashed.jpg")
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


async def send_season_summary_broadcast(
    bot,
    season_number: int,
    recalc: bool,
) -> tuple[int, int, int]:
    response = await api_get_season_summary(season_number, recalc)
    if response.get("status") != "ok":
        return 0, 0, 0
    entries = response.get("entries", [])

    sent = 0
    failed = 0
    total = len(entries)

    for entry in entries:
        telegram_id = entry.get("telegram_id")
        text = entry.get("text")
        if not telegram_id or not text:
            continue
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except TelegramRetryAfter as exc:
            logger.info(
                "Broadcast rate limit: waiting %.2f seconds before retry (telegram_id=%s)",
                exc.retry_after,
                telegram_id,
            )
            await asyncio.sleep(exc.retry_after)
            try:
                await bot.send_message(telegram_id, text)
                sent += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(0.05)

    return sent, failed, total


@router.callback_query(F.data == "menu:broadcast")
async def broadcast_menu_callback(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    active = await api_get_active_run(user.id)
    has_active = bool(active.get("run_id"))
    await callback.answer()
    is_admin = is_admin_user(callback.from_user)
    await callback.bot.send_message(
        user.id,
        "Главное меню",
        reply_markup=main_menu_kb(has_active_run=has_active, is_admin=is_admin),
    )
