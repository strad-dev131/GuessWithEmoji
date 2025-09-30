"""
Game session management for GuessWithEmojiBot
Handles individual game instances and state management
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from database.db import DatabaseManager
from database.models import GameSession, GameStatus, DifficultyLevel

logger = logging.getLogger(__name__)

class GameSessionManager:
    """Manages individual game sessions"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.active_sessions: Dict[int, str] = {}  # chat_id -> session_id

    async def create_session(self, chat_id: int, puzzle_id: str, 
                           emojis: str, answer: str, category: str,
                           difficulty: DifficultyLevel) -> Optional[GameSession]:
        """Create new game session"""
        try:
            session_id = str(uuid.uuid4())

            session = GameSession(
                id=session_id,
                chat_id=chat_id,
                puzzle_id=puzzle_id,
                emojis=emojis,
                answer=answer,
                category=category,
                difficulty=difficulty,
                status=GameStatus.ACTIVE,
                start_time=datetime.now(timezone.utc)
            )

            # Save to database
            success = await self.db.create_game_session(session)
            if success:
                self.active_sessions[chat_id] = session_id
                return session

            return None

        except Exception as e:
            logger.error(f"Error creating game session: {e}")
            return None

    async def get_active_session(self, chat_id: int) -> Optional[GameSession]:
        """Get active session for chat"""
        try:
            session_id = self.active_sessions.get(chat_id)
            if not session_id:
                return None

            # Get from database
            doc = await self.db.db.game_sessions.find_one({"_id": session_id})
            if doc:
                return GameSession.from_dict(doc)

            return None

        except Exception as e:
            logger.error(f"Error getting active session: {e}")
            return None

    async def end_session(self, chat_id: int, winner_id: Optional[int] = None) -> bool:
        """End game session"""
        try:
            session_id = self.active_sessions.get(chat_id)
            if not session_id:
                return False

            updates = {
                "status": GameStatus.COMPLETED.value,
                "end_time": datetime.now(timezone.utc)
            }

            if winner_id:
                updates["winner_id"] = winner_id

            success = await self.db.update_game_session(session_id, updates)

            if success and chat_id in self.active_sessions:
                del self.active_sessions[chat_id]

            return success

        except Exception as e:
            logger.error(f"Error ending session: {e}")
            return False
