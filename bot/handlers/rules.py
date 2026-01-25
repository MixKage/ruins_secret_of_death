from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.game.characters import CHARACTERS
from bot.game.data import ENEMIES, SCROLLS, UPGRADES, WEAPONS
from bot.game.logic import WEAPON_RARITY_TIERS
from bot.keyboards import rules_back_kb, rules_menu_kb
from bot.progress import BADGES, LEVEL_BASE_XP, LEVEL_STEP_XP
from bot.utils.telegram import edit_or_send

router = Router()

BADGE_REQUIREMENTS = {
    "season_top1": "Место #1 в рейтинге сезона",
    "season_top2": "Место #2 в рейтинге сезона",
    "season_top3": "Место #3 в рейтинге сезона",
    "season_top10": "Топ-10 сезона",
    "season_most_kills": "Больше всех убийств за сезон",
    "season_most_chests": "Больше всех сундуков за сезон",
    "season_most_treasures": "Больше всех сокровищ за сезон",
    "season_highest_floor": "Самый высокий этаж сезона",
    "season_most_runs": "Больше всех забегов за сезон",
    "first_pioneer": "Игроки, зарегистрированные до 2026 года",
}

RULES_MENU_TEXT = (
    "<b>Правила и справка</b>\n"
    "Выберите раздел ниже, чтобы узнать детали о механиках руин и героях."
)


def _format_badges() -> str:
    lines = [
        "<b>Награды сезона</b>",
        "<i>Выдаются при завершении сезона.</i>",
        "<i>Сезонные награды сохраняются в истории и могут стакаться (x2 и т.д.).</i>",
        "",
    ]
    for badge_id, badge in BADGES.items():
        requirement = BADGE_REQUIREMENTS.get(badge_id, "Особая награда")
        xp = f"+{badge.xp} XP" if badge.xp else "+0 XP"
        lines.append(f"- <b>{badge.name}</b> — <i>{requirement}</i> ({xp})")
    lines.append("")
    lines.append(
        f"<i>Уровни опыта:</i> базовый порог {LEVEL_BASE_XP} XP, каждый следующий +{LEVEL_STEP_XP} XP."
    )
    return "\n".join(lines)


def _format_seasons() -> str:
    return "\n".join(
        [
            "<b>Сезоны</b>",
            "Рейтинг обновляется <b>1-го числа каждого месяца</b>.",
            "Сезон 0 стартует 20.12.2025 (2025-12).",
            "В сезонной таблице учитывается <b>максимальный этаж</b> за сезон.",
            "Сезонные награды сохраняются навсегда и отображаются в истории.",
        ]
    )


def _format_weapons() -> str:
    lines = ["<b>Оружие</b>", "<i>Свойства оружия:</i>"]
    for item in WEAPONS:
        parts = [f"урон {item['min_dmg']}-{item['max_dmg']}"]
        acc = item.get("accuracy_bonus", 0.0)
        if acc:
            sign = "+" if acc > 0 else ""
            parts.append(f"точность {sign}{int(round(acc * 100))}%")
        splash = item.get("splash_ratio", 0.0)
        if splash:
            parts.append(f"сплэш {int(round(splash * 100))}%")
        bleed = item.get("bleed_chance", 0.0)
        if bleed:
            parts.append(f"кровотечение {int(round(bleed * 100))}%/{item.get('bleed_damage', 0)}")
        pierce = item.get("armor_pierce", 0.0)
        if pierce:
            parts.append(f"бронепробой {int(round(pierce * 100))}%")
        lines.append(f"- <b>{item['name']}</b> ({' | '.join(parts)})")
    lines.append("")
    lines.append("<i>Редкость (префиксы) по этажам:</i>")
    for min_floor, name in WEAPON_RARITY_TIERS:
        lines.append(f"- {name} — с {min_floor} этажа")
    return "\n".join(lines)


def _format_enemies() -> str:
    lines = [
        "<b>Противники</b>",
        "После 10 этажа враги мутируют, а после 50 становятся <b>Оскверненными</b>.",
        "Элиты (50+): <b>Проклятый Клинок тени</b>, <b>Проклятый Окаменелый Хранитель</b>, <b>Проклятый Слепой охотник</b>.",
        "",
    ]
    for item in ENEMIES:
        min_floor = item.get("min_floor", 1)
        max_floor = item.get("max_floor", 999)
        floor_label = f"{min_floor}+" if max_floor >= 999 else f"{min_floor}-{max_floor}"
        lines.append(f"- <b>{item['name']}</b> — этажи {floor_label}")
    lines.append("")
    lines.append("<i>Боссы:</i>")
    lines.append("- Некромант — 10 этаж.")
    lines.append("- Павший герой — каждые 10 этажей после 10 (кроме кратных 50).")
    lines.append("- Дочь некроманта — каждые 50 этажей.")
    lines.append("- Павший герой частично игнорирует уклонение и <b>не промахивается</b>.")
    lines.append("- Некромант и Дочь некроманта <b>не промахиваются</b>.")
    lines.append("- Награда Павшего героя: +5 к макс. HP и сильное зелье.")
    lines.append("- Награда Дочери некроманта: +5 к макс. HP, пополнение зелий до половины, свиток молнии и +10 XP.")
    return "\n".join(lines)


