"""
Telegram Bot Core
Handles all Telegram bot operations and posting
"""

import logging
from typing import Optional
from telegram import Bot, Update
from telegram.error import TelegramError
from datetime import datetime
from config import settings
from internal.db_manager import DatabaseManager
from internal.deal_fetcher import MessageFormatter
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """Manager for Telegram bot operations"""

    def __init__(self):
        """Initialize Telegram bot"""
        try:
            self.bot = Bot(token=settings.telegram_bot_token)
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            self.bot = None

    async def post_deal(self, db: Session, deal: dict) -> Optional[int]:
        """
        Post a deal to Telegram channel
        
        Args:
            db: Database session
            deal: Deal data to post
            
        Returns:
            Telegram message ID if successful, None otherwise
        """
        if not self.bot:
            logger.error("Bot not initialized")
            return None

        try:
            message_text, reply_markup = MessageFormatter.format_deal_with_button(deal)
            
            # Send message to channel
            message = await self.bot.send_message(
                chat_id=settings.telegram_channel_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
            
            # Save to database
            deal_data = {
                "asin": deal.get("asin"),
                "title": deal.get("title"),
                "price": deal.get("price"),
                "original_price": deal.get("original_price"),
                "discount_percent": deal.get("discount_percent"),
                "image_url": deal.get("image_url"),
                "affiliate_url": deal.get("affiliate_url"),
                "category": deal.get("category"),
                "telegram_message_id": message.message_id,
                "posted_to_channel": True,
                "posted_at": datetime.utcnow()
            }
            
            DatabaseManager.add_posted_deal(db, deal_data)
            
            logger.info(f"Successfully posted deal {deal.get('asin')} to channel")
            
            # Log action
            DatabaseManager.log_action(
                db,
                action="post_deal",
                status="success",
                message=f"Posted: {deal.get('title')}"
            )
            
            return message.message_id

        except TelegramError as e:
            logger.error(f"Telegram error posting deal: {str(e)}")
            DatabaseManager.log_action(
                db,
                action="post_deal",
                status="error",
                message=f"Telegram error: {str(e)}",
                error_details=str(e)
            )
            return None
        except Exception as e:
            logger.error(f"Unexpected error posting deal: {str(e)}")
            DatabaseManager.log_action(
                db,
                action="post_deal",
                status="error",
                message=f"Unexpected error: {str(e)}",
                error_details=str(e)
            )
            return None

    async def post_summary(self, db: Session, deals: list) -> Optional[int]:
        """
        Post daily deal summary
        
        Args:
            db: Database session
            deals: List of deals for summary
            
        Returns:
            Telegram message ID if successful
        """
        if not self.bot:
            return None

        try:
            message_text = MessageFormatter.format_summary_message(deals)
            
            message = await self.bot.send_message(
                chat_id=settings.telegram_channel_id,
                text=message_text,
                parse_mode="HTML"
            )
            
            logger.info(f"Posted summary with {len(deals)} deals")
            DatabaseManager.log_action(
                db,
                action="post_summary",
                status="success",
                message=f"Posted summary: {len(deals)} deals"
            )
            
            return message.message_id

        except TelegramError as e:
            logger.error(f"Error posting summary: {str(e)}")
            DatabaseManager.log_action(
                db,
                action="post_summary",
                status="error",
                message=f"Failed to post summary: {str(e)}"
            )
            return None

    async def send_admin_alert(self, alert_type: str, data: dict) -> bool:
        """
        Send alert to admin
        
        Args:
            alert_type: Type of alert (error, analytics, warning)
            data: Alert data
            
        Returns:
            True if sent successfully
        """
        if not self.bot:
            return False

        try:
            if alert_type == "analytics":
                message = MessageFormatter.format_analytics_alert(data)
            elif alert_type == "error":
                message = MessageFormatter.format_error_alert(data)
            else:
                message = str(data)
            
            # Send to admin (implement with admin user ID)
            # await self.bot.send_message(chat_id=ADMIN_USER_ID, text=message)
            logger.info(f"Admin alert sent: {alert_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to send admin alert: {str(e)}")
            return False

    async def pin_message(self, chat_id: str, message_id: int) -> bool:
        """
        Pin a message in channel
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to pin
            
        Returns:
            True if successful
        """
        if not self.bot:
            return False

        try:
            await self.bot.pin_chat_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"Pinned message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to pin message: {str(e)}")
            return False

    async def edit_message(self, chat_id: str, message_id: int, text: str) -> bool:
        """
        Edit an existing message
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to edit
            text: New message text
            
        Returns:
            True if successful
        """
        if not self.bot:
            return False

        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text
            )
            logger.info(f"Edited message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to edit message: {str(e)}")
            return False

    async def delete_message(self, chat_id: str, message_id: int) -> bool:
        """
        Delete a message
        
        Args:
            chat_id: Chat ID
            message_id: Message ID to delete
            
        Returns:
            True if successful
        """
        if not self.bot:
            return False

        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            logger.info(f"Deleted message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete message: {str(e)}")
            return False

    async def get_chat_info(self, chat_id: str) -> Optional[dict]:
        """
        Get information about a chat/channel
        
        Args:
            chat_id: Chat ID
            
        Returns:
            Chat info dict or None
        """
        if not self.bot:
            return None

        try:
            chat = await self.bot.get_chat(chat_id=chat_id)
            return {
                "id": chat.id,
                "title": chat.title,
                "type": chat.type,
                "member_count": await self.bot.get_chat_member_count(chat_id=chat_id),
                "description": chat.description
            }
        except Exception as e:
            logger.error(f"Failed to get chat info: {str(e)}")
            return None

    async def health_check(self) -> bool:
        """
        Check if bot is working
        
        Returns:
            True if bot is operational
        """
        if not self.bot:
            return False

        try:
            await self.bot.get_me()
            logger.debug("Bot health check passed")
            return True
        except Exception as e:
            logger.error(f"Bot health check failed: {str(e)}")
            return False


# Global bot instance
_bot_manager: Optional[TelegramBotManager] = None


def get_bot_manager() -> TelegramBotManager:
    """Get or create bot manager"""
    global _bot_manager
    if _bot_manager is None:
        _bot_manager = TelegramBotManager()
    return _bot_manager
