import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

if __name__ == "__main__" and __package__ is None:
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from bot.config import get_bot_token
from bot.db import init_db
from bot.handlers import (
    admin_router,
    broadcast_router,
    game_router,
    heroes_router,
    leaderboard_router,
    profile_router,
    rules_router,
    share_router,
    start_router,
    stats_router,
    stars_router,
    story_router,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        await init_db()
        bot = Bot(token=get_bot_token(), default=DefaultBotProperties(parse_mode="HTML"))
        dispatcher = Dispatcher()
        dispatcher.include_router(start_router)
        dispatcher.include_router(admin_router)
        dispatcher.include_router(broadcast_router)
        dispatcher.include_router(game_router)
        dispatcher.include_router(heroes_router)
        dispatcher.include_router(leaderboard_router)
        dispatcher.include_router(rules_router)
        dispatcher.include_router(share_router)
        dispatcher.include_router(stats_router)
        dispatcher.include_router(profile_router)
        dispatcher.include_router(stars_router)
        dispatcher.include_router(story_router)
        logger.info("Starting bot polling")
        await dispatcher.start_polling(bot)
    except Exception:
        logger.exception("Bot failed to start")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(main())
