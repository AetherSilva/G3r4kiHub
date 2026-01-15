"""
Database operations for G3r4kiHub
Handles all database interactions with SQLAlchemy
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from internal.models import PostedDeal, Analytics, BotLog, DealCache, Channel, SessionLocal


class DatabaseManager:
    """Manager for all database operations"""

    @staticmethod
    def get_session():
        """Get a database session"""
        return SessionLocal()

    # ============ Posted Deals Operations ============

    @staticmethod
    def add_posted_deal(db: Session, deal_data: dict) -> PostedDeal:
        """Add a new posted deal"""
        new_deal = PostedDeal(**deal_data)
        db.add(new_deal)
        db.commit()
        db.refresh(new_deal)
        return new_deal

    @staticmethod
    def is_deal_posted(db: Session, asin: str) -> bool:
        """Check if deal ASIN already posted"""
        return db.query(PostedDeal).filter(PostedDeal.asin == asin).first() is not None

    @staticmethod
    def get_posted_deal(db: Session, asin: str) -> PostedDeal:
        """Get a posted deal by ASIN"""
        return db.query(PostedDeal).filter(PostedDeal.asin == asin).first()

    @staticmethod
    def get_all_posted_deals(db: Session, limit: int = 100) -> list:
        """Get all posted deals with optional limit"""
        return db.query(PostedDeal).order_by(desc(PostedDeal.posted_at)).limit(limit).all()

    @staticmethod
    def get_posted_deals_by_date(db: Session, start_date: datetime, end_date: datetime) -> list:
        """Get posted deals within date range"""
        return db.query(PostedDeal).filter(
            PostedDeal.posted_at.between(start_date, end_date)
        ).all()

    @staticmethod
    def update_deal_message_id(db: Session, asin: str, message_id: int):
        """Update telegram message ID for a deal"""
        deal = db.query(PostedDeal).filter(PostedDeal.asin == asin).first()
        if deal:
            deal.telegram_message_id = message_id
            db.commit()

    # ============ Analytics Operations ============

    @staticmethod
    def add_analytics_record(db: Session, analytics_data: dict) -> Analytics:
        """Add analytics record"""
        new_record = Analytics(**analytics_data)
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record

    @staticmethod
    def get_analytics_by_deal(db: Session, deal_id: str) -> Analytics:
        """Get analytics for a specific deal"""
        return db.query(Analytics).filter(Analytics.deal_id == deal_id).first()

    @staticmethod
    def get_total_revenue(db: Session, days: int = 30) -> float:
        """Get total revenue for last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        result = db.query(func.sum(Analytics.revenue_amount)).filter(
            Analytics.timestamp >= start_date
        ).scalar()
        return float(result) if result else 0.0

    @staticmethod
    def get_average_ctr(db: Session, days: int = 30) -> float:
        """Get average CTR for last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        result = db.query(func.avg(Analytics.ctr)).filter(
            Analytics.timestamp >= start_date
        ).scalar()
        return float(result) if result else 0.0

    @staticmethod
    def get_top_performing_deals(db: Session, limit: int = 5) -> list:
        """Get top performing deals by revenue"""
        return db.query(PostedDeal, Analytics).join(
            Analytics, PostedDeal.asin == Analytics.deal_id
        ).order_by(desc(Analytics.revenue_amount)).limit(limit).all()

    # ============ Bot Logs Operations ============

    @staticmethod
    def log_action(db: Session, action: str, status: str, message: str, error_details: str = None):
        """Log a bot action"""
        log_entry = BotLog(
            action=action,
            status=status,
            message=message,
            error_details=error_details
        )
        db.add(log_entry)
        db.commit()

    @staticmethod
    def get_logs(db: Session, action_filter: str = None, limit: int = 100) -> list:
        """Get bot logs with optional action filter"""
        query = db.query(BotLog)
        if action_filter:
            query = query.filter(BotLog.action == action_filter)
        return query.order_by(desc(BotLog.created_at)).limit(limit).all()

    @staticmethod
    def get_error_logs(db: Session, hours: int = 24, limit: int = 50) -> list:
        """Get recent error logs"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        return db.query(BotLog).filter(
            BotLog.status == "error",
            BotLog.created_at >= start_time
        ).order_by(desc(BotLog.created_at)).limit(limit).all()

    # ============ Deal Cache Operations ============

    @staticmethod
    def cache_deal(db: Session, asin: str, title: str, price: float):
        """Cache a deal for deduplication"""
        existing = db.query(DealCache).filter(DealCache.asin == asin).first()
        if existing:
            existing.last_seen = datetime.utcnow()
            existing.is_active = True
        else:
            new_cache = DealCache(asin=asin, title=title, price=price)
            db.add(new_cache)
        db.commit()

    @staticmethod
    def is_deal_cached(db: Session, asin: str) -> bool:
        """Check if deal is in cache"""
        return db.query(DealCache).filter(
            DealCache.asin == asin,
            DealCache.is_active == True
        ).first() is not None

    # ============ Channel Operations ============

    @staticmethod
    def add_channel(db: Session, channel_id: str, channel_name: str, description: str = None):
        """Add a channel"""
        channel = Channel(channel_id=channel_id, channel_name=channel_name, description=description)
        db.add(channel)
        db.commit()

    @staticmethod
    def get_active_channels(db: Session) -> list:
        """Get all active channels"""
        return db.query(Channel).filter(Channel.is_active == True).all()

    @staticmethod
    def update_channel_post_time(db: Session, channel_id: str):
        """Update last post time for a channel"""
        channel = db.query(Channel).filter(Channel.channel_id == channel_id).first()
        if channel:
            channel.last_post_at = datetime.utcnow()
            db.commit()

    # ============ Dashboard Statistics ============

    @staticmethod
    def get_dashboard_stats(db: Session) -> dict:
        """Get all statistics for dashboard"""
        total_deals = db.query(func.count(PostedDeal.id)).scalar()
        today_deals = db.query(func.count(PostedDeal.id)).filter(
            PostedDeal.posted_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).scalar()
        total_revenue = DatabaseManager.get_total_revenue(db, days=30)
        avg_ctr = DatabaseManager.get_average_ctr(db, days=30)
        
        return {
            "total_deals": total_deals or 0,
            "today_deals": today_deals or 0,
            "total_revenue": round(total_revenue, 2),
            "average_ctr": round(avg_ctr, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
