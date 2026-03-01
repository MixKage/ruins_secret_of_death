from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.handlers.broadcast import send_season_summary_broadcast, send_server_crash_broadcast
from bot.handlers.helpers import is_admin_user
from bot.keyboards import (
    admin_crash_confirm_kb,
    admin_end_season_confirm_kb,
    admin_end_season_remind_kb,
    admin_kb,
)
from bot.api_client import (
    admin_season_advance as api_admin_season_advance,
    admin_season_badges as api_admin_season_badges,
    get_admin_panel as api_get_admin_panel,
    get_admin_season_prompt as api_get_admin_season_prompt,
)
from bot.utils.telegram import edit_or_send

router = Router()


async def _build_season_end_prompt(telegram_id: int) -> tuple[str, object, int | None]:
    response = await api_get_admin_season_prompt(telegram_id)
    text = response.get("text") or "Недоступно."
    action = response.get("action")
    last_processed = response.get("last_processed")
    markup = admin_end_season_confirm_kb() if action == "confirm" else admin_end_season_remind_kb()
    return text, markup, last_processed


async def _show_admin_panel(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    response = await api_get_admin_panel(callback.from_user.id)
    text = response.get("text") or "Админ панель недоступна."
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin")
async def admin_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:refresh")
async def admin_refresh(callback: CallbackQuery) -> None:
    await callback.answer("Обновляю...")
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:season_badges")
async def admin_season_badges(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    response = await api_admin_season_badges(callback.from_user.id)
    label = response.get("label") or "Сезон обновлен."
    await callback.answer(f"Пересчитано: {label}")
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:season_end")
async def admin_season_end_prompt(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    text, markup, _last_processed = await _build_season_end_prompt(callback.from_user.id)
    await edit_or_send(callback, text, reply_markup=markup)


@router.message(Command("admin_end_season"))
async def admin_end_season_command(message: Message) -> None:
    if not is_admin_user(message.from_user):
        await message.answer("Команда недоступна.")
        return
    text, markup, _last_processed = await _build_season_end_prompt(message.from_user.id)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "menu:admin:season_end:confirm")
async def admin_season_end_confirm(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    response = await api_admin_season_advance(callback.from_user.id)
    if response.get("status") != "ok":
        await callback.answer(response.get("message") or "Повышение сезона недоступно.", show_alert=True)
        await admin_season_end_prompt(callback)
        return
    closed_number = response.get("closed_number")
    if closed_number is None:
        await edit_or_send(callback, "Не удалось определить закрытый сезон.", reply_markup=admin_kb())
        return
    next_number = response.get("next_number") or (closed_number + 1)
    await callback.answer("Завершаю сезон...")
    sent, failed, total = await send_season_summary_broadcast(
        callback.bot,
        closed_number,
        recalc=True,
    )
    text = (
        f"Сезон {closed_number} завершен. Начат Сезон {next_number}.\n"
        f"Рассылка итогов: {sent}/{total}, ошибок {failed}."
    )
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin:season_end:remind")
async def admin_season_end_remind(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    _text, _markup, last_processed = await _build_season_end_prompt(callback.from_user.id)
    if last_processed is None:
        await callback.answer("Не удалось определить сезон.", show_alert=True)
        return
    await callback.answer("Отправляю напоминание...")
    sent, failed, total = await send_season_summary_broadcast(
        callback.bot,
        last_processed,
        recalc=False,
    )
    text = (
        f"Напоминание для Сезона {last_processed}: {sent}/{total}, ошибок {failed}."
    )
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin:season_end:cancel")
async def admin_season_end_cancel(callback: CallbackQuery) -> None:
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:crash")
async def admin_crash_prompt(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    await callback.answer()
    text = (
        "<b>Рассылка «Падение сервера»</b>\n"
        "Сообщение о технических неполадках будет отправлено всем игрокам.\n"
        "Эта рассылка не ограничена и может быть повторена."
    )
    await edit_or_send(callback, text, reply_markup=admin_crash_confirm_kb())


@router.callback_query(F.data == "menu:admin:crash:confirm")
async def admin_crash_send(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    await callback.answer("Начинаю рассылку...")
    sent, failed, total = await send_server_crash_broadcast(callback.bot)
    text = (
        "<b>Рассылка «Падение сервера» завершена.</b>\n"
        f"Отправлено: {sent}/{total}\n"
        f"Ошибок: {failed}"
    )
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin:crash:cancel")
async def admin_crash_cancel(callback: CallbackQuery) -> None:
    await callback.answer()
    await _show_admin_panel(callback)
