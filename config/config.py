"""
Configuration management for GuessWithEmojiBot
Handles environment variables and bot settings
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Centralized configuration management"""

    # Bot Settings
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "GuessWithEmojiBot")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

    # MongoDB Settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "emoji_movie_bot")

    # Game Settings
    GAME_TIMEOUT: int = int(os.getenv("GAME_TIMEOUT", "60"))  # seconds
    MAX_HINTS: int = int(os.getenv("MAX_HINTS", "3"))
    POINTS_CORRECT: int = int(os.getenv("POINTS_CORRECT", "10"))
    POINTS_HINT: int = int(os.getenv("POINTS_HINT", "5"))

    # Rate Limiting Settings
    GLOBAL_RATE_LIMIT: int = int(os.getenv("GLOBAL_RATE_LIMIT", "25"))  # messages per second
    GROUP_RATE_LIMIT: int = int(os.getenv("GROUP_RATE_LIMIT", "20"))   # messages per minute per group

    # Logging Settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

    # Heroku Settings
    PORT: int = int(os.getenv("PORT", "8000"))
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"

    # Error Reporting
    ERROR_CHAT_ID: Optional[int] = int(os.getenv("ERROR_CHAT_ID", "0")) if os.getenv("ERROR_CHAT_ID") else None

    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")
        if not cls.OWNER_ID:
            raise ValueError("OWNER_ID is required")
        if not cls.MONGODB_URI:
            raise ValueError("MONGODB_URI is required")
        return True

    @classmethod
    def get_webhook_url(cls) -> Optional[str]:
        """Get webhook URL if webhooks are enabled"""
        if cls.USE_WEBHOOK and cls.WEBHOOK_URL:
            return f"{cls.WEBHOOK_URL}/{cls.BOT_TOKEN}"
        return None
