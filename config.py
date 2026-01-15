"""
Configuration management for G3r4kiHub
Handles environment variables and settings
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings from environment variables"""

    # Telegram Configuration
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    telegram_channel_id: str = Field(..., alias="TELEGRAM_CHANNEL_ID")
    telegram_group_id: str = Field(..., alias="TELEGRAM_GROUP_ID")

    # Amazon API Configuration
    amazon_access_key: str = Field(..., alias="AMAZON_ACCESS_KEY")
    amazon_secret_key: str = Field(..., alias="AMAZON_SECRET_KEY")
    amazon_partner_tag: str = Field(..., alias="AMAZON_PARTNER_TAG")
    amazon_country: str = Field(default="US", alias="AMAZON_COUNTRY")

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./g3r4kihub.db", alias="DATABASE_URL"
    )
    postgres_user: str = Field(default="g3r4kihub", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="g3r4kihub", alias="POSTGRES_DB")

    # Scheduler Configuration
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    post_interval_hours: int = Field(default=3, alias="POST_INTERVAL_HOURS")
    posts_per_day: int = Field(default=10, alias="POSTS_PER_DAY")
    posting_start_hour: int = Field(default=8, alias="POSTING_START_HOUR")
    posting_end_hour: int = Field(default=22, alias="POSTING_END_HOUR")

    # Analytics
    enable_analytics: bool = Field(default=True, alias="ENABLE_ANALYTICS")
    affiliate_disclosure_text: str = Field(
        default="🔗 Amazon Affiliate Link",
        alias="AFFILIATE_DISCLOSURE_TEXT",
    )

    # FastAPI Admin
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="admin", alias="ADMIN_PASSWORD")
    api_secret_key: str = Field(
        default="your-secret-key", alias="API_SECRET_KEY"
    )
    debug_mode: bool = Field(default=False, alias="DEBUG_MODE")

    # Redis Configuration (Optional)
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    enable_redis: bool = Field(default=False, alias="ENABLE_REDIS")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/g3r4kihub.log", alias="LOG_FILE")

    # Email Alerts (Optional)
    smtp_server: str = Field(default="smtp.gmail.com", alias="SMTP_SERVER")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    alert_email: str = Field(default="", alias="ALERT_EMAIL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Export settings instance
settings = get_settings()