def _format_magic() -> str:
    lines = [
        "<b>Магия</b>",
        "Свитки тратят 1 ОД и <b>игнорируют броню</b>.",
        "Урон: max(20, (weapon.max_dmg + power) * ap_max).",
        "Решимость (Рыцарь, полное здоровье) усиливает урон магии.",
    ]
    for scroll in SCROLLS:
        desc = scroll.get("desc", "").strip()
        line = f"- <b>{scroll['name']}</b>"
        if desc:
            line += f" — <i>{desc}</i>"
        lines.append(line)
    lines.append("Свиток молнии появляется в сундуках с 15 этажа.")
    return "\n".join(lines)


def _format_characters() -> str:
    lines = [
        "<b>Игровые персонажи</b>",
        "Каждый герой имеет уникальные эффекты и стартовые параметры.",
        "Новые герои открываются каждые 5 уровней, Рыцарь доступен сразу.",
        "",
    ]
    for character in CHARACTERS.values():
        name = character.get("name", "Герой")
        lines.append(f"<b>{name}</b>")
        for desc in character.get("description", []):
            lines.append(f"- {desc}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _format_upgrades() -> str:
    lines = ["<b>Улучшения</b>"]
    for item in UPGRADES:
        min_floor = item.get("min_floor", 1)
        lines.append(f"- <b>{item['name']}</b> — с {min_floor} этажа")
    lines.append("")
    lines.append("<i>Лимиты зелий:</i> малые 10, средние 5, сильные 2.")
    return "\n".join(lines)


def _format_run_tasks() -> str:
    return "\n".join(
        [
            "<b>Испытания руин</b>",
            "Набор испытаний обновляется каждые <b>30 минут</b> (UTC).",
            "Испытания действуют <b>только на один забег</b> и фиксируются при старте.",
            "В каждом забеге — <b>3 задачи</b>: минимум одна боевая и одна по прогрессу.",
            "Примеры задач: убить X врагов, убить конкретного врага, дойти до N этажа, победить босса.",
            "За выполнение каждой задачи дается <b>+10 XP</b>.",
        ]
    )


def _format_balance() -> str:
    lines = [
        "<b>Баланс и прогресс</b>",
        "- Враги усиливаются по формуле base + per_floor.",
        "- Бюджет урона группы = hp_max героя * коэффициент этажа.",
        "- Броня режет 70% урона, 30% проходит всегда.",
        "- После 50 этажа враги получают бронепробой (до 20%).",
        "- После 50 этажа обычные враги переживают полный ход героя.",
        "- После 50 этажа уклонение приглушается.",
        "- Проклятые этажи (50+): ОД снижены до 3/4.",
        "- Этажи 1-3: 1 враг, 4-6: до 2, дальше: до 3+.",
        "- Комнаты между этажами: источник благодати, сундук древних, костер паломника.",
        "- Комнаты 'Сундук древних' и 'Костер паломника' не повторяются подряд.",
        "- Костер паломника даёт +4 к макс. HP Стражу рун.",
        "- Лимиты брони/уклонения: до 50 этажа броня ≤ 4, уклонение ≤ 40%; до 100 этажа — броня ≤ 6, уклонение ≤ 80%.",
        "- XP за забег = этажи + сокровища (по 5 XP). Убийства XP не дают.",
        "- Перед боссом выбирается артефакт: Печать ярости (+2 урона), Печать воли (+1 ОД), Алхимический набор (2 средних зелья + свиток).",
    ]
    return "\n".join(lines)


@router.callback_query(F.data == "menu:rules")
async def rules_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, RULES_MENU_TEXT, reply_markup=rules_menu_kb())


@router.message(Command("rules"))
async def rules_command(message: Message) -> None:
    await message.answer(RULES_MENU_TEXT, reply_markup=rules_menu_kb())


@router.callback_query(F.data == "rules:menu")
async def rules_menu_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, RULES_MENU_TEXT, reply_markup=rules_menu_kb())


@router.callback_query(F.data == "rules:badges")
async def rules_badges_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_badges(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:seasons")
async def rules_seasons_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_seasons(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:weapons")
async def rules_weapons_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_weapons(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:enemies")
async def rules_enemies_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_enemies(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:magic")
async def rules_magic_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_magic(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:characters")
async def rules_characters_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_characters(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:upgrades")
async def rules_upgrades_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_upgrades(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:run_tasks")
async def rules_run_tasks_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_run_tasks(), reply_markup=rules_back_kb())


@router.callback_query(F.data == "rules:balance")
async def rules_balance_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await edit_or_send(callback, _format_balance(), reply_markup=rules_back_kb())
