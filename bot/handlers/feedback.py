from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User

from bot.api_client import create_feedback as api_create_feedback
from bot.api_client import get_active_run as api_get_active_run
from bot.handlers.helpers import is_admin_user
from bot.keyboards import feedback_categories_kb, feedback_input_kb, main_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()

MIN_FEEDBACK_LENGTH = 5
MAX_FEEDBACK_LENGTH = 2000
FEEDBACK_CATEGORY_LABELS = {
    "bug": "Баг",
    "balance": "Баланс",
    "idea": "Идея",
    "other": "Другое",
}


class FeedbackFlow(StatesGroup):
    waiting_message = State()


async def _main_menu_markup(user: User | None):
    has_active_run = False
    if user is not None:
        try:
            active = await api_get_active_run(user.id)
            has_active_run = bool(active.get("run_id"))
        except Exception:
            has_active_run = False
    return main_menu_kb(has_active_run=has_active_run, is_admin=is_admin_user(user))


def _feedback_intro_text() -> str:
    return (
        "<b>Обратная связь</b>\n"
        "Выберите категорию и отправьте отзыв одним сообщением.\n"
        "Мы читаем каждое обращение."
    )


@router.callback_query(F.data == "menu:feedback")
async def feedback_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await edit_or_send(callback, _feedback_intro_text(), reply_markup=feedback_categories_kb())


@router.message(Command("feedback"))
async def feedback_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(_feedback_intro_text(), reply_markup=feedback_categories_kb())


@router.callback_query(F.data.startswith("feedback:category:"))
async def feedback_select_category(callback: CallbackQuery, state: FSMContext) -> None:
    parts = (callback.data or "").split(":")
    category = parts[2] if len(parts) >= 3 else ""
    if category not in FEEDBACK_CATEGORY_LABELS:
        await callback.answer("Категория недоступна.", show_alert=True)
        return

    await state.set_state(FeedbackFlow.waiting_message)
    await state.update_data(category=category, source="menu")
    await callback.answer()
    await edit_or_send(
        callback,
        (
            f"<b>Категория:</b> {FEEDBACK_CATEGORY_LABELS[category]}\n"
            "Напишите отзыв одним сообщением.\n"
            f"Длина: от {MIN_FEEDBACK_LENGTH} до {MAX_FEEDBACK_LENGTH} символов."
        ),
        reply_markup=feedback_input_kb(),
    )


@router.callback_query(F.data == "feedback:change_category")
async def feedback_change_category(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer()
    await edit_or_send(callback, _feedback_intro_text(), reply_markup=feedback_categories_kb())


@router.callback_query(F.data == "feedback:cancel")
async def feedback_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Отмена.")
    await edit_or_send(
        callback,
        "Главное меню",
        reply_markup=await _main_menu_markup(callback.from_user),
    )


@router.message(FeedbackFlow.waiting_message, Command("cancel"))
async def feedback_cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Отправка отзыва отменена.",
        reply_markup=await _main_menu_markup(message.from_user),
    )


@router.message(FeedbackFlow.waiting_message, F.text)
async def feedback_submit(message: Message, state: FSMContext) -> None:
    user = message.from_user
    if user is None:
        return

    feedback_text = (message.text or "").strip()
    if feedback_text.startswith("/"):
        await message.answer("Сейчас идет отправка отзыва. Используйте /cancel для отмены.")
        return
    if len(feedback_text) < MIN_FEEDBACK_LENGTH:
        await message.answer(
            f"Отзыв слишком короткий. Минимум {MIN_FEEDBACK_LENGTH} символов."
        )
        return
    if len(feedback_text) > MAX_FEEDBACK_LENGTH:
        await message.answer(
            f"Отзыв слишком длинный. Максимум {MAX_FEEDBACK_LENGTH} символов."
        )
        return

    state_data = await state.get_data()
    category = state_data.get("category")
    if category not in FEEDBACK_CATEGORY_LABELS:
        await state.clear()
        await message.answer(
            "Категория не выбрана. Нажмите «Обратная связь» в меню и попробуйте снова.",
            reply_markup=await _main_menu_markup(user),
        )
        return

    context = {"chat_id": message.chat.id}
    if message.message_thread_id is not None:
        context["message_thread_id"] = message.message_thread_id

    try:
        response = await api_create_feedback(
            telegram_id=user.id,
            username=user.username,
            category=category,
            message=feedback_text,
            source=str(state_data.get("source") or "menu"),
            context=context,
        )
    except Exception:
        await message.answer(
            "Не удалось отправить отзыв. Попробуйте позже.",
            reply_markup=await _main_menu_markup(user),
        )
        return

    await state.clear()
    feedback_id = response.get("feedback_id")
    if feedback_id is not None:
        text = (
            "<b>Спасибо, отзыв принят.</b>\n"
            f"Номер: <code>#{feedback_id}</code>"
        )
    else:
        text = "<b>Спасибо, отзыв принят.</b>"
    await message.answer(text, reply_markup=await _main_menu_markup(user))


@router.message(FeedbackFlow.waiting_message)
async def feedback_waiting_non_text(message: Message) -> None:
    await message.answer("Отправьте отзыв текстом одним сообщением.")
