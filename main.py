"""
Main entry point for G3r4kiHub
Starts the Telegram bot and scheduler
"""

import asyncio
import logging
import sys
from datetime import datetime

from config import settings
from internal.models import create_tables, SessionLocal
from services.scheduler import get_scheduler
from services.telegram_bot import get_bot_manager

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file)
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Starting G3r4kiHub - Telegram Amazon Affiliate Bot")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        create_tables()
        logger.info("✓ Database initialized")
        
        # Initialize bot
        logger.info("Initializing Telegram bot...")
        bot_manager = get_bot_manager()
        
        if not bot_manager.bot:
            logger.error("Failed to initialize Telegram bot")
            sys.exit(1)
        
        # Check bot health
        health_ok = await bot_manager.health_check()
        if health_ok:
            logger.info("✓ Telegram bot ready")
        else:
            logger.warning("⚠ Telegram bot health check failed")
        
        # Start scheduler
        logger.info("Starting scheduler...")
        scheduler = get_scheduler()
        scheduler.start()
        
        if scheduler.is_running:
            logger.info("✓ Scheduler started")
            jobs = scheduler.list_jobs()
            for job in jobs:
                logger.info(f"  - Job: {job.name} (next run: {job.next_run_time})")
        else:
            logger.warning("⚠ Scheduler failed to start")
        
        logger.info("=" * 60)
        logger.info("G3r4kiHub is running! (Press Ctrl+C to stop)")
        logger.info("=" * 60)
        logger.info(f"Telegram Channel: {settings.telegram_channel_id}")
        logger.info(f"Bot Status: {'✓ Active' if bot_manager.bot else '✗ Inactive'}")
        logger.info(f"Scheduler Status: {'✓ Running' if scheduler.is_running else '✗ Stopped'}")
        logger.info(f"Database: SQLite" if "sqlite" in settings.database_url else "PostgreSQL")
        logger.info("=" * 60)
        
        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping G3r4kiHub...")
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.stop()
        logger.info("✓ G3r4kiHub stopped")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
