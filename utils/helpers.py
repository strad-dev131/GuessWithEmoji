"""
Utility functions and decorators for GuessWithEmojiBot
Common helper functions used throughout the application
"""

import asyncio
import functools
import logging
import time
from typing import Callable, Any, Optional, List, Dict
import re
import unicodedata
from datetime import datetime, timezone

from telegram import Update, User as TelegramUser
from telegram.ext import ContextTypes

from config.config import Config

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to restrict command to bot owner only"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else 0
        if user_id != Config.OWNER_ID:
            await update.effective_message.reply_text(
                "❌ This command is restricted to the bot owner only."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def rate_limit(calls_per_minute: int = 30):
    """Decorator to rate limit function calls per user"""
    def decorator(func):
        call_times = {}

        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id if update.effective_user else 0
            now = time.time()

            # Clean old entries
            call_times[user_id] = [t for t in call_times.get(user_id, []) if now - t < 60]

            # Check rate limit
            if len(call_times.get(user_id, [])) >= calls_per_minute:
                await update.effective_message.reply_text(
                    f"⚠️ Rate limit exceeded. Please wait before using this command again."
                )
                return

            # Record call time
            call_times.setdefault(user_id, []).append(now)

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def log_command_usage(func):
    """Decorator to log command usage"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        command = update.message.text.split()[0] if update.message else "unknown"

        logger.info(
            f"Command used: {command} by user {user.id} ({user.username or user.first_name}) "
            f"in chat {chat.id} ({chat.title if chat.title else 'private'})"
        )

        return await func(update, context, *args, **kwargs)
    return wrapper

async def safe_send_message(bot, chat_id: int, text: str, **kwargs) -> bool:
    """Safely send message with error handling"""
    try:
        await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False

def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())

    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)

    # Remove common punctuation and articles for movie matching
    text = re.sub(r"[.,!?;:\"\'\-\(\)\[\]{}]", "", text) 
    text = re.sub(r'\b(the|a|an)\b\s*', '', text)

    return text.strip()

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two texts (0.0 to 1.0)"""
    text1 = normalize_text(text1)
    text2 = normalize_text(text2)

    if not text1 or not text2:
        return 0.0

    if text1 == text2:
        return 1.0

    # Simple Jaccard similarity
    words1 = set(text1.split())
    words2 = set(text2.split())

    if not words1 or not words2:
        return 0.0

    intersection = words1.intersection(words2)
    union = words1.union(words2)

    return len(intersection) / len(union)

def is_close_match(guess: str, answer: str, threshold: float = 0.8) -> bool:
    """Check if guess is close enough to answer"""
    return calculate_similarity(guess, answer) >= threshold

def extract_user_info(telegram_user: TelegramUser) -> Dict[str, Any]:
    """Extract user information from Telegram user object"""
    return {
        "user_id": telegram_user.id,
        "username": telegram_user.username,
        "first_name": telegram_user.first_name,
        "last_name": telegram_user.last_name
    }

def format_leaderboard(users: List[Any], title: str = "🏆 Leaderboard") -> str:
    """Format leaderboard for display"""
    if not users:
        return f"{title}\n\nNo players yet! Be the first to play! 🎬"

    text = f"{title}\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(users[:10]):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = user.username or user.first_name or "Anonymous"
        text += f"{medal} {name}: {user.score} points ({user.games_won}/{user.games_played} wins)\n"

    return text

def format_duration(seconds: int) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds//60}m {seconds%60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def get_difficulty_emoji(difficulty: str) -> str:
    """Get emoji for difficulty level"""
    emoji_map = {
        "easy": "🟢",
        "medium": "🟡", 
        "hard": "🔴"
    }
    return emoji_map.get(difficulty.lower(), "⚪")

def get_category_emoji(category: str) -> str:
    """Get emoji for movie category"""
    emoji_map = {
        "hollywood": "🇺🇸",
        "bollywood": "🇮🇳",
        "tollywood": "🎭",
        "anime": "🇯🇵",
        "classic": "🎞️"
    }
    return emoji_map.get(category.lower(), "🎬")

async def cleanup_old_data(db_manager, days: int = 30):
    """Cleanup old game sessions and expired data"""
    try:
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        # Remove old completed game sessions
        result = await db_manager.db.game_sessions.delete_many({
            "status": {"$in": ["completed", "timeout"]},
            "end_time": {"$lt": cutoff_date}
        })

        logger.info(f"Cleaned up {result.deleted_count} old game sessions")

    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = r'\`*_{}[]()#+\-.!|'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def truncate_text(text: str, max_length: int = 4096) -> str:
    """Truncate text to fit Telegram message limits"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
