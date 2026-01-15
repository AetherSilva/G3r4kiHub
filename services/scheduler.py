"""
Analytics tracking and scheduler for G3r4kiHub
Handles deal posting schedule and analytics updates
"""

import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from config import settings
from internal.db_manager import DatabaseManager
from internal.deal_fetcher import DealFetcher
from internal.models import SessionLocal
from services.telegram_bot import get_bot_manager

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manager for bot scheduling and automation"""

    def __init__(self):
        """Initialize scheduler"""
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.deal_fetcher = DealFetcher()
        self.bot_manager = get_bot_manager()

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        if not settings.scheduler_enabled:
            logger.warning("Scheduler disabled in configuration")
            return

        try:
            # Add posting job
            self.scheduler.add_job(
                self.post_deals_job,
                trigger=CronTrigger(
                    hour=f"{settings.posting_start_hour}-{settings.posting_end_hour}",
                    minute="0",
                    second="0",
                    timezone=timezone('UTC')
                ),
                id="post_deals",
                name="Post scheduled deals",
                replace_existing=True,
                max_instances=1
            )

            # Add analytics job
            self.scheduler.add_job(
                self.analytics_job,
                trigger=CronTrigger(
                    hour="0",
                    minute="0",
                    second="0",
                    timezone=timezone('UTC')
                ),
                id="analytics",
                name="Daily analytics report",
                replace_existing=True,
                max_instances=1
            )

            # Add cleanup job
            self.scheduler.add_job(
                self.cleanup_job,
                trigger=CronTrigger(
                    hour="3",
                    minute="0",
                    second="0",
                    timezone=timezone('UTC')
                ),
                id="cleanup",
                name="Database cleanup",
                replace_existing=True,
                max_instances=1
            )

            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler started successfully")

        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return

        try:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {str(e)}")

    def post_deals_job(self):
        """Job to post deals"""
        db = SessionLocal()
        try:
            logger.info("Starting post deals job")
            
            # This is where you'd fetch deals from Amazon or other sources
            # For now, this is a placeholder
            # In production, integrate with deal APIs
            
            logger.info("Post deals job completed")
            DatabaseManager.log_action(
                db,
                action="post_deals_job",
                status="success",
                message="Posted daily deals"
            )

        except Exception as e:
            logger.error(f"Error in post deals job: {str(e)}")
            DatabaseManager.log_action(
                db,
                action="post_deals_job",
                status="error",
                message=f"Error posting deals: {str(e)}",
                error_details=str(e)
            )
        finally:
            db.close()

    def analytics_job(self):
        """Job to generate daily analytics"""
        db = SessionLocal()
        try:
            logger.info("Starting analytics job")

            stats = DatabaseManager.get_dashboard_stats(db)
            
            logger.info(f"Analytics generated: {stats}")
            DatabaseManager.log_action(
                db,
                action="analytics_job",
                status="success",
                message=f"Daily stats: {stats['total_deals']} deals, ${stats['total_revenue']}"
            )

        except Exception as e:
            logger.error(f"Error in analytics job: {str(e)}")
            DatabaseManager.log_action(
                db,
                action="analytics_job",
                status="error",
                message=f"Error generating analytics: {str(e)}",
                error_details=str(e)
            )
        finally:
            db.close()

    def cleanup_job(self):
        """Job to clean up old data"""
        db = SessionLocal()
        try:
            logger.info("Starting cleanup job")
            
            # Clean up old logs (older than 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            db.query(DatabaseManager).filter(
                BotLog.created_at < cutoff_date
            ).delete()
            db.commit()
            
            logger.info("Cleanup job completed")
            DatabaseManager.log_action(
                db,
                action="cleanup_job",
                status="success",
                message="Cleaned up old logs"
            )

        except Exception as e:
            logger.error(f"Error in cleanup job: {str(e)}")
        finally:
            db.close()

    def get_next_run_time(self, job_id: str) -> datetime:
        """Get next run time for a job"""
        job = self.scheduler.get_job(job_id)
        if job:
            return job.next_run_time
        return None

    def list_jobs(self) -> list:
        """List all scheduled jobs"""
        return self.scheduler.get_jobs()


class AnalyticsTracker:
    """Tracks analytics for deals"""

    @staticmethod
    def update_deal_analytics(db: Session, deal_id: str, clicks: int = 0, 
                             conversions: int = 0, revenue: float = 0.0):
        """
        Update analytics for a deal
        
        Args:
            db: Database session
            deal_id: ASIN of the deal
            clicks: Number of clicks
            conversions: Number of conversions
            revenue: Revenue amount
        """
        analytics = DatabaseManager.get_analytics_by_deal(db, deal_id)
        
        if analytics:
            analytics.click_count += clicks
            analytics.conversion_count += conversions
            analytics.revenue_amount += revenue
            
            # Calculate CTR
            if analytics.view_count > 0:
                analytics.ctr = (analytics.click_count / analytics.view_count) * 100
            
            analytics.last_updated = datetime.utcnow()
            db.commit()
        else:
            # Create new record
            analytics_data = {
                "deal_id": deal_id,
                "click_count": clicks,
                "conversion_count": conversions,
                "revenue_amount": revenue,
                "ctr": 0.0
            }
            DatabaseManager.add_analytics_record(db, analytics_data)

    @staticmethod
    def get_deal_performance(db: Session, days: int = 30) -> dict:
        """
        Get overall deal performance metrics
        
        Args:
            db: Database session
            days: Number of days to analyze
            
        Returns:
            Performance metrics dictionary
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        deals = DatabaseManager.get_posted_deals_by_date(db, start_date, datetime.utcnow())
        total_revenue = DatabaseManager.get_total_revenue(db, days)
        avg_ctr = DatabaseManager.get_average_ctr(db, days)
        
        return {
            "total_deals": len(deals),
            "total_revenue": round(total_revenue, 2),
            "average_ctr": round(avg_ctr, 2),
            "date_range": f"{start_date.date()} to {datetime.utcnow().date()}",
            "top_deals": DatabaseManager.get_top_performing_deals(db, limit=5)
        }

    @staticmethod
    def get_hourly_stats(db: Session) -> dict:
        """
        Get statistics for current hour
        
        Args:
            db: Database session
            
        Returns:
            Hourly statistics
        """
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        
        deals = DatabaseManager.get_posted_deals_by_date(db, hour_ago, now)
        
        return {
            "deals_posted": len(deals),
            "timestamp": now.isoformat(),
            "period": "1 hour"
        }


# Global scheduler instance
_scheduler: SchedulerManager = SchedulerManager()


def get_scheduler() -> SchedulerManager:
    """Get scheduler instance"""
    return _scheduler
