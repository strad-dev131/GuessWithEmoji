"""
Command handlers for GuessWithEmojiBot
Handles all bot commands including /start, /help, /gen, /guess, /broadcast
"""

import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, ChatType

from config.config import Config
from database.db import db_manager
from database.models import DifficultyLevel
from utils.helpers import (
    admin_only, rate_limit, log_command_usage, 
    extract_user_info, format_leaderboard, escape_markdown
)
from bot.game_logic import GameManager

logger = logging.getLogger(__name__)

class CommandHandlers:
    """Collection of command handlers"""

    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager

    @log_command_usage
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            chat = update.effective_chat

            # Create or update user in database
            user_data = extract_user_info(user)
            await db_manager.create_or_update_user(user_data)

            if chat.type == ChatType.PRIVATE:
                # Private chat welcome message
                welcome_msg = f"""🎬 **Welcome to GuessWithEmojiBot!** 🎭

Hello {user.first_name}! I'm your ultimate emoji movie guessing companion!

🎯 **What I Do:**
• Generate movie puzzles using emojis
• Support Hollywood, Bollywood & Tollywood films  
• Track scores and maintain leaderboards
• Provide hints when you're stuck
• Work in groups with 1000+ members seamlessly

🎮 **How to Play:**
1. Add me to your group chat
2. Use `/gen` to start a new movie puzzle
3. Use `/guess <movie name>` to make your guess
4. Use `/hint` if you need a clue
5. Compete with friends for the top spot!

🏆 **Commands:**
/gen - Start a new movie puzzle
/guess - Make your guess
/hint - Get a helpful clue
/leaderboard - View top players
/help - Show detailed help
/stats - View your statistics

🌟 **Features:**
✅ 500+ unique movie puzzles
✅ Multiple difficulty levels
✅ Category-based puzzles
✅ Real-time leaderboards
✅ 24/7 uptime guarantee
✅ Lightning-fast responses

Ready to test your movie knowledge? Add me to a group and use `/gen` to start playing!

🔥 **Challenge your friends and become the ultimate movie guru!**"""

                keyboard = [
                    [InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
                    [InlineKeyboardButton("📊 Leaderboard", callback_data="show_leaderboard")],
                    [InlineKeyboardButton("ℹ️ Help", callback_data="show_help")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    welcome_msg,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                # Group chat welcome
                group_msg = f"""🎬 **GuessWithEmojiBot is now active!** 🎭

Hello everyone! I'm ready to challenge you with emoji movie puzzles!

🎮 **Quick Start:**
• Use `/gen` to start a new puzzle
• Use `/guess <movie name>` to answer
• Use `/leaderboard` to see top players

Let the games begin! 🍿"""

                await update.message.reply_text(group_msg, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")

    @log_command_usage
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = f"""🎬 **GuessWithEmojiBot - Complete Guide** 🎭

🎯 **Game Commands:**
• `/gen [category] [difficulty]` - Start new puzzle
  Examples: `/gen hollywood easy`, `/gen bollywood`, `/gen`
• `/guess <movie name>` - Make your guess
• `/hint` - Get a clue (max {Config.MAX_HINTS} per game)
• `/endgame` - End current game (admins only)

📊 **Stats & Rankings:**
• `/leaderboard` - View top 10 players
• `/stats` - View your personal statistics
• `/groupstats` - View group statistics

🎬 **Categories Available:**
• **Hollywood** 🇺🇸 - International blockbusters
• **Bollywood** 🇮🇳 - Hindi cinema classics
• **Tollywood** 🎭 - Telugu cinema gems

⚡ **Difficulty Levels:**
• 🟢 **Easy** - Popular, well-known movies
• 🟡 **Medium** - Moderate challenge
• 🔴 **Hard** - For true movie buffs

🎮 **How Scoring Works:**
• Correct Answer: {Config.POINTS_CORRECT} points
• Easy: 1x multiplier
• Medium: 1.5x multiplier  
• Hard: 2x multiplier
• Speed Bonus: +50% (if solved under 30s)

🏆 **Game Features:**
• Real-time leaderboards updated instantly
• Anti-repetition system (500+ puzzle rotation)
• Hint system with contextual clues
• Automatic timeout after {Config.GAME_TIMEOUT} seconds
• Support for 1000+ groups simultaneously

⚙️ **Admin Commands:**
• `/broadcast <message>` - Send to all groups (owner only)
• `/stats` - Bot statistics (owner only)

🚀 **Tips for Success:**
1. Think about the movie's plot, characters, or iconic scenes
2. Don't overthink - sometimes it's simpler than you think
3. Use hints wisely - they're limited!
4. Speed matters - faster answers get bonus points

Need more help? Contact the bot owner or visit our support group!

🎭 **Ready to become a movie guessing legend?**"""

        await update.effective_message.reply_text(help_msg, parse_mode=ParseMode.MARKDOWN)

    @log_command_usage
    @rate_limit(calls_per_minute=10)
    async def gen_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /gen command - Generate new movie puzzle"""
        try:
            chat_id = update.effective_chat.id
            args = context.args

            # Parse arguments
            category = None
            difficulty = None

            if args:
                if len(args) >= 1 and args[0].lower() in ['hollywood', 'bollywood', 'tollywood']:
                    category = args[0].lower()
                if len(args) >= 2 and args[1].lower() in ['easy', 'medium', 'hard']:
                    difficulty = args[1].lower()
                elif len(args) >= 1 and args[0].lower() in ['easy', 'medium', 'hard']:
                    difficulty = args[0].lower()

            # Start new game
            success, message, session = await self.game_manager.start_new_game(
                chat_id, category, difficulty
            )

            if success:
                # Create interactive keyboard
                keyboard = [
                    [InlineKeyboardButton("💡 Hint", callback_data=f"hint_{session.id}")],
                    [InlineKeyboardButton("⏹️ End Game", callback_data=f"endgame_{session.id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(message)

        except Exception as e:
            logger.error(f"Error in gen command: {e}")
            await update.message.reply_text("❌ Failed to generate puzzle. Please try again.")

    @log_command_usage
    @rate_limit(calls_per_minute=30)
    async def guess_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /guess command"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "🤔 Please provide your guess! \n\nExample: `/guess Titanic`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            guess = " ".join(context.args)
            success, message = await self.game_manager.process_guess(update, context, guess)

            if success:
                # Game won - show celebration
                keyboard = [
                    [InlineKeyboardButton("🎮 New Game", callback_data="new_game")],
                    [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error in guess command: {e}")
            await update.message.reply_text("❌ Error processing your guess. Please try again.")

    @log_command_usage
    @rate_limit(calls_per_minute=5)
    async def hint_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /hint command"""
        try:
            chat_id = update.effective_chat.id
            success, message = await self.game_manager.get_hint(chat_id)
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error in hint command: {e}")
            await update.message.reply_text("❌ Error getting hint. Please try again.")

    @log_command_usage
    async def leaderboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /leaderboard command"""
        try:
            chat_id = update.effective_chat.id
            users = await db_manager.get_leaderboard(limit=10, chat_id=chat_id)

            leaderboard_text = format_leaderboard(
                users, 
                "🏆 Global Leaderboard" if update.effective_chat.type == ChatType.PRIVATE else "🏆 Top Players"
            )

            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="show_leaderboard")],
                [InlineKeyboardButton("📊 My Stats", callback_data="show_stats")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                leaderboard_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            await update.message.reply_text("❌ Error loading leaderboard. Please try again.")

    @log_command_usage
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            user_id = update.effective_user.id
            user = await db_manager.get_user(user_id)

            if not user:
                await update.message.reply_text("❌ User not found. Use /start to initialize.")
                return

            # Calculate additional stats
            win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
            avg_score = user.score / user.games_played if user.games_played > 0 else 0

            stats_msg = f"""📊 **Your Game Statistics** 📊

👤 **Player:** {user.username or user.first_name or 'Anonymous'}
⭐ **Total Score:** {user.score:,} points
🏆 **Games Won:** {user.games_won:,}
🎮 **Games Played:** {user.games_played:,}
📈 **Win Rate:** {win_rate:.1f}%
🎯 **Correct Guesses:** {user.correct_guesses:,}
💡 **Hints Used:** {user.hints_used:,}
📅 **Member Since:** {user.join_date.strftime('%B %d, %Y')}
🕐 **Last Active:** {user.last_active.strftime('%B %d, %Y')}

🔥 **Average Score per Game:** {avg_score:.1f} points"""

            keyboard = [
                [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
                [InlineKeyboardButton("🎮 New Game", callback_data="new_game")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                stats_msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("❌ Error loading statistics. Please try again.")

    @admin_only
    @log_command_usage
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /broadcast command - Owner only"""
        from bot.broadcast import BroadcastManager

        try:
            if not context.args:
                await update.message.reply_text(
                    "📢 **Broadcast Usage:**\n\n"
                    "`/broadcast Your message here`\n\n"
                    "This will send the message to all active groups and users.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            message = " ".join(context.args)
            broadcast_manager = BroadcastManager(db_manager)

            # Send broadcast
            success_count, total_count = await broadcast_manager.send_broadcast(
                context.bot, message, update.effective_user.id
            )

            result_msg = f"📢 **Broadcast Complete**\n\n"
            result_msg += f"✅ **Sent:** {success_count}\n"
            result_msg += f"📊 **Total Chats:** {total_count}\n"
            result_msg += f"📈 **Success Rate:** {success_count/total_count*100:.1f}%" if total_count > 0 else ""

            await update.message.reply_text(result_msg, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error in broadcast command: {e}")
            await update.message.reply_text("❌ Error sending broadcast. Please try again.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button callbacks"""
        try:
            query = update.callback_query
            await query.answer()

            data = query.data

            if data == "show_leaderboard":
                users = await db_manager.get_leaderboard(limit=10)
                leaderboard_text = format_leaderboard(users, "🏆 Global Leaderboard")

                await query.edit_message_text(
                    leaderboard_text,
                    parse_mode=ParseMode.MARKDOWN
                )

            elif data == "show_help":
                await self.help_command(update, context)

            elif data == "show_stats":
                await self.stats_command(update, context)

            elif data == "new_game":
                await self.gen_command(update, context)

            elif data.startswith("hint_"):
                session_id = data.split("_")[1]
                chat_id = update.effective_chat.id
                success, message = await self.game_manager.get_hint(chat_id)

                await query.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

            elif data.startswith("endgame_"):
                session_id = data.split("_")[1]
                chat_id = update.effective_chat.id
                success, message = await self.game_manager.end_game(chat_id, "manual")

                await query.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Error in button callback: {e}")

def setup_command_handlers(application: Application, game_manager: GameManager):
    """Setup all command handlers"""
    handlers = CommandHandlers(game_manager)

    # Command handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("gen", handlers.gen_command))
    application.add_handler(CommandHandler("guess", handlers.guess_command))
    application.add_handler(CommandHandler("hint", handlers.hint_command))
    application.add_handler(CommandHandler("leaderboard", handlers.leaderboard_command))
    application.add_handler(CommandHandler("stats", handlers.stats_command))
    application.add_handler(CommandHandler("broadcast", handlers.broadcast_command))

    # Callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(handlers.button_callback))

    logger.info("All command handlers registered successfully")
