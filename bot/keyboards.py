from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(has_active_run: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_active_run:
        builder.button(text="Продолжить забег", callback_data="menu:continue")
        builder.button(text="Новый забег", callback_data="menu:new")
    else:
        builder.button(text="Начать забег", callback_data="menu:new")
    builder.button(text="Рейтинг", callback_data="menu:leaderboard")
    builder.button(text="Правила", callback_data="menu:rules")
    builder.adjust(1)
    return builder.as_markup()


def battle_kb(has_potion: bool, can_attack: bool, show_info: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_attack:
        builder.button(text="Атаковать", callback_data="action:attack")
    builder.button(text="Завершить ход", callback_data="action:endturn")
    if has_potion:
        builder.button(text="Зелье", callback_data="action:potion")
    info_text = "Скрыть справку" if show_info else "Справка"
    builder.button(text=info_text, callback_data="action:info")
    builder.button(text="Сдаться", callback_data="action:forfeit")
    builder.adjust(2)
    return builder.as_markup()


def reward_kb(reward_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx in range(reward_count):
        builder.button(text=f"{idx + 1}", callback_data=f"reward:{idx}")
    builder.adjust(reward_count)
    return builder.as_markup()


def event_kb(options: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(text=option["name"], callback_data=f"event:{option['id']}")
    builder.adjust(1)
    return builder.as_markup()
