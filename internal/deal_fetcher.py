"""
Deal fetcher and message formatter for G3r4kiHub
Handles deal validation, formatting, and preparation for posting
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List
from internal.amazon_api import get_amazon_client
from internal.db_manager import DatabaseManager
from config import settings
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DealFetcher:
    """Fetches and validates deals from various sources"""

    def __init__(self):
        """Initialize deal fetcher"""
        self.amazon_client = get_amazon_client()

    def fetch_deal_by_asin(self, db: Session, asin: str) -> Optional[Dict]:
        """
        Fetch and validate a deal by ASIN
        
        Args:
            db: Database session
            asin: Amazon Standard Identification Number
            
        Returns:
            Deal data dict or None if validation fails
        """
        # Check if already posted
        if DatabaseManager.is_deal_posted(db, asin):
            logger.info(f"Deal {asin} already posted, skipping")
            return None

        # Fetch from Amazon API
        product = self.amazon_client.get_product_by_asin(asin)
        if not product:
            logger.warning(f"Failed to fetch product {asin}")
            return None

        # Validate deal quality
        if not self._validate_deal(product):
            logger.warning(f"Deal {asin} failed validation")
            return None

        logger.info(f"Successfully fetched valid deal: {product['title']}")
        return product

    def fetch_deals_by_category(self, db: Session, category: str = "Electronics", 
                               limit: int = 5) -> List[Dict]:
        """
        Fetch deals by category (mock implementation)
        In production, integrate with real deal sources
        
        Args:
            db: Database session
            category: Product category
            limit: Maximum deals to fetch
            
        Returns:
            List of deal data
        """
        deals = []
        logger.info(f"Fetching {limit} deals from category: {category}")
        # Integration point for deal sources like:
        # - CamelCamelCamel API
        # - Slickdeals RSS
        # - Amazon Price History API
        return deals

    def validate_and_prepare_deal(self, db: Session, deal_data: Dict) -> Optional[Dict]:
        """
        Validate and prepare deal for posting
        
        Args:
            db: Database session
            deal_data: Raw deal data
            
        Returns:
            Prepared deal data or None if invalid
        """
        if not self._validate_deal(deal_data):
            return None

        # Cache the deal
        DatabaseManager.cache_deal(
            db,
            deal_data["asin"],
            deal_data["title"],
            deal_data["price"]
        )

        return deal_data

    # ============ Validation Methods ============

    @staticmethod
    def _validate_deal(deal: Dict) -> bool:
        """
        Validate deal quality and relevance
        
        Args:
            deal: Deal data to validate
            
        Returns:
            True if deal is valid
        """
        # Check required fields
        if not deal.get("asin") or not deal.get("price"):
            logger.warning("Deal missing required fields")
            return False

        # Price must be positive
        if deal.get("price", 0) <= 0:
            logger.warning(f"Invalid price: {deal.get('price')}")
            return False

        # Title must exist
        if not deal.get("title") or len(deal.get("title", "")) < 5:
            logger.warning("Invalid or missing title")
            return False

        # Minimum discount for featured deals (optional)
        if deal.get("discount_percent", 0) < 5:
            logger.debug(f"Low discount: {deal.get('discount_percent')}%")
            # Still valid, but lower priority

        return True

    @staticmethod
    def _is_high_value_deal(deal: Dict, min_discount: float = 20) -> bool:
        """Check if deal has significant discount"""
        discount = deal.get("discount_percent", 0)
        return discount >= min_discount


class MessageFormatter:
    """Formats deals into high-converting Telegram messages"""

    DISCOUNT_EMOJI = {
        0: "💙",      # Blue heart for sales
        10: "🟡",     # Yellow for good deals
        20: "🟠",     # Orange for great deals
        30: "🔥",     # Fire for excellent deals
    }

    @staticmethod
    def format_deal_message(deal: Dict) -> str:
        """
        Format deal into engaging Telegram message
        
        Args:
            deal: Deal data
            
        Returns:
            Formatted message for Telegram
        """
        title = deal.get("title", "Unknown Product")
        price = deal.get("price", 0)
        original_price = deal.get("original_price")
        discount = deal.get("discount_percent", 0)
        
        # Get appropriate emoji based on discount
        emoji = MessageFormatter._get_discount_emoji(discount)
        
        # Build message
        message = f"{emoji} DEAL ALERT {emoji}\n\n"
        message += f"🛍️ {title[:80]}\n"
        message += f"💰 Price: ${price:.2f}"
        
        if original_price:
            message += f" (Was ${original_price:.2f})"
        
        if discount > 0:
            message += f"\n🎯 Save: {discount:.0f}%"
        
        message += f"\n\n{settings.affiliate_disclosure_text}"
        
        return message

    @staticmethod
    def format_deal_with_button(deal: Dict) -> tuple:
        """
        Format deal message with inline button
        
        Args:
            deal: Deal data
            
        Returns:
            Tuple of (message_text, inline_keyboard_markup)
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message = MessageFormatter.format_deal_message(deal)
        
        keyboard = [[
            InlineKeyboardButton(
                "🛒 Buy on Amazon",
                url=deal.get("affiliate_url", "")
            )
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return message, reply_markup

    @staticmethod
    def format_summary_message(deals: List[Dict]) -> str:
        """
        Format multiple deals as summary/digest
        
        Args:
            deals: List of deals
            
        Returns:
            Formatted summary message
        """
        if not deals:
            return "No deals found today!"

        message = "🔥 TOP DEALS TODAY 🔥\n\n"
        
        for idx, deal in enumerate(deals[:5], 1):
            discount = deal.get("discount_percent", 0)
            price = deal.get("price", 0)
            title = deal.get("title", "Unknown")[:50]
            
            message += f"{idx}. {title}\n"
            message += f"   💰 ${price:.2f}"
            if discount > 0:
                message += f" ({discount:.0f}% off)"
            message += "\n\n"
        
        message += f"\n{settings.affiliate_disclosure_text}"
        
        return message

    @staticmethod
    def _get_discount_emoji(discount: float) -> str:
        """Get emoji based on discount percentage"""
        if discount >= 30:
            return "🔥"
        elif discount >= 20:
            return "🟠"
        elif discount >= 10:
            return "🟡"
        else:
            return "💙"

    @staticmethod
    def format_analytics_alert(stats: Dict) -> str:
        """
        Format analytics for admin notifications
        
        Args:
            stats: Analytics statistics
            
        Returns:
            Formatted alert message
        """
        message = "📊 DAILY ANALYTICS REPORT\n\n"
        message += f"📈 Deals Posted: {stats.get('deals_posted', 0)}\n"
        message += f"👁️ Total Views: {stats.get('total_views', 0)}\n"
        message += f"🖱️ Total Clicks: {stats.get('total_clicks', 0)}\n"
        message += f"💵 Revenue: ${stats.get('revenue', 0):.2f}\n"
        message += f"📊 CTR: {stats.get('ctr', 0):.2f}%\n"
        
        return message

    @staticmethod
    def format_error_alert(error_details: Dict) -> str:
        """
        Format error alert for admin
        
        Args:
            error_details: Error information
            
        Returns:
            Formatted error message
        """
        message = "❌ BOT ERROR ALERT ❌\n\n"
        message += f"Error: {error_details.get('action', 'Unknown')}\n"
        message += f"Details: {error_details.get('message', 'No details')}\n"
        message += f"Time: {datetime.utcnow().isoformat()}\n"
        
        return message
