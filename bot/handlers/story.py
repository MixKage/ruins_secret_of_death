from __future__ import annotations

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, BufferedInputFile, InputMediaPhoto

from bot.api_client import (
    get_story_state as api_get_story_state,
    get_story_chapter as api_get_story_chapter,
    get_story_photo as api_get_story_photo,
)
from bot.config import is_image_sending_enabled
from bot.keyboards import story_nav_kb

router = Router()
SEND_IMAGES = is_image_sending_enabled()


async def _send_chapter(callback: CallbackQuery, chapter: int, max_chapter: int) -> None:
    response = await api_get_story_chapter(chapter)
    caption = response.get("caption", "")
    markup = story_nav_kb(chapter, max_chapter)
    photo_exists = bool(response.get("has_photo")) and SEND_IMAGES

    if callback.message and callback.message.photo and photo_exists:
        try:
            photo_bytes = await api_get_story_photo(chapter)
        except Exception:
            photo_bytes = None
        if photo_bytes:
            media = InputMediaPhoto(
                media=BufferedInputFile(photo_bytes, filename=f"h{chapter}.jpg"),
                caption=caption,
                parse_mode="HTML",
            )
            try:
                await callback.message.edit_media(media=media, reply_markup=markup)
                await callback.answer()
                return
            except TelegramBadRequest as exc:
                if "message is not modified" in str(exc):
                    await callback.answer()
                    return

    if not callback.from_user:
        return

    if photo_exists:
        try:
            photo_bytes = await api_get_story_photo(chapter)
        except Exception:
            photo_bytes = None
        if photo_bytes:
            photo = BufferedInputFile(photo_bytes, filename=f"h{chapter}.jpg")
            await callback.bot.send_photo(
                callback.from_user.id,
                photo,
                caption=caption,
                reply_markup=markup,
                parse_mode="HTML",
            )
        else:
            await callback.bot.send_message(
                callback.from_user.id,
                caption,
                reply_markup=markup,
                parse_mode="HTML",
            )
    else:
        await callback.bot.send_message(
            callback.from_user.id,
            caption,
            reply_markup=markup,
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "menu:story")
async def story_menu(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    response = await api_get_story_state(user.id)
    max_chapter = int(response.get("max_chapter", 1))
    await _send_chapter(callback, max_chapter, max_chapter)


@router.callback_query(F.data.startswith("story:chapter:"))
async def story_chapter(callback: CallbackQuery) -> None:
    user = callback.from_user
    if user is None:
        return
    try:
        chapter = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer("Неверная глава.", show_alert=True)
        return
    if chapter < 1:
        await callback.answer("Неверная глава.", show_alert=True)
        return
    response = await api_get_story_state(user.id)
    max_chapter = int(response.get("max_chapter", 1))
    if chapter > max_chapter:
        await callback.answer("Эта глава пока закрыта.", show_alert=True)
        return
    await _send_chapter(callback, chapter, max_chapter)
