from html import escape

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot import db
from bot.handlers.broadcast import BROADCAST_KEY, send_season_summary_broadcast, send_server_crash_broadcast
from bot.handlers.helpers import is_admin_user
from bot.keyboards import (
    admin_crash_confirm_kb,
    admin_end_season_confirm_kb,
    admin_end_season_remind_kb,
    admin_kb,
)
from bot.progress import (
    advance_season_once,
    award_current_season_badges,
    award_latest_closed_season_badges,
    expected_season_number,
    get_last_processed_season,
    season_label,
    season_key_for_number,
)
from bot.utils.telegram import edit_or_send

router = Router()


def _format_admin_panel(stats: dict) -> str:
    avg_death_floor = stats.get("avg_death_floor", 0.0)
    avg_text = f"{avg_death_floor:.1f}" if avg_death_floor else "—"
    season_avg_death_floor = stats.get("season_avg_death_floor", 0.0)
    season_avg_text = f"{season_avg_death_floor:.1f}" if season_avg_death_floor else "—"
    season_deaths = stats.get("season_deaths", 0)
    runs_24h = stats.get("runs_24h", 0)
    users_24h = stats.get("users_24h", 0)
    top_killers = stats.get("top_killers", [])
    season_current_label = stats.get("season_current_label", "—")
    season_current_key = stats.get("season_current_key", "—")
    season_expected_label = stats.get("season_expected_label", "—")
    season_last_processed_label = stats.get("season_last_processed_label", "—")
    season_last_closed_label = stats.get("season_last_closed_label", "—")

    lines = [
        "<b>Админ панель</b>",
        f"<b>Игроков:</b> {stats.get('total_users', 0)}",
        f"<b>Активных забегов:</b> {stats.get('active_runs', 0)}",
        f"<b>Всего забегов:</b> {stats.get('total_runs', 0)}",
        f"<b>Смертей (всего):</b> {stats.get('total_deaths', 0)}",
        f"<b>Ср. этаж смерти (всего):</b> {avg_text}",
        f"<b>Смертей (сезон):</b> {season_deaths}",
        f"<b>Ср. этаж смерти (сезон):</b> {season_avg_text}",
        f"<b>Активность 24ч:</b> {runs_24h} забегов | {users_24h} игроков",
        f"<b>Сундуков открыто:</b> {stats.get('total_chests', 0)}",
        f"<b>Сокровищ найдено:</b> {stats.get('total_treasures', 0)}",
        f"<b>Макс. этаж (глобально):</b> {stats.get('max_floor', 0)}",
    ]

    lines.append("")
    lines.append("<b>Сезоны:</b>")
    lines.append(f"- Текущий: {season_current_label} ({season_current_key})")
    lines.append(f"- Ожидаемый по дате: {season_expected_label}")
    lines.append(f"- Последний обработанный: {season_last_processed_label}")
    lines.append(f"- Последний закрытый: {season_last_closed_label}")

    if top_killers:
        lines.append("")
        lines.append("<b>Топ-3 убийцы:</b>")
        for idx, (username, kills) in enumerate(top_killers, start=1):
            name = escape(username) if username else "Без имени"
            lines.append(f"{idx}. {name} — {kills}")

    lines.append("")
    lines.append(
        f"<b>Рассылка «Баланс»:</b> отправлено {stats.get('broadcast_sent', 0)} | "
        f"осталось {stats.get('broadcast_pending', 0)}"
    )

    return "\n".join(lines)


async def _build_season_end_prompt() -> tuple[str, object]:
    last_processed = await get_last_processed_season()
    expected = expected_season_number()
    if expected > last_processed:
        text = (
            f"<b>Завершить {season_label(season_key_for_number(last_processed))}</b>\n"
            f"Вы хотите завершить Сезон {last_processed} и начать Сезон {last_processed + 1}?\n"
            "Будет выполнен финальный перерасчет и рассылка статистики.\n"
            "Дата обновления соответствует календарю."
        )
        return text, admin_end_season_confirm_kb()
    text = (
        f"Текущий сезон ({last_processed}) уже актуален или новее ожидаемого "
        f"по дате ({expected}). Повторное повышение невозможно.\n"
        "Вы можете отправить игрокам напоминание с их статистикой за "
        "последний завершенный сезон."
    )
    return text, admin_end_season_remind_kb()


async def _show_admin_panel(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    stats = await db.get_admin_stats(BROADCAST_KEY)
    if not stats:
        await edit_or_send(callback, "Админ панель недоступна.", reply_markup=admin_kb())
        return
    season_id, season_key, _prev = await db.get_or_create_current_season()
    last_processed = await get_last_processed_season()
    expected = expected_season_number()
    last_closed = await db.get_last_season(ended_only=True)
    season_deaths, season_avg_death_floor = await db.get_season_death_stats(season_id)
    stats["season_current_label"] = season_label(season_key)
    stats["season_current_key"] = season_key
    stats["season_expected_label"] = season_label(season_key_for_number(expected))
    stats["season_last_processed_label"] = season_label(season_key_for_number(last_processed))
    stats["season_last_closed_label"] = (
        season_label(last_closed[1]) if last_closed else "—"
    )
    stats["season_deaths"] = season_deaths
    stats["season_avg_death_floor"] = season_avg_death_floor
    text = _format_admin_panel(stats)
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
    season_key = await award_latest_closed_season_badges()
    if season_key:
        await callback.answer(f"Пересчитано: {season_label(season_key)}")
    else:
        season_key = await award_current_season_badges()
        await callback.answer(f"Пересчитано: {season_label(season_key)} (текущий)")
    await _show_admin_panel(callback)


@router.callback_query(F.data == "menu:admin:season_end")
async def admin_season_end_prompt(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    text, markup = await _build_season_end_prompt()
    await edit_or_send(callback, text, reply_markup=markup)


@router.message(Command("admin_end_season"))
async def admin_end_season_command(message: Message) -> None:
    if not is_admin_user(message.from_user):
        await message.answer("Команда недоступна.")
        return
    text, markup = await _build_season_end_prompt()
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "menu:admin:season_end:confirm")
async def admin_season_end_confirm(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    last_processed = await get_last_processed_season()
    expected = expected_season_number()
    if expected <= last_processed:
        await callback.answer("Повышение сезона недоступно.", show_alert=True)
        await admin_season_end_prompt(callback)
        return
    await callback.answer("Завершаю сезон...")
    await advance_season_once()
    closed_number = last_processed
    sent, failed, total = await send_season_summary_broadcast(
        callback.bot,
        closed_number,
        recalc=True,
    )
    text = (
        f"Сезон {closed_number} завершен. Начат Сезон {closed_number + 1}.\n"
        f"Рассылка итогов: {sent}/{total}, ошибок {failed}."
    )
    await edit_or_send(callback, text, reply_markup=admin_kb())


@router.callback_query(F.data == "menu:admin:season_end:remind")
async def admin_season_end_remind(callback: CallbackQuery) -> None:
    if not is_admin_user(callback.from_user):
        await callback.answer("Команда недоступна.", show_alert=True)
        return
    last_processed = await get_last_processed_season()
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
