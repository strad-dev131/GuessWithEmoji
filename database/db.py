"""
MongoDB database connection and operations for GuessWithEmojiBot
Handles all database interactions with async operations
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import asyncio

import motor.motor_asyncio
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo import IndexModel, TEXT, ASCENDING, DESCENDING

from config.config import Config
from database.models import User, MoviePuzzle, GameSession, ChatStats, GameStatus, DifficultyLevel

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles MongoDB operations"""

    def __init__(self):
        self.client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
        self.db = None
        self._connected = False

    async def connect(self):
        """Establish connection to MongoDB"""
        try:
            logger.info("Connecting to MongoDB...")
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )

            # Test connection
            await self.client.admin.command('ping')
            self.db = self.client[Config.DATABASE_NAME]

            # Create indexes
            await self._create_indexes()

            self._connected = True
            logger.info(f"Successfully connected to MongoDB database: {Config.DATABASE_NAME}")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")

    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Users collection indexes
            users_indexes = [
                IndexModel("user_id", unique=True),
                IndexModel("username"),
                IndexModel([("score", DESCENDING)]),
                IndexModel("last_active")
            ]
            await self.db.users.create_indexes(users_indexes)

            # Game sessions collection indexes
            sessions_indexes = [
                IndexModel("chat_id"),
                IndexModel([("chat_id", ASCENDING), ("status", ASCENDING)]),
                IndexModel("start_time"),
                IndexModel("winner_id")
            ]
            await self.db.game_sessions.create_indexes(sessions_indexes)

            # Movie puzzles collection indexes
            puzzles_indexes = [
                IndexModel("category"),
                IndexModel("difficulty"),
                IndexModel([("times_used", ASCENDING)]),
                IndexModel([("answer", TEXT)])
            ]
            await self.db.movie_puzzles.create_indexes(puzzles_indexes)

            # Chat stats collection indexes
            chat_indexes = [
                IndexModel("chat_id", unique=True),
                IndexModel([("total_games", DESCENDING)])
            ]
            await self.db.chat_stats.create_indexes(chat_indexes)

            logger.info("Database indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    async def is_connected(self) -> bool:
        """Check if database is connected"""
        return self._connected and self.client is not None

    # User Operations
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            doc = await self.db.users.find_one({"_id": user_id})
            return User.from_dict(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None

    async def create_or_update_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user or update existing"""
        try:
            user_id = user_data["user_id"]
            existing_user = await self.get_user(user_id)

            if existing_user:
                # Update existing user
                update_data = {
                    "username": user_data.get("username"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "last_active": datetime.now(timezone.utc)
                }
                await self.db.users.update_one(
                    {"_id": user_id},
                    {"$set": {k: v for k, v in update_data.items() if v is not None}}
                )
                # Return updated user
                return await self.get_user(user_id)
            else:
                # Create new user
                new_user = User(
                    user_id=user_id,
                    username=user_data.get("username"),
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name")
                )
                await self.db.users.insert_one(new_user.to_dict())
                return new_user

        except Exception as e:
            logger.error(f"Error creating/updating user {user_data.get('user_id')}: {e}")
            raise

    async def update_user_stats(self, user_id: int, stats_update: Dict[str, Any]):
        """Update user statistics"""
        try:
            await self.db.users.update_one(
                {"_id": user_id},
                {
                    "$inc": stats_update,
                    "$set": {"last_active": datetime.now(timezone.utc)}
                }
            )
        except Exception as e:
            logger.error(f"Error updating user stats {user_id}: {e}")

    async def get_leaderboard(self, limit: int = 10, chat_id: Optional[int] = None) -> List[User]:
        """Get leaderboard (global or chat-specific)"""
        try:
            # For now, get global leaderboard
            # TODO: Implement chat-specific leaderboard logic
            cursor = self.db.users.find(
                {"is_banned": {"$ne": True}}
            ).sort("score", DESCENDING).limit(limit)

            users = []
            async for doc in cursor:
                users.append(User.from_dict(doc))
            return users

        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

    # Movie Puzzle Operations
    async def get_random_puzzle(self, category: Optional[str] = None, 
                              difficulty: Optional[DifficultyLevel] = None,
                              exclude_recent: List[str] = None) -> Optional[MoviePuzzle]:
        """Get random movie puzzle with optional filters"""
        try:
            query = {}
            if category:
                query["category"] = category
            if difficulty:
                query["difficulty"] = difficulty.value
            if exclude_recent:
                query["_id"] = {"$nin": exclude_recent}

            # Get puzzle with lowest usage count (fair rotation)
            pipeline = [
                {"$match": query},
                {"$sort": {"times_used": 1}},
                {"$sample": {"size": 1}}
            ]

            cursor = self.db.movie_puzzles.aggregate(pipeline)
            doc = await cursor.to_list(length=1)

            if doc:
                puzzle = MoviePuzzle.from_dict(doc[0])
                # Increment usage count
                await self.db.movie_puzzles.update_one(
                    {"_id": puzzle.id},
                    {"$inc": {"times_used": 1}}
                )
                return puzzle
            return None

        except Exception as e:
            logger.error(f"Error getting random puzzle: {e}")
            return None

    async def mark_puzzle_solved(self, puzzle_id: str):
        """Mark puzzle as solved (increment solve count)"""
        try:
            await self.db.movie_puzzles.update_one(
                {"_id": puzzle_id},
                {"$inc": {"times_solved": 1}}
            )
        except Exception as e:
            logger.error(f"Error marking puzzle solved {puzzle_id}: {e}")

    # Game Session Operations
    async def create_game_session(self, session: GameSession) -> bool:
        """Create new game session"""
        try:
            await self.db.game_sessions.insert_one(session.to_dict())
            return True
        except Exception as e:
            logger.error(f"Error creating game session: {e}")
            return False

    async def get_active_game(self, chat_id: int) -> Optional[GameSession]:
        """Get active game session for chat"""
        try:
            doc = await self.db.game_sessions.find_one({
                "chat_id": chat_id,
                "status": GameStatus.ACTIVE.value
            })
            return GameSession.from_dict(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting active game for chat {chat_id}: {e}")
            return None

    async def update_game_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update game session"""
        try:
            await self.db.game_sessions.update_one(
                {"_id": session_id},
                {"$set": updates}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating game session {session_id}: {e}")
            return False

    async def add_game_guess(self, session_id: str, user_id: int, guess: str) -> bool:
        """Add guess to game session"""
        try:
            guess_data = {
                "user_id": user_id,
                "guess": guess,
                "timestamp": datetime.now(timezone.utc)
            }
            await self.db.game_sessions.update_one(
                {"_id": session_id},
                {"$push": {"guesses": guess_data}}
            )
            return True
        except Exception as e:
            logger.error(f"Error adding guess to session {session_id}: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()
