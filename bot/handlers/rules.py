from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.api_client import get_rules as api_get_rules
from bot.keyboards import rules_back_kb, rules_menu_kb
from bot.utils.telegram import edit_or_send

router = Router()

@router.callback_query(F.data == "menu:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("menu")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_menu_kb())


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    response = await api_get_rules("menu")
    await message.answer(response.get("text", ""), reply_markup=rules_menu_kb())


@router.callback_query(F.data == "rules:menu")
async def rules_menu_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("menu")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_menu_kb())


@router.callback_query(F.data == "rules:badges")
async def rules_badges_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("badges")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:seasons")
async def rules_seasons_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("seasons")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:weapons")
async def rules_weapons_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("weapons")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:enemies")
async def rules_enemies_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("enemies")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:magic")
async def rules_magic_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("magic")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:characters")
async def rules_characters_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("characters")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:upgrades")
async def rules_upgrades_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("upgrades")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:run_tasks")
async def rules_run_tasks_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("run_tasks")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:balance")
async def rules_balance_callback(callback: CallbackQuery) -> None:
    response = await api_get_rules("balance")
    await callback.answer()
    await edit_or_send(callback, response.get("text", ""), reply_markup=rules_back_kb())
