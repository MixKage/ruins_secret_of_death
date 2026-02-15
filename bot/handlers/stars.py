from __future__ import annotations

from typing import Tuple

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.api_client import stars_menu as api_stars_menu
from bot.api_client import stars_validate as api_stars_validate
from bot.api_client import stars_success as api_stars_success
from bot.handlers.helpers import is_admin_user
from bot.keyboards import profile_kb
from bot.game.logic import render_state
from bot.utils.telegram import edit_or_send


router = Router()

STARS_CURRENCY = "XTR"
STARS_PROVIDER_TOKEN = ""


def _stars_kb(packages: list[dict]):
    builder = InlineKeyboardBuilder()
    for entry in sorted(packages, key=lambda item: int(item.get("levels", 0))):
        levels = int(entry.get("levels", 0))
        stars = int(entry.get("stars", 0))
        label = str(entry.get("label", ""))
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
    response = await api_stars_menu()
    await callback.answer()
    await edit_or_send(
        callback,
        response.get("text", ""),
        reply_markup=_stars_kb(response.get("packages", [])),
    )


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
    response = await api_stars_menu()
    packages = response.get("packages", [])
    pack = next((item for item in packages if int(item.get("levels", 0)) == levels), None)
    if not pack:
        await callback.answer("Пакет недоступен.", show_alert=True)
        return
    stars = int(pack.get("stars", 0))
    label = str(pack.get("label", ""))
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
    if query.from_user is None:
        await query.answer(ok=False, error_message="Некорректный платеж.")
        return
    response = await api_stars_validate(
        payload=payload,
        telegram_id=query.from_user.id,
        currency=query.currency,
        total_amount=int(query.total_amount or 0),
    )
    if response.get("ok"):
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=response.get("error_message") or "Некорректный платеж.")


@router.message(F.successful_payment)
async def stars_success(message: Message) -> None:
    user = message.from_user
    if user is None or message.successful_payment is None:
        return
    payment = message.successful_payment
    response = await api_stars_success(
        payload=payment.invoice_payload or "",
        telegram_id=user.id,
        username=user.username,
        telegram_charge_id=payment.telegram_payment_charge_id,
        provider_charge_id=payment.provider_payment_charge_id,
        currency=payment.currency,
        total_amount=int(payment.total_amount or 0),
    )
    status = response.get("status")
    if status == "levels":
        message_text = response.get("message")
        if message_text:
            await message.answer(message_text)
        profile_text = response.get("profile_text")
        if profile_text:
            await message.answer(profile_text, reply_markup=profile_kb(can_unlock=bool(response.get("can_unlock"))))
        return
    if status == "second_chance":
        state = response.get("state")
        if state:
            from bot.handlers.game import _markup_for_state
            is_admin = is_admin_user(message.from_user)
            await message.answer(
                render_state(state),
                reply_markup=_markup_for_state(state, is_admin=is_admin),
            )
        return
