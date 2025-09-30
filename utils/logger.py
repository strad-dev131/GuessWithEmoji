"""
Centralized logging system for GuessWithEmojiBot
Provides comprehensive logging with file rotation and error tracking
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from config.config import Config

class TelegramLogHandler(logging.Handler):
    """Custom log handler that sends critical errors to Telegram"""

    def __init__(self, bot_instance=None, error_chat_id: Optional[int] = None):
        super().__init__()
        self.bot_instance = bot_instance
        self.error_chat_id = error_chat_id or Config.ERROR_CHAT_ID
        self.setLevel(logging.ERROR)

    def emit(self, record):
        """Send log record to Telegram chat"""
        try:
            if self.bot_instance and self.error_chat_id and record.levelno >= logging.ERROR:
                log_entry = self.format(record)
                # Truncate if too long for Telegram
                if len(log_entry) > 4000:
                    log_entry = log_entry[:4000] + "\n... (truncated)"

                # Format for Telegram
                message = f"🚨 *Bot Error Alert*\n\n```\n{log_entry}\n```"

                # Send asynchronously (don't block the main thread)
                import asyncio
                if asyncio.get_event_loop().is_running():
                    asyncio.create_task(self._send_message(message))
        except Exception:
            # Don't let logging errors crash the bot
            pass

    async def _send_message(self, message: str):
        """Send message to Telegram"""
        try:
            await self.bot_instance.send_message(
                chat_id=self.error_chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception:
            pass

class ColoredFormatter(logging.Formatter):
    """Colored logging formatter for console output"""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logging(bot_instance=None) -> logging.Logger:
    """Setup comprehensive logging system"""

    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / Config.LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Error file handler
    error_handler = logging.FileHandler(
        filename=log_dir / "error.log",
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Telegram error handler
    if bot_instance and Config.ERROR_CHAT_ID:
        telegram_handler = TelegramLogHandler(bot_instance, Config.ERROR_CHAT_ID)
        telegram_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s\n%(message)s',
            datefmt='%H:%M:%S'
        )
        telegram_handler.setFormatter(telegram_formatter)
        root_logger.addHandler(telegram_handler)

    # Initialize Sentry for error tracking (optional)
    sentry_dsn = os.getenv("SENTRY_DSN")
    if sentry_dsn:
        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR
        )
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[sentry_logging],
            traces_sample_rate=0.1,
            environment=os.getenv("ENVIRONMENT", "production")
        )

    # Set specific loggers to appropriate levels
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.INFO)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging system initialized")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    logger.info(f"Log file: {log_dir / Config.LOG_FILE}")

    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    return logging.getLogger(name)
