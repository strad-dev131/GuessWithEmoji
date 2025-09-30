"""
Game logic implementation for emoji movie guessing
Handles game sessions, puzzles, and scoring
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config.config import Config
from database.db import DatabaseManager
from database.models import GameSession, MoviePuzzle, User, GameStatus, DifficultyLevel
from utils.helpers import (
    normalize_text, is_close_match, format_duration, 
    get_difficulty_emoji, get_category_emoji
)

logger = logging.getLogger(__name__)

class GameManager:
    """Manages active game sessions and game logic"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.active_games: Dict[int, GameSession] = {}  # chat_id -> GameSession
        self.recent_puzzles: Dict[int, List[str]] = {}  # chat_id -> [puzzle_ids]
        self.game_timers: Dict[int, asyncio.Task] = {}  # chat_id -> timer_task

        logger.info("GameManager initialized")

    async def start_new_game(self, chat_id: int, category: Optional[str] = None, 
                           difficulty: Optional[str] = None) -> Tuple[bool, str, Optional[GameSession]]:
        """Start a new game session"""
        try:
            # Check if game already active
            if await self.is_game_active(chat_id):
                return False, "🎮 A game is already active in this chat! Use /guess to participate.", None

            # Convert difficulty string to enum
            diff_level = None
            if difficulty:
                try:
                    diff_level = DifficultyLevel(difficulty.lower())
                except ValueError:
                    pass

            # Get recent puzzles to avoid repetition
            recent = self.recent_puzzles.get(chat_id, [])

            # Get random puzzle
            puzzle = await self.db.get_random_puzzle(
                category=category,
                difficulty=diff_level,
                exclude_recent=recent[-100:]  # Avoid last 100 puzzles
            )

            if not puzzle:
                return False, "😔 No puzzles available for the specified criteria. Try a different category or difficulty.", None

            # Create game session
            session_id = str(uuid.uuid4())
            session = GameSession(
                id=session_id,
                chat_id=chat_id,
                puzzle_id=puzzle.id,
                emojis=puzzle.emojis,
                answer=puzzle.answer,
                category=puzzle.category,
                difficulty=puzzle.difficulty,
                status=GameStatus.ACTIVE,
                start_time=datetime.now(timezone.utc)
            )

            # Save to database
            await self.db.create_game_session(session)

            # Store in memory
            self.active_games[chat_id] = session

            # Update recent puzzles
            if chat_id not in self.recent_puzzles:
                self.recent_puzzles[chat_id] = []
            self.recent_puzzles[chat_id].append(puzzle.id)

            # Start game timer
            await self._start_game_timer(chat_id)

            # Create game message
            game_msg = self._format_game_message(session)

            logger.info(f"New game started in chat {chat_id}: {puzzle.answer}")
            return True, game_msg, session

        except Exception as e:
            logger.error(f"Error starting new game in chat {chat_id}: {e}")
            return False, "❌ Failed to start game. Please try again.", None

    async def process_guess(self, update: Update, context: ContextTypes.DEFAULT_TYPE, guess: str) -> Tuple[bool, str]:
        """Process a player's guess"""
        try:
            chat_id = update.effective_chat.id
            user = update.effective_user

            # Check if game is active
            session = self.active_games.get(chat_id)
            if not session or session.status != GameStatus.ACTIVE:
                return False, "🤔 No active game in this chat. Use /gen to start a new game!"

            # Add user to participants
            if user.id not in session.participants:
                session.participants.append(user.id)

            # Record the guess
            await self.db.add_game_guess(session.id, user.id, guess)

            # Check if guess is correct
            if is_close_match(guess, session.answer, threshold=0.8):
                return await self._handle_correct_guess(session, user)
            else:
                # Check for close match (hint)
                similarity = self._calculate_similarity(guess, session.answer)
                if similarity > 0.5:
                    return False, f"🔥 Getting warmer! Keep trying, {user.first_name}!"
                else:
                    responses = [
                        f"❌ Not quite right, {user.first_name}!",
                        f"🤔 Nope, try again {user.first_name}!",
                        f"🎯 Keep guessing, {user.first_name}!"
                    ]
                    return False, random.choice(responses)

        except Exception as e:
            logger.error(f"Error processing guess in chat {chat_id}: {e}")
            return False, "❌ Error processing your guess. Please try again."

    async def _handle_correct_guess(self, session: GameSession, user) -> Tuple[bool, str]:
        """Handle a correct guess"""
        try:
            # Update session
            session.status = GameStatus.COMPLETED
            session.end_time = datetime.now(timezone.utc)
            session.winner_id = user.id
            session.winner_username = user.username or user.first_name

            # Calculate points
            base_points = Config.POINTS_CORRECT
            difficulty_multiplier = {
                DifficultyLevel.EASY: 1.0,
                DifficultyLevel.MEDIUM: 1.5,
                DifficultyLevel.HARD: 2.0
            }
            points = int(base_points * difficulty_multiplier[session.difficulty])

            # Bonus for speed (if solved in under 30 seconds)
            duration = (session.end_time - session.start_time).total_seconds()
            if duration < 30:
                points = int(points * 1.5)
                speed_bonus = True
            else:
                speed_bonus = False

            # Update database
            await self.db.update_game_session(session.id, {
                "status": session.status.value,
                "end_time": session.end_time,
                "winner_id": session.winner_id,
                "winner_username": session.winner_username
            })

            # Update user stats
            await self.db.update_user_stats(user.id, {
                "score": points,
                "games_won": 1,
                "games_played": 1,
                "correct_guesses": 1
            })

            # Update puzzle stats
            await self.db.mark_puzzle_solved(session.puzzle_id)

            # Remove from active games
            chat_id = session.chat_id
            if chat_id in self.active_games:
                del self.active_games[chat_id]

            # Cancel timer
            if chat_id in self.game_timers:
                self.game_timers[chat_id].cancel()
                del self.game_timers[chat_id]

            # Create victory message
            victory_msg = self._format_victory_message(session, points, duration, speed_bonus)

            logger.info(f"Game won in chat {chat_id} by user {user.id}: {session.answer}")
            return True, victory_msg

        except Exception as e:
            logger.error(f"Error handling correct guess: {e}")
            return True, f"🎉 Correct! The answer was **{session.answer}**!"

    async def get_hint(self, chat_id: int) -> Tuple[bool, str]:
        """Get a hint for the current game"""
        try:
            session = self.active_games.get(chat_id)
            if not session or session.status != GameStatus.ACTIVE:
                return False, "🤔 No active game in this chat."

            # Get puzzle from database to get hints
            puzzle = await self.db.get_puzzle_by_id(session.puzzle_id)
            if not puzzle or not puzzle.hints:
                return False, "💡 No hints available for this puzzle."

            # Check hint limit
            if session.hints_given >= Config.MAX_HINTS:
                return False, f"🚫 Maximum {Config.MAX_HINTS} hints already given!"

            # Give next hint
            hint = puzzle.hints[session.hints_given]
            session.hints_given += 1

            # Update database
            await self.db.update_game_session(session.id, {
                "hints_given": session.hints_given
            })

            hint_msg = f"💡 **Hint {session.hints_given}/{len(puzzle.hints)}:** {hint}"
            return True, hint_msg

        except Exception as e:
            logger.error(f"Error getting hint for chat {chat_id}: {e}")
            return False, "❌ Error getting hint."

    async def end_game(self, chat_id: int, reason: str = "manual") -> Tuple[bool, str]:
        """End the current game"""
        try:
            session = self.active_games.get(chat_id)
            if not session:
                return False, "🤔 No active game in this chat."

            # Update session
            session.status = GameStatus.TIMEOUT if reason == "timeout" else GameStatus.COMPLETED
            session.end_time = datetime.now(timezone.utc)

            # Update database
            await self.db.update_game_session(session.id, {
                "status": session.status.value,
                "end_time": session.end_time
            })

            # Update participant stats (games played)
            for user_id in session.participants:
                await self.db.update_user_stats(user_id, {"games_played": 1})

            # Remove from active games
            if chat_id in self.active_games:
                del self.active_games[chat_id]

            # Cancel timer
            if chat_id in self.game_timers:
                self.game_timers[chat_id].cancel()
                del self.game_timers[chat_id]

            end_msg = f"⏰ Game ended! The answer was **{session.answer}**\n\n"
            end_msg += f"🎬 {session.emojis}\n"
            end_msg += f"{get_category_emoji(session.category)} {session.category.title()} | "
            end_msg += f"{get_difficulty_emoji(session.difficulty.value)} {session.difficulty.value.title()}"

            return True, end_msg

        except Exception as e:
            logger.error(f"Error ending game in chat {chat_id}: {e}")
            return False, "❌ Error ending game."

    async def is_game_active(self, chat_id: int) -> bool:
        """Check if a game is active in the chat"""
        return chat_id in self.active_games and self.active_games[chat_id].status == GameStatus.ACTIVE

    def _format_game_message(self, session: GameSession) -> str:
        """Format the game start message"""
        msg = f"🎬 **New Movie Puzzle!**\n\n"
        msg += f"🎯 **Guess the movie:** {session.emojis}\n\n"
        msg += f"{get_category_emoji(session.category)} **Category:** {session.category.title()}\n"
        msg += f"{get_difficulty_emoji(session.difficulty.value)} **Difficulty:** {session.difficulty.value.title()}\n"
        msg += f"⏰ **Time Limit:** {Config.GAME_TIMEOUT} seconds\n\n"
        msg += f"💡 Use `/hint` to get a clue!\n"
        msg += f"🎮 Use `/guess <your answer>` to participate!"
        return msg

    def _format_victory_message(self, session: GameSession, points: int, duration: float, speed_bonus: bool) -> str:
        """Format the victory message"""
        duration_str = format_duration(int(duration))

        msg = f"🎉 **WINNER!** 🎉\n\n"
        msg += f"🏆 **{session.winner_username}** got it right!\n"
        msg += f"🎬 **Answer:** {session.answer}\n"
        msg += f"⚡ **Time:** {duration_str}\n"
        msg += f"⭐ **Points Earned:** {points}"

        if speed_bonus:
            msg += f" (🚀 Speed Bonus!)"

        msg += f"\n\n{get_category_emoji(session.category)} {session.category.title()} | "
        msg += f"{get_difficulty_emoji(session.difficulty.value)} {session.difficulty.value.title()}"

        return msg

    def _calculate_similarity(self, guess: str, answer: str) -> float:
        """Calculate similarity between guess and answer"""
        # Simple implementation - could be enhanced
        guess_norm = normalize_text(guess)
        answer_norm = normalize_text(answer)

        if guess_norm == answer_norm:
            return 1.0

        # Check if guess is substring of answer or vice versa
        if guess_norm in answer_norm or answer_norm in guess_norm:
            return 0.8

        # Word overlap
        guess_words = set(guess_norm.split())
        answer_words = set(answer_norm.split())

        if not guess_words or not answer_words:
            return 0.0

        overlap = len(guess_words.intersection(answer_words))
        total = len(guess_words.union(answer_words))

        return overlap / total if total > 0 else 0.0

    async def _start_game_timer(self, chat_id: int):
        """Start game timeout timer"""
        async def timeout_handler():
            try:
                await asyncio.sleep(Config.GAME_TIMEOUT)
                await self.end_game(chat_id, "timeout")
            except asyncio.CancelledError:
                pass  # Timer was cancelled (game ended normally)
            except Exception as e:
                logger.error(f"Error in game timer for chat {chat_id}: {e}")

        if chat_id in self.game_timers:
            self.game_timers[chat_id].cancel()

        self.game_timers[chat_id] = asyncio.create_task(timeout_handler())
