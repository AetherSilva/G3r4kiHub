"""
Database models for G3r4kiHub
Defines all database tables and relationships
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

# Create base class for models
Base = declarative_base()

# Database engine setup
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=settings.debug_mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class PostedDeal(Base):
    """Model for tracking posted deals"""
    __tablename__ = "posted_deals"

    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String, unique=True, index=True)
    title = Column(String(500))
    price = Column(Float)
    original_price = Column(Float, nullable=True)
    discount_percent = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    affiliate_url = Column(String(500))
    category = Column(String(100), nullable=True)
    posted_at = Column(DateTime, default=datetime.utcnow, index=True)
    telegram_message_id = Column(Integer, nullable=True)
    posted_to_channel = Column(Boolean, default=False)
    posted_to_group = Column(Boolean, default=False)


class Analytics(Base):
    """Model for tracking analytics"""
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(String, index=True)  # Reference to ASIN
    telegram_message_id = Column(Integer, index=True)
    view_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    conversion_count = Column(Integer, default=0)
    revenue_amount = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)  # Click-through rate
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    last_updated = Column(DateTime, default=datetime.utcnow)


class Channel(Base):
    """Model for managing channel information"""
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(String, unique=True, index=True)
    channel_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    member_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_post_at = Column(DateTime, nullable=True)


class BotLog(Base):
    """Model for logging bot activities"""
    __tablename__ = "bot_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), index=True)
    status = Column(String(50))  # success, error, pending
    message = Column(Text)
    error_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class DealCache(Base):
    """Model for caching deals to avoid duplicates"""
    __tablename__ = "deal_cache"

    id = Column(Integer, primary_key=True, index=True)
    asin = Column(String, unique=True, index=True)
    title = Column(String(500))
    price = Column(Float)
    last_seen = Column(DateTime, default=datetime.utcnow, index=True)
    is_active = Column(Boolean, default=True)


def create_tables():
    """Create all tables in database"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
