#!/usr/bin/env python3
"""
GuessWithEmojiBot - Ultimate Telegram Emoji Movie Guessing Bot
A comprehensive bot for 24/7 emoji-based movie guessing games
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.bot import GuessWithEmojiBot
from config.config import Config
from utils.logger import setup_logging

async def main():
    """Main entry point for the bot"""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)

        logger.info("Starting GuessWithEmojiBot...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")

        # Initialize and start the bot
        bot = GuessWithEmojiBot()
        await bot.start()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
