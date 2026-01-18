from __future__ import annotations

from typing import Dict, Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import db
from bot.handlers.helpers import is_admin_user
from bot.handlers.heroes import _unlock_state
from bot.handlers.profile import build_profile_text
from bot.keyboards import profile_kb
from bot.game.logic import render_state
from bot.progress import ensure_current_season, xp_for_level_increase, xp_to_level
from bot.utils.telegram import edit_or_send


router = Router()

STARS_CURRENCY = "XTR"
STARS_PROVIDER_TOKEN = ""
SECOND_CHANCE_STARS = 2
STARS_PACKAGES: Dict[int, Dict[str, int | str]] = {
    1: {"stars": 50, "label": "Уровень +1"},
    5: {"stars": 200, "label": "Уровень +5"},
}


def _stars_text() -> str:
    return "\n".join(
        [
            "<b>Уровни за ⭐</b>",
            "Покупка повышает уровень ровно на выбранное число.",
            "XP начисляется автоматически и учитывается в сезоне.",
        ]
    )


def _stars_kb():
    builder = InlineKeyboardBuilder()
    for levels in sorted(STARS_PACKAGES):
        pack = STARS_PACKAGES[levels]
        stars = int(pack["stars"])
        label = str(pack["label"])
        builder.button(
            text=f"{stars}⭐ — {label}",
            callback_data=f"stars:buy:{levels}",
        )
    builder.button(text="Назад", callback_data="menu:profile")
    builder.adjust(1)
    return builder.as_markup()


def _parse_payload(payload: str) -> Tuple[str, int, int] | None:
    if not payload:
        return None
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "stars_levels":
        if len(parts) != 3 or parts[0] != "stars_second_chance":
            return None
    try:
        user_id = int(parts[1])
        value = int(parts[2])
    except ValueError:
        return None
    if parts[0] == "stars_levels":
        return "levels", user_id, value
    return "second_chance", user_id, value


@router.callback_query(F.data == "profile:stars")
async def stars_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _stars_text(), reply_markup=_stars_kb())


@router.callback_query(F.data.startswith("stars:buy:"))
async def stars_buy(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    parts = callback.data.split(":")
    if len(parts) < 3:
        await callback.answer("Неверный пакет.", show_alert=True)
        return
    try:
        levels = int(parts[2])
    except ValueError:
        await callback.answer("Неверный пакет.", show_alert=True)
        return
    pack = STARS_PACKAGES.get(levels)
    if not pack:
        await callback.answer("Пакет недоступен.", show_alert=True)
        return
    stars = int(pack["stars"])
    label = str(pack["label"])
    payload = f"stars_levels:{callback.from_user.id}:{levels}"
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title=label,
        description=f"Повышение уровня на {levels}.",
        payload=payload,
        currency=STARS_CURRENCY,
        prices=[LabeledPrice(label=label, amount=stars)],
        provider_token=STARS_PROVIDER_TOKEN,
    )
    await callback.answer()


@router.pre_checkout_query()
async def stars_pre_checkout(query: PreCheckoutQuery) -> None:
    payload = query.invoice_payload or ""
    parsed = _parse_payload(payload)
    if not parsed:
        await query.answer(ok=False, error_message="Некорректный платеж.")
        return
    kind, user_id, value = parsed
    if query.from_user and query.from_user.id != user_id:
        await query.answer(ok=False, error_message="Платеж не для этого пользователя.")
        return
    if kind == "levels":
        pack = STARS_PACKAGES.get(value)
        if not pack:
            await query.answer(ok=False, error_message="Пакет недоступен.")
            return
        if query.currency != STARS_CURRENCY or int(query.total_amount or 0) != int(pack["stars"]):
            await query.answer(ok=False, error_message="Неверная сумма оплаты.")
            return
        await query.answer(ok=True)
        return
    if kind == "second_chance":
        if query.currency != STARS_CURRENCY or int(query.total_amount or 0) != int(SECOND_CHANCE_STARS):
            await query.answer(ok=False, error_message="Неверная сумма оплаты.")
            return
        user_row = await db.get_user_by_telegram(user_id)
        if not user_row:
            await query.answer(ok=False, error_message="Пользователь не найден.")
            return
        run_row = await db.get_run_by_id(value)
        if not run_row:
            await query.answer(ok=False, error_message="Забег не найден.")
            return
        run_user_id, is_active, state = run_row
        if (
            not is_active
            or run_user_id != user_row[0]
            or state.get("phase") != "second_chance_offer"
            or state.get("second_chance_offer_type") != "buy"
        ):
            await query.answer(ok=False, error_message="Второй шанс недоступен.")
            return
        await query.answer(ok=True)
        return
    await query.answer(ok=False, error_message="Некорректный платеж.")


