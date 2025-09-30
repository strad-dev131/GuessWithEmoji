"""
Core bot implementation for GuessWithEmojiBot
Handles initialization, error handling, and main bot lifecycle
"""

import asyncio
import logging
from typing import Optional
import signal
import sys

from telegram import Update, Bot
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, 
    MessageHandler, CallbackQueryHandler, filters,
    ContextTypes
)
from telegram.constants import ParseMode
from telegram.error import NetworkError, TimedOut, BadRequest

from config.config import Config
from database.db import db_manager
from utils.logger import setup_logging, get_logger
from utils.helpers import safe_send_message
from bot.commands import setup_command_handlers
from bot.game_logic import GameManager
from utils.movie_puzzles import initialize_puzzle_database

logger = get_logger(__name__)

class GuessWithEmojiBot:
    """Main bot application class"""

    def __init__(self):
        """Initialize the bot"""
        self.application: Optional[Application] = None
        self.game_manager: Optional[GameManager] = None
        self._running = False

        # Validate configuration
        Config.validate()

        logger.info("GuessWithEmojiBot initialized")

    async def start(self):
        """Start the bot"""
        try:
            # Setup logging
            setup_logging()

            # Connect to database
            await db_manager.connect()

            # Initialize puzzle database (load from JSON if empty)
            await self._initialize_puzzles()

            # Build application
            builder = ApplicationBuilder().token(Config.BOT_TOKEN)

            # Add rate limiter if available
            try:
                from telegram.ext import AIORateLimiter
                rate_limiter = AIORateLimiter(
                    overall_max_rate=Config.GLOBAL_RATE_LIMIT,
                    group_max_rate=Config.GROUP_RATE_LIMIT
                )
                builder.rate_limiter(rate_limiter)
                logger.info("Rate limiter enabled")
            except ImportError:
                logger.warning("Rate limiter not available - install with pip install 'python-telegram-bot[rate-limiter]'")

            self.application = builder.build()

            # Initialize game manager
            self.game_manager = GameManager(db_manager)

            # Setup handlers
            self._setup_handlers()

            # Setup error handling
            self.application.add_error_handler(self._error_handler)

            # Start the bot
            if Config.USE_WEBHOOK:
                await self._start_webhook()
            else:
                await self._start_polling()

        except Exception as e:
            logger.error(f"Failed to start bot: {e}", exc_info=True)
            await self.shutdown()
            raise

    async def _initialize_puzzles(self):
        """Initialize puzzle database if empty"""
        try:
            puzzle_count = await db_manager.count_puzzles()
            logger.info(f"Found {puzzle_count} puzzles in database")

            if puzzle_count == 0:
                logger.info("No puzzles found, initializing from JSON file...")
                success = await initialize_puzzle_database(db_manager)
                if success:
                    new_count = await db_manager.count_puzzles()
                    logger.info(f"Successfully loaded {new_count} puzzles into database")
                else:
                    logger.error("Failed to initialize puzzle database")
            else:
                logger.info(f"Puzzle database already initialized with {puzzle_count} puzzles")

        except Exception as e:
            logger.error(f"Error initializing puzzles: {e}")
            # Create some default puzzles as fallback
            await self._create_fallback_puzzles()

    async def _create_fallback_puzzles(self):
        """Create some basic puzzles as fallback"""
        try:
            logger.info("Creating fallback puzzles...")

            fallback_puzzles = [
                {
                    "_id": "hollywood_1",
                    "emojis": "🚢💔🧊",
                    "answer": "Titanic",
                    "category": "hollywood",
                    "difficulty": "easy",
                    "hints": ["1912", "Leonardo DiCaprio", "Unsinkable ship"],
                    "times_used": 0,
                    "times_solved": 0
                },
                {
                    "_id": "hollywood_2",
                    "emojis": "🦁👑",
                    "answer": "The Lion King",
                    "category": "hollywood",
                    "difficulty": "easy",
                    "hints": ["Disney", "Simba", "Hakuna Matata"],
                    "times_used": 0,
                    "times_solved": 0
                },
                {
                    "_id": "hollywood_3",
                    "emojis": "🕷️👦🌃",
                    "answer": "Spider-Man",
                    "category": "hollywood",  
                    "difficulty": "easy",
                    "hints": ["Marvel", "Peter Parker", "Web slinger"],
                    "times_used": 0,
                    "times_solved": 0
                },
                {
                    "_id": "bollywood_1",
                    "emojis": "🎓📚❤️",
                    "answer": "3 Idiots",
                    "category": "bollywood",
                    "difficulty": "easy",
                    "hints": ["Engineering", "Aamir Khan", "All is well"],
                    "times_used": 0,
                    "times_solved": 0
                },
                {
                    "_id": "tollywood_1",
                    "emojis": "🗡️👑🏰",
                    "answer": "Baahubali",
                    "category": "tollywood",
                    "difficulty": "medium",
                    "hints": ["Epic movie", "Prabhas", "Why Kattappa killed"],
                    "times_used": 0,
                    "times_solved": 0
                }
            ]

            for puzzle in fallback_puzzles:
                try:
                    await db_manager.db.movie_puzzles.insert_one(puzzle)
                except Exception as e:
                    logger.error(f"Error inserting fallback puzzle: {e}")

            count = await db_manager.count_puzzles()
            logger.info(f"Created {count} fallback puzzles")

        except Exception as e:
            logger.error(f"Error creating fallback puzzles: {e}")

    async def _start_polling(self):
        """Start bot with polling"""
        logger.info("Starting bot with polling...")

        # Setup signal handlers
        self._setup_signal_handlers()

        try:
            await self.application.initialize()
            await self.application.start()

            # Start polling
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            self._running = True
            logger.info("Bot started successfully with polling")

            # Send startup notification
            if Config.ERROR_CHAT_ID:
                puzzle_count = await db_manager.count_puzzles()
                await safe_send_message(
                    self.application.bot,
                    Config.ERROR_CHAT_ID,
                    f"🤖 *GuessWithEmojiBot Started*\n\n"
                    f"✅ Status: Online\n"
                    f"🔄 Mode: Polling\n"
                    f"📊 Database: Connected\n"
                    f"🎬 Puzzles: {puzzle_count} loaded\n"
                    f"⚡ Ready to serve 1000+ groups!",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Keep running until stopped
            while self._running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in polling mode: {e}")
            raise
        finally:
            await self.shutdown()

    async def _start_webhook(self):
        """Start bot with webhook (for Heroku deployment)"""
        webhook_url = Config.get_webhook_url()
        if not webhook_url:
            raise ValueError("Webhook URL not configured")

        logger.info(f"Starting bot with webhook: {webhook_url}")

        try:
            await self.application.initialize()
            await self.application.start()

            # Set webhook
            await self.application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True
            )

            # Start webhook server
            await self.application.updater.start_webhook(
                listen="0.0.0.0",
                port=Config.PORT,
                url_path=Config.BOT_TOKEN,
                webhook_url=webhook_url
            )

            self._running = True
            logger.info("Bot started successfully with webhook")

            # Send startup notification
            if Config.ERROR_CHAT_ID:
                puzzle_count = await db_manager.count_puzzles()
                await safe_send_message(
                    self.application.bot,
                    Config.ERROR_CHAT_ID,
                    f"🤖 *GuessWithEmojiBot Started*\n\n"
                    f"✅ Status: Online\n"
                    f"🔄 Mode: Webhook\n"
                    f"🌐 URL: {webhook_url}\n"
                    f"📊 Database: Connected\n"
                    f"🎬 Puzzles: {puzzle_count} loaded\n"
                    f"⚡ Ready to serve 1000+ groups!",
                    parse_mode=ParseMode.MARKDOWN
                )

            # Keep running
            while self._running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in webhook mode: {e}")
            raise
        finally:
            await self.shutdown()

    def _setup_handlers(self):
        """Setup all command and message handlers"""
        # Setup command handlers from commands module
        setup_command_handlers(self.application, self.game_manager)

        logger.info("Command handlers setup complete")

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self._running = False
            # Create task for async shutdown
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Global error handler"""
        try:
            # Log the error
            logger.error(f"Exception while handling update {update}: {context.error}", exc_info=context.error)

            # Don't send error messages for specific errors
            if isinstance(context.error, (NetworkError, TimedOut)):
                return

            # Send error message to user if possible
            if isinstance(update, Update) and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "🚫 Sorry, something went wrong. The error has been logged and will be fixed soon!",
                        reply_markup=None
                    )
                except BadRequest:
                    pass  # Message might be too old or chat deleted

            # Send detailed error to admin
            if Config.ERROR_CHAT_ID:
                error_msg = (
                    f"🚨 *Bot Error*\n\n"
                    f"**Error:** `{str(context.error)}`\n"
                    f"**Update:** `{str(update)[:500]}...`\n"
                    f"**User:** {update.effective_user.id if update and update.effective_user else 'Unknown'}\n"
                    f"**Chat:** {update.effective_chat.id if update and update.effective_chat else 'Unknown'}"
                )
                await safe_send_message(
                    context.bot,
                    Config.ERROR_CHAT_ID,
                    error_msg[:4000],  # Truncate if too long
                    parse_mode=ParseMode.MARKDOWN
                )

        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    async def shutdown(self):
        """Gracefully shutdown the bot"""
        if not self._running:
            return

        logger.info("Shutting down bot...")
        self._running = False

        try:
            if self.application:
                if Config.ERROR_CHAT_ID:
                    await safe_send_message(
                        self.application.bot,
                        Config.ERROR_CHAT_ID,
                        "🤖 *GuessWithEmojiBot Shutdown*\n\n"
                        "⏹️ Bot is going offline for maintenance.\n"
                        "Will be back online shortly!",
                        parse_mode=ParseMode.MARKDOWN
                    )

                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()

            # Disconnect from database
            await db_manager.disconnect()

            logger.info("Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
