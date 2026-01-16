from __future__ import annotations

from typing import Dict, Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import db
from bot.progress import ensure_current_season, xp_for_level_increase, xp_to_level
from bot.utils.telegram import edit_or_send

router = Router()

STARS_CURRENCY = "XTR"
STARS_PROVIDER_TOKEN = ""

STARS_PACKAGES: Dict[int, Dict[str, int | str]] = {
    1: {"stars": 50, "label": "Уровень +1"},
    5: {"stars": 200, "label": "Уровень +5"},
}


def _stars_text() -> str:
    return "\n".join(
        [
            "<b>Stars / Уровни</b>",
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


def _parse_payload(payload: str) -> Tuple[int, int] | None:
    if not payload:
        return None
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "stars_levels":
        return None
    try:
        user_id = int(parts[1])
        levels = int(parts[2])
    except ValueError:
        return None
    return user_id, levels


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
    user_id, levels = parsed
    pack = STARS_PACKAGES.get(levels)
    if not pack:
        await query.answer(ok=False, error_message="Пакет недоступен.")
        return
    if query.from_user and query.from_user.id != user_id:
        await query.answer(ok=False, error_message="Платеж не для этого пользователя.")
        return
    if query.currency != STARS_CURRENCY or int(query.total_amount or 0) != int(pack["stars"]):
        await query.answer(ok=False, error_message="Неверная сумма оплаты.")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def stars_success(message: Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return
    payment = message.successful_payment
    parsed = _parse_payload(payment.invoice_payload or "")
    if not parsed:
        return
    user_id, levels = parsed
    if user.id != user_id:
        return
    pack = STARS_PACKAGES.get(levels)
    if not pack:
        return
    charge_id = payment.telegram_payment_charge_id
    if await db.has_star_purchase(charge_id):
        return
    profile = await db.get_user_profile(user_id)
    current_xp = int(profile.get("xp", 0)) if profile else 0
    xp_added = xp_for_level_increase(current_xp, levels)
    if xp_added <= 0:
        return
    await db.add_user_xp(user_id, xp_added)
    season_id, _ = await ensure_current_season()
    await db.add_season_xp(user_id, season_id, xp_added)
    await db.record_star_purchase(
        user_id=user_id,
        telegram_payment_charge_id=charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
        levels=levels,
        stars=int(pack["stars"]),
        xp_added=xp_added,
    )
    new_level, _current, _need = xp_to_level(current_xp + xp_added)
    await message.answer(
        f"Stars: +{levels} ур. успешно. Новый уровень: <b>{new_level}</b>."
    )