@router.message(F.successful_payment)
async def stars_success(message: Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return
    payment = message.successful_payment
    parsed = _parse_payload(payment.invoice_payload or "")
    if not parsed:
        return
    kind, user_id, value = parsed
    if user.id != user_id:
        return
    if kind == "levels":
        levels = value
        pack = STARS_PACKAGES.get(levels)
        if not pack:
            return
        internal_user_id = await db.ensure_user(user_id, user.username)
        charge_id = payment.telegram_payment_charge_id
        if await db.has_star_purchase(charge_id):
            return
        profile = await db.get_user_profile(internal_user_id)
        current_xp = int(profile.get("xp", 0)) if profile else 0
        xp_added = xp_for_level_increase(current_xp, levels)
        if xp_added <= 0:
            return
        await db.add_user_xp(internal_user_id, xp_added)
        season_id, _ = await ensure_current_season()
        await db.add_season_xp(internal_user_id, season_id, xp_added)
        await db.record_star_purchase(
            user_id=internal_user_id,
            telegram_payment_charge_id=charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
            levels=levels,
            stars=int(pack["stars"]),
            xp_added=xp_added,
        )
        new_level, _current, _need = xp_to_level(current_xp + xp_added)
        is_admin = is_admin_user(message.from_user)
        unlocked_ids = await db.get_unlocked_heroes(internal_user_id)
        _unlocked_set, available, required_level, _total_unlockable = _unlock_state(
            new_level,
            unlocked_ids,
            is_admin=is_admin,
        )
        if available > 0:
            slot_note = "Вам доступен новый слот открытия персонажа."
        elif required_level:
            remaining = max(0, required_level - new_level)
            slot_note = f"Осталось уровней до нового слота персонажей: {remaining}."
        else:
            slot_note = "Все герои уже открыты."
        await message.answer(
            (
                f"Спасибо, что поддержали наш проект! Поздравляем с успешной покупкой "
                f"нового уровня (+{levels}). Теперь ваш уровень: <b>{new_level}</b>. {slot_note}"
            )
        )
        profile_text, can_unlock = await build_profile_text(internal_user_id, is_admin=is_admin)
        await message.answer(profile_text, reply_markup=profile_kb(can_unlock=can_unlock))
        return
    if kind == "second_chance":
        run_id = value
        internal_user_id = await db.ensure_user(user_id, user.username)
        charge_id = payment.telegram_payment_charge_id
        if await db.has_star_action(charge_id):
            return
        run_row = await db.get_run_by_id(run_id)
        if not run_row:
            return
        run_user_id, is_active, state = run_row
        if (
            not is_active
            or run_user_id != internal_user_id
            or state.get("phase") != "second_chance_offer"
            or state.get("second_chance_offer_type") != "buy"
        ):
            return
        from bot.game.logic import apply_second_chance
        from bot.handlers.game import _markup_for_state
        apply_second_chance(state, note="Амулет второго шанса выкуплен: 1 HP и полный запас ОД.")
        await db.update_run(run_id, state)
        await db.record_star_action(
            user_id=internal_user_id,
            telegram_payment_charge_id=charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
            action="second_chance",
            stars=SECOND_CHANCE_STARS,
        )
        is_admin = is_admin_user(message.from_user)
        await message.answer(
            render_state(state),
            reply_markup=_markup_for_state(state, is_admin=is_admin),
        )
        return
