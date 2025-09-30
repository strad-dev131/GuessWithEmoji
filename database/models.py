"""
MongoDB data models for GuessWithEmojiBot
Defines schemas for users, games, and leaderboards
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class GameStatus(Enum):
    """Game status enumeration"""
    WAITING = "waiting"
    ACTIVE = "active" 
    COMPLETED = "completed"
    TIMEOUT = "timeout"

class DifficultyLevel(Enum):
    """Difficulty level enumeration"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

@dataclass
class User:
    """User data model"""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    score: int = 0
    games_played: int = 0
    games_won: int = 0
    correct_guesses: int = 0
    hints_used: int = 0
    favorite_category: Optional[str] = None
    join_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_banned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "_id": self.user_id,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "score": self.score,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "correct_guesses": self.correct_guesses,
            "hints_used": self.hints_used,
            "favorite_category": self.favorite_category,
            "join_date": self.join_date,
            "last_active": self.last_active,
            "is_banned": self.is_banned
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create User from dictionary"""
        return cls(
            user_id=data["user_id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            score=data.get("score", 0),
            games_played=data.get("games_played", 0),
            games_won=data.get("games_won", 0),
            correct_guesses=data.get("correct_guesses", 0),
            hints_used=data.get("hints_used", 0),
            favorite_category=data.get("favorite_category"),
            join_date=data.get("join_date", datetime.now(timezone.utc)),
            last_active=data.get("last_active", datetime.now(timezone.utc)),
            is_banned=data.get("is_banned", False)
        )

@dataclass
class MoviePuzzle:
    """Movie puzzle data model"""
    id: str
    emojis: str
    answer: str
    category: str
    difficulty: DifficultyLevel
    hints: List[str] = field(default_factory=list)
    times_used: int = 0
    times_solved: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "_id": self.id,
            "emojis": self.emojis,
            "answer": self.answer,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "hints": self.hints,
            "times_used": self.times_used,
            "times_solved": self.times_solved
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoviePuzzle':
        """Create MoviePuzzle from dictionary"""
        return cls(
            id=data["_id"],
            emojis=data["emojis"],
            answer=data["answer"],
            category=data["category"],
            difficulty=DifficultyLevel(data["difficulty"]),
            hints=data.get("hints", []),
            times_used=data.get("times_used", 0),
            times_solved=data.get("times_solved", 0)
        )

@dataclass
class GameSession:
    """Active game session data model"""
    id: str
    chat_id: int
    puzzle_id: str
    emojis: str
    answer: str
    category: str
    difficulty: DifficultyLevel
    status: GameStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    winner_id: Optional[int] = None
    winner_username: Optional[str] = None
    hints_given: int = 0
    participants: List[int] = field(default_factory=list)
    guesses: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "_id": self.id,
            "chat_id": self.chat_id,
            "puzzle_id": self.puzzle_id,
            "emojis": self.emojis,
            "answer": self.answer,
            "category": self.category,
            "difficulty": self.difficulty.value,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "winner_id": self.winner_id,
            "winner_username": self.winner_username,
            "hints_given": self.hints_given,
            "participants": self.participants,
            "guesses": self.guesses
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameSession':
        """Create GameSession from dictionary"""
        return cls(
            id=data["_id"],
            chat_id=data["chat_id"],
            puzzle_id=data["puzzle_id"],
            emojis=data["emojis"],
            answer=data["answer"],
            category=data["category"],
            difficulty=DifficultyLevel(data["difficulty"]),
            status=GameStatus(data["status"]),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            winner_id=data.get("winner_id"),
            winner_username=data.get("winner_username"),
            hints_given=data.get("hints_given", 0),
            participants=data.get("participants", []),
            guesses=data.get("guesses", [])
        )

@dataclass
class ChatStats:
    """Chat statistics data model"""
    chat_id: int
    chat_title: Optional[str] = None
    total_games: int = 0
    active_users: int = 0
    top_player_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_game: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            "_id": self.chat_id,
            "chat_id": self.chat_id,
            "chat_title": self.chat_title,
            "total_games": self.total_games,
            "active_users": self.active_users,
            "top_player_id": self.top_player_id,
            "created_at": self.created_at,
            "last_game": self.last_game
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatStats':
        """Create ChatStats from dictionary"""
        return cls(
            chat_id=data["chat_id"],
            chat_title=data.get("chat_title"),
            total_games=data.get("total_games", 0),
            active_users=data.get("active_users", 0),
            top_player_id=data.get("top_player_id"),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            last_game=data.get("last_game")
        )
