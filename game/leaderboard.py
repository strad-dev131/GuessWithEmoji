"""
Leaderboard and scoring system for GuessWithEmojiBot
Handles user rankings and score calculations
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from database.db import DatabaseManager
from database.models import User

logger = logging.getLogger(__name__)

class LeaderboardManager:
    """Manages leaderboards and user rankings"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_global_leaderboard(self, limit: int = 10) -> List[User]:
        """Get global leaderboard"""
        try:
            cursor = self.db.db.users.find(
                {"is_banned": {"$ne": True}}
            ).sort("score", -1).limit(limit)

            users = []
            async for doc in cursor:
                users.append(User.from_dict(doc))

            return users

        except Exception as e:
            logger.error(f"Error getting global leaderboard: {e}")
            return []

    async def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get user's global rank"""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return None

            # Count users with higher scores
            higher_count = await self.db.db.users.count_documents({
                "score": {"$gt": user.score},
                "is_banned": {"$ne": True}
            })

            return higher_count + 1

        except Exception as e:
            logger.error(f"Error getting user rank for {user_id}: {e}")
            return None

    async def get_top_players_by_category(self, category: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top players for specific category"""
        # This would require tracking category-specific stats
        # For now, return global leaderboard
        return await self.get_global_leaderboard(limit)
