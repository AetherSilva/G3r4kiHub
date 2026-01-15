"""
API Routes for analytics
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional

from internal.models import SessionLocal
from internal.db_manager import DatabaseManager
from services.scheduler import AnalyticsTracker

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def get_analytics_summary(days: int = Query(30, ge=1, le=365)):
    """Get analytics summary for period"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        total_deals = db.query(DatabaseManager).count()
        total_revenue = DatabaseManager.get_total_revenue(db, days=days)
        avg_ctr = DatabaseManager.get_average_ctr(db, days=days)
        
        return {
            "period_days": days,
            "total_deals": total_deals,
            "total_revenue": round(total_revenue, 2),
            "average_ctr": round(avg_ctr, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        db.close()


@router.get("/deals-by-category")
async def get_deals_by_category(days: int = Query(30, ge=1, le=365)):
    """Get deal count by category"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query deals grouped by category
        deals = DatabaseManager.get_posted_deals_by_date(db, start_date, datetime.utcnow())
        
        category_stats = {}
        for deal in deals:
            cat = deal.category or "Other"
            if cat not in category_stats:
                category_stats[cat] = 0
            category_stats[cat] += 1
        
        return {
            "period_days": days,
            "categories": category_stats,
            "total_deals": sum(category_stats.values())
        }
    finally:
        db.close()


@router.get("/daily-stats")
async def get_daily_stats(date: Optional[str] = None):
    """Get stats for specific day or today"""
    db = SessionLocal()
    try:
        if date:
            target_date = datetime.fromisoformat(date).replace(hour=0, minute=0, second=0)
        else:
            target_date = datetime.utcnow().replace(hour=0, minute=0, second=0)
        
        next_day = target_date + timedelta(days=1)
        
        deals = DatabaseManager.get_posted_deals_by_date(db, target_date, next_day)
        
        # Calculate totals
        total_revenue = sum(
            db.query(DatabaseManager.get_analytics_by_deal(db, d.asin).revenue_amount or 0)
            for d in deals
        )
        
        return {
            "date": target_date.date().isoformat(),
            "deals_posted": len(deals),
            "total_revenue": round(total_revenue, 2),
            "deals": [
                {
                    "asin": d.asin,
                    "title": d.title,
                    "price": d.price,
                    "discount_percent": d.discount_percent
                }
                for d in deals
            ]
        }
    finally:
        db.close()


@router.get("/top-categories")
async def get_top_categories(limit: int = Query(10, le=50), days: int = Query(30, ge=1, le=365)):
    """Get top performing categories"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        deals = DatabaseManager.get_posted_deals_by_date(db, start_date, datetime.utcnow())
        
        category_revenue = {}
        for deal in deals:
            cat = deal.category or "Other"
            analytics = DatabaseManager.get_analytics_by_deal(db, deal.asin)
            if analytics:
                if cat not in category_revenue:
                    category_revenue[cat] = 0
                category_revenue[cat] += analytics.revenue_amount
        
        sorted_cats = sorted(category_revenue.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "limit": limit,
            "categories": [
                {"name": cat, "revenue": round(revenue, 2)}
                for cat, revenue in sorted_cats[:limit]
            ]
        }
    finally:
        db.close()


@router.get("/revenue-trends")
async def get_revenue_trends(days: int = Query(30, ge=1, le=365)):
    """Get revenue trend over time"""
    db = SessionLocal()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        deals = DatabaseManager.get_posted_deals_by_date(db, start_date, datetime.utcnow())
        
        # Group by day
        daily_revenue = {}
        for deal in deals:
            day = deal.posted_at.date().isoformat()
            analytics = DatabaseManager.get_analytics_by_deal(db, deal.asin)
            if analytics:
                if day not in daily_revenue:
                    daily_revenue[day] = 0
                daily_revenue[day] += analytics.revenue_amount
        
        # Sort by date
        sorted_days = sorted(daily_revenue.items())
        
        return {
            "period_days": days,
            "daily_revenue": [
                {"date": day, "revenue": round(revenue, 2)}
                for day, revenue in sorted_days
            ],
            "total_revenue": round(sum(r for _, r in sorted_days), 2)
        }
    finally:
        db.close()


@router.get("/performance")
async def get_performance_metrics(days: int = Query(30, ge=1, le=365)):
    """Get comprehensive performance metrics"""
    db = SessionLocal()
    try:
        performance = AnalyticsTracker.get_deal_performance(db, days=days)
        
        return {
            **performance,
            "average_revenue_per_deal": round(
                performance["total_revenue"] / max(performance["total_deals"], 1), 2
            )
        }
    finally:
        db.close()
