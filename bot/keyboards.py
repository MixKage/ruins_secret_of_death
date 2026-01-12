from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(has_active_run: bool = False, is_admin: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_active_run:
        builder.button(text="Продолжить забег", callback_data="menu:continue")
        builder.button(text="Новый забег", callback_data="menu:new")
    else:
        builder.button(text="Начать забег", callback_data="menu:new")
    builder.button(text="Рейтинг", callback_data="menu:leaderboard")
    builder.button(text="Правила", callback_data="menu:rules")
    builder.button(text="Статистика", callback_data="menu:stats")
    builder.button(text="Личный кабинет", callback_data="menu:profile")
    if not has_active_run:
        builder.button(text="Поделиться", callback_data="menu:share")
    if is_admin:
        builder.button(text="Админ панель", callback_data="menu:admin")
    builder.adjust(1)
    return builder.as_markup()

def broadcast_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Начать приключение", callback_data="menu:broadcast")
    builder.adjust(1)
    return builder.as_markup()

def battle_kb(
    has_potion: bool,
    can_attack: bool,
    can_attack_all: bool,
    show_info: bool,
    can_endturn: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_attack:
        builder.button(text="Атаковать", callback_data="action:attack")
    if can_attack_all:
        builder.button(text="Атаковать на все ОД", callback_data="action:attack_all")
    if can_endturn:
        builder.button(text="Завершить ход", callback_data="action:endturn")
    if has_potion:
        builder.button(text="Зелье", callback_data="action:potion")
    builder.button(text="Инвентарь", callback_data="action:inventory")
    info_text = "Скрыть справку" if show_info else "Справка"
    builder.button(text=info_text, callback_data="action:info")
    builder.button(text="Сдаться", callback_data="action:forfeit")
    builder.adjust(2)
    return builder.as_markup()



def forfeit_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, сдаться", callback_data="forfeit:confirm")
    builder.button(text="Отмена", callback_data="forfeit:cancel")
    builder.adjust(2)
    return builder.as_markup()

def tutorial_fail_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Повторить обучение", callback_data="tutorial:restart")
    builder.button(text="Главное меню", callback_data="tutorial:menu")
    builder.adjust(1)
    return builder.as_markup()


def potion_kb(small_count: int, medium_count: int, strong_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if small_count > 0:
        builder.button(text=f"Малое ({small_count})", callback_data="potion:small")
    if medium_count > 0:
        builder.button(text=f"Среднее ({medium_count})", callback_data="potion:medium")
    if strong_count > 0:
        builder.button(text=f"Сильное ({strong_count})", callback_data="potion:strong")
    builder.button(text="Назад", callback_data="potion:back")
    builder.adjust(1)
    return builder.as_markup()

def inventory_kb(scrolls: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    grouped = {}
    order = []
    for scroll in scrolls:
        scroll_id = scroll.get("id") if isinstance(scroll, dict) else None
        if not scroll_id:
            continue
        if scroll_id not in grouped:
            grouped[scroll_id] = {
                "name": scroll.get("name", "Свиток"),
                "count": 0,
            }
            order.append(scroll_id)
        grouped[scroll_id]["count"] += 1
    for scroll_id in order:
        entry = grouped[scroll_id]
        label = entry["name"]
        if entry["count"] > 1:
            label = f"{label} x{entry['count']}"
        builder.button(text=label, callback_data=f"inventory:use_id:{scroll_id}")
    builder.button(text="Назад", callback_data="inventory:back")
    builder.adjust(1)
    return builder.as_markup()

def reward_kb(reward_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx in range(reward_count):
        builder.button(text=f"{idx + 1}", callback_data=f"reward:{idx}")
    builder.adjust(reward_count)
    return builder.as_markup()

def treasure_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Экипировать", callback_data="treasure:equip")
    builder.button(text="Оставить", callback_data="treasure:leave")
    builder.adjust(2)
    return builder.as_markup()

def boss_artifact_kb(options: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(text=option["name"], callback_data=f"boss:{option['id']}")
    builder.adjust(1)
    return builder.as_markup()

def admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Обновить", callback_data="menu:admin:refresh")
    builder.button(text="Пересчитать награды сезона", callback_data="menu:admin:season_badges")
    builder.button(text="Завершить сезон", callback_data="menu:admin:season_end")
    builder.button(text="Падение сервера", callback_data="menu:admin:crash")
    builder.button(text="Меню", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def admin_crash_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отправить", callback_data="menu:admin:crash:confirm")
    builder.button(text="Отмена", callback_data="menu:admin:crash:cancel")
    builder.adjust(2)
    return builder.as_markup()


def admin_end_season_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Завершить сезон", callback_data="menu:admin:season_end:confirm")
    builder.button(text="Отмена", callback_data="menu:admin:season_end:cancel")
    builder.adjust(2)
    return builder.as_markup()


def admin_end_season_remind_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Отправить напоминание", callback_data="menu:admin:season_end:remind")
    builder.button(text="Отмена", callback_data="menu:admin:season_end:cancel")
    builder.adjust(2)
    return builder.as_markup()

def leaderboard_kb(page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="<-", callback_data=f"menu:leaderboard:page:{page - 1}")
    builder.button(text="меню", callback_data="menu:main")
    builder.button(text="->", callback_data=f"menu:leaderboard:page:{page + 1}")
    builder.adjust(3)
    return builder.as_markup()

def rules_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="О наградах", callback_data="rules:badges")
    builder.button(text="О сезонах", callback_data="rules:seasons")
    builder.button(text="Оружие", callback_data="rules:weapons")
    builder.button(text="Противники", callback_data="rules:enemies")
    builder.button(text="Магия", callback_data="rules:magic")
    builder.button(text="Улучшения", callback_data="rules:upgrades")
    builder.button(text="Баланс", callback_data="rules:balance")
    builder.button(text="Назад", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()

def rules_back_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data="rules:menu")
    builder.adjust(1)
    return builder.as_markup()

def event_kb(options: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(text=option["name"], callback_data=f"event:{option['id']}")
    builder.adjust(1)
    return builder.as_markup()
