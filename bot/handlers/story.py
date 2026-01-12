from __future__ import annotations

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto

from bot import db
from bot.handlers.helpers import get_user_row
from bot.keyboards import story_nav_kb
from bot.progress import xp_to_level
from bot.story import build_chapter_caption, chapter_photo_path, max_unlocked_chapter, STORY_MAX_CHAPTERS

router = Router()


async def _user_level(user_id: int) -> int:
    profile = await db.get_user_profile(user_id)
    xp = int(profile.get("xp", 0)) if profile else 0
    level, _current, _need = xp_to_level(xp)
    return level


async def _send_chapter(callback: CallbackQuery, chapter: int, max_chapter: int) -> None:
    caption = build_chapter_caption(chapter)
    photo_path = chapter_photo_path(chapter)
    markup = story_nav_kb(chapter, max_chapter)
    photo_exists = photo_path.exists()

    if callback.message and callback.message.photo and photo_exists:
        media = InputMediaPhoto(
            media=FSInputFile(str(photo_path)),
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
        photo = FSInputFile(str(photo_path))
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
    await callback.answer()


@router.callback_query(F.data == "menu:story")
async def story_menu(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    level = await _user_level(user_row[0])
    max_chapter = max_unlocked_chapter(level)
    await _send_chapter(callback, max_chapter, max_chapter)


@router.callback_query(F.data.startswith("story:chapter:"))
async def story_chapter(callback: CallbackQuery) -> None:
    user_row = await get_user_row(callback)
    if not user_row:
        return
    try:
        chapter = int(callback.data.split(":")[-1])
    except (ValueError, AttributeError):
        await callback.answer("Неверная глава.", show_alert=True)
        return
    if chapter < 1 or chapter > STORY_MAX_CHAPTERS:
        await callback.answer("Неверная глава.", show_alert=True)
        return
    level = await _user_level(user_row[0])
    max_chapter = max_unlocked_chapter(level)
    if chapter > max_chapter:
        await callback.answer("Эта глава пока закрыта.", show_alert=True)
        return
    await _send_chapter(callback, chapter, max_chapter)
