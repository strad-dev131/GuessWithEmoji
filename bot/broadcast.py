"""
Broadcast functionality for GuessWithEmojiBot
Handles mass messaging to all groups and users
"""

import asyncio
import logging
from typing import Tuple, List
from datetime import datetime, timezone

from telegram import Bot
from telegram.error import Forbidden, BadRequest, NetworkError

from database.db import DatabaseManager
from utils.helpers import safe_send_message

logger = logging.getLogger(__name__)

class BroadcastManager:
    """Manages broadcast operations"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def send_broadcast(self, bot: Bot, message: str, sender_id: int) -> Tuple[int, int]:
        """Send broadcast message to all active chats"""
        try:
            # Get all chat IDs from database (you'll need to implement this)
            chat_ids = await self._get_all_chat_ids()

            success_count = 0
            total_count = len(chat_ids)

            # Log broadcast start
            logger.info(f"Starting broadcast to {total_count} chats by user {sender_id}")

            # Add broadcast header
            broadcast_msg = f"📢 **Official Announcement**\n\n{message}"

            # Send messages with rate limiting
            for chat_id in chat_ids:
                try:
                    success = await safe_send_message(
                        bot, chat_id, broadcast_msg, parse_mode="Markdown"
                    )
                    if success:
                        success_count += 1

                    # Small delay to respect rate limits
                    await asyncio.sleep(0.05)  # 20 messages per second max

                except Exception as e:
                    logger.warning(f"Failed to send broadcast to {chat_id}: {e}")
                    continue

            # Log results
            logger.info(f"Broadcast complete: {success_count}/{total_count} successful")

            # Store broadcast record
            await self._store_broadcast_record(sender_id, message, success_count, total_count)

            return success_count, total_count

        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            return 0, 0

    async def _get_all_chat_ids(self) -> List[int]:
        """Get all chat IDs from database"""
        try:
            # This would get chat IDs from your chat_stats collection
            # For now, return empty list - implement based on your needs
            cursor = self.db.db.chat_stats.find({}, {"chat_id": 1})
            chat_ids = []
            async for doc in cursor:
                chat_ids.append(doc["chat_id"])
            return chat_ids
        except Exception as e:
            logger.error(f"Error getting chat IDs: {e}")
            return []

    async def _store_broadcast_record(self, sender_id: int, message: str, 
                                    success_count: int, total_count: int):
        """Store broadcast record in database"""
        try:
            record = {
                "sender_id": sender_id,
                "message": message,
                "success_count": success_count,
                "total_count": total_count,
                "timestamp": datetime.now(timezone.utc)
            }
            await self.db.db.broadcasts.insert_one(record)
        except Exception as e:
            logger.error(f"Error storing broadcast record: {e}")
