from .admin import router as admin_router
from .broadcast import router as broadcast_router
from .game import router as game_router
from .leaderboard import router as leaderboard_router
from .rules import router as rules_router
from .share import router as share_router
from .start import router as start_router
from .stats import router as stats_router
from .profile import router as profile_router

__all__ = [
    "start_router",
    "game_router",
    "leaderboard_router",
    "rules_router",
    "share_router",
    "stats_router",
    "broadcast_router",
    "admin_router",
    "profile_router",
]
