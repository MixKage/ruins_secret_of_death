from .game import router as game_router
from .leaderboard import router as leaderboard_router
from .rules import router as rules_router
from .share import router as share_router
from .start import router as start_router
from .stats import router as stats_router

__all__ = ["start_router", "game_router", "leaderboard_router", "rules_router", "share_router", "stats_router"]
