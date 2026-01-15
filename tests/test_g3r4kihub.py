"""
Test suite for G3r4kiHub
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from internal.deal_fetcher import MessageFormatter, DealFetcher
from internal.db_manager import DatabaseManager
from internal.models import SessionLocal


class TestMessageFormatter:
    """Test message formatting"""

    def test_format_deal_message(self):
        """Test basic deal message formatting"""
        deal = {
            "title": "Sony WH-1000XM5 Headphones",
            "price": 299.99,
            "original_price": 399.99,
            "discount_percent": 25,
            "asin": "B0XXXXXXX"
        }
        
        message = MessageFormatter.format_deal_message(deal)
        
        assert "Sony WH-1000XM5" in message
        assert "299.99" in message
        assert "25" in message
        assert "Amazon Affiliate Link" in message

    def test_discount_emoji(self):
        """Test discount emoji selection"""
        assert MessageFormatter._get_discount_emoji(35) == "🔥"
        assert MessageFormatter._get_discount_emoji(25) == "🟠"
        assert MessageFormatter._get_discount_emoji(15) == "🟡"
        assert MessageFormatter._get_discount_emoji(5) == "💙"

    def test_summary_message(self):
        """Test summary message formatting"""
        deals = [
            {
                "title": "Deal 1",
                "price": 99.99,
                "discount_percent": 20,
                "asin": "B001"
            },
            {
                "title": "Deal 2",
                "price": 199.99,
                "discount_percent": 30,
                "asin": "B002"
            }
        ]
        
        message = MessageFormatter.format_summary_message(deals)
        
        assert "TOP DEALS" in message
        assert "Deal 1" in message
        assert "Deal 2" in message


class TestDealFetcher:
    """Test deal fetcher"""

    def test_validate_deal_valid(self):
        """Test validation of valid deal"""
        deal = {
            "asin": "B0XXXXXXX",
            "title": "Valid Product Title",
            "price": 99.99,
            "discount_percent": 20
        }
        
        assert DealFetcher._validate_deal(deal) is True

    def test_validate_deal_missing_asin(self):
        """Test validation fails without ASIN"""
        deal = {
            "title": "Valid Product Title",
            "price": 99.99
        }
        
        assert DealFetcher._validate_deal(deal) is False

    def test_validate_deal_invalid_price(self):
        """Test validation fails with invalid price"""
        deal = {
            "asin": "B0XXXXXXX",
            "title": "Valid Product Title",
            "price": 0,
        }
        
        assert DealFetcher._validate_deal(deal) is False

    def test_high_value_deal(self):
        """Test high value deal detection"""
        deal = {"discount_percent": 25}
        assert DealFetcher._is_high_value_deal(deal, min_discount=20) is True
        
        deal = {"discount_percent": 15}
        assert DealFetcher._is_high_value_deal(deal, min_discount=20) is False


class TestDatabaseManager:
    """Test database operations"""

    def test_get_dashboard_stats(self):
        """Test dashboard stats generation"""
        db = SessionLocal()
        try:
            stats = DatabaseManager.get_dashboard_stats(db)
            
            assert "total_deals" in stats
            assert "today_deals" in stats
            assert "total_revenue" in stats
            assert "average_ctr" in stats
            assert "timestamp" in stats
        finally:
            db.close()

    def test_log_action(self):
        """Test action logging"""
        db = SessionLocal()
        try:
            DatabaseManager.log_action(
                db,
                action="test",
                status="success",
                message="Test message"
            )
            
            logs = DatabaseManager.get_logs(db, action_filter="test")
            assert len(logs) > 0
            assert logs[0].action == "test"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
