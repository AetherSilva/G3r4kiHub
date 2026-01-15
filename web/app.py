"""
FastAPI Admin Panel for G3r4kiHub
Provides analytics dashboard, deal management, and system monitoring
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import logging
import os

from config import settings
from internal.models import create_tables
from internal.db_manager import DatabaseManager
from services.scheduler import get_scheduler

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="G3r4kiHub Admin Panel",
    description="Analytics and management dashboard for Telegram Amazon affiliate bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Startup/Shutdown ============

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting G3r4kiHub Admin Panel")
    try:
        create_tables()
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down G3r4kiHub Admin Panel")
    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            scheduler.stop()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# ============ Pydantic Models ============

class DealResponse(BaseModel):
    id: int
    asin: str
    title: str
    price: float
    original_price: Optional[float]
    discount_percent: Optional[float]
    posted_at: datetime
    telegram_message_id: Optional[int]
    category: Optional[str]

    class Config:
        from_attributes = True


class AnalyticsResponse(BaseModel):
    total_deals: int
    today_deals: int
    total_revenue: float
    average_ctr: float
    timestamp: str


class DashboardStats(BaseModel):
    total_deals_posted: int
    today_deals: int
    total_revenue: float
    average_ctr: float
    top_deals: List[dict]
    recent_logs: List[dict]
    scheduler_status: bool
    last_update: str


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    database: bool
    scheduler: bool
    telegram_bot: bool


# ============ Health Check ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    from internal.models import SessionLocal
    
    # Check database
    db_ok = True
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except:
        db_ok = False

    # Check scheduler
    scheduler = get_scheduler()
    scheduler_ok = scheduler.is_running

    # Check telegram bot
    from services.telegram_bot import get_bot_manager
    bot_manager = get_bot_manager()
    telegram_ok = await bot_manager.health_check() if bot_manager.bot else False

    return HealthResponse(
        status="healthy" if all([db_ok, scheduler_ok, telegram_ok]) else "degraded",
        timestamp=datetime.utcnow().isoformat(),
        database=db_ok,
        scheduler=scheduler_ok,
        telegram_bot=telegram_ok
    )


# ============ Dashboard Endpoints ============

@app.get("/api/dashboard", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        # Get basic stats
        stats = DatabaseManager.get_dashboard_stats(db)
        
        # Get top deals
        top_deals_query = DatabaseManager.get_top_performing_deals(db, limit=5)
        top_deals = []
        for deal, analytics in top_deals_query:
            top_deals.append({
                "asin": deal.asin,
                "title": deal.title[:60],
                "revenue": analytics.revenue_amount,
                "clicks": analytics.click_count,
                "conversions": analytics.conversion_count
            })
        
        # Get recent logs
        logs = DatabaseManager.get_logs(db, limit=5)
        recent_logs = [
            {
                "action": log.action,
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
        
        # Scheduler status
        scheduler = get_scheduler()
        
        return DashboardStats(
            total_deals_posted=stats.get("total_deals", 0),
            today_deals=stats.get("today_deals", 0),
            total_revenue=stats.get("total_revenue", 0.0),
            average_ctr=stats.get("average_ctr", 0.0),
            top_deals=top_deals,
            recent_logs=recent_logs,
            scheduler_status=scheduler.is_running,
            last_update=datetime.utcnow().isoformat()
        )
    finally:
        db.close()


# ============ Deals Endpoints ============

@app.get("/api/deals", response_model=List[DealResponse])
async def get_deals(limit: int = 50, offset: int = 0):
    """Get all posted deals"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        deals = DatabaseManager.get_all_posted_deals(db, limit=limit + offset)
        return deals[offset:offset + limit]
    finally:
        db.close()


@app.get("/api/deals/{asin}", response_model=DealResponse)
async def get_deal(asin: str):
    """Get specific deal by ASIN"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        deal = DatabaseManager.get_posted_deal(db, asin)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        return deal
    finally:
        db.close()


@app.get("/api/deals/date-range")
async def get_deals_by_date(start_date: str, end_date: str):
    """Get deals within date range"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        deals = DatabaseManager.get_posted_deals_by_date(db, start, end)
        return {
            "count": len(deals),
            "deals": deals,
            "date_range": f"{start.date()} to {end.date()}"
        }
    finally:
        db.close()


# ============ Analytics Endpoints ============

@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """Get current analytics"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        return AnalyticsResponse(
            **DatabaseManager.get_dashboard_stats(db)
        )
    finally:
        db.close()


@app.get("/api/analytics/performance")
async def get_performance(days: int = 30):
    """Get deal performance metrics"""
    from internal.models import SessionLocal
    from services.scheduler import AnalyticsTracker
    
    db = SessionLocal()
    try:
        return AnalyticsTracker.get_deal_performance(db, days=days)
    finally:
        db.close()


@app.get("/api/analytics/top-deals")
async def get_top_deals(limit: int = 10):
    """Get top performing deals"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        results = DatabaseManager.get_top_performing_deals(db, limit=limit)
        return {
            "count": len(results),
            "deals": [
                {
                    "asin": deal.asin,
                    "title": deal.title,
                    "price": deal.price,
                    "revenue": analytics.revenue_amount,
                    "conversions": analytics.conversion_count,
                    "ctr": analytics.ctr
                }
                for deal, analytics in results
            ]
        }
    finally:
        db.close()


# ============ Logs Endpoints ============

@app.get("/api/logs")
async def get_logs(action: Optional[str] = None, limit: int = 100):
    """Get system logs"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        logs = DatabaseManager.get_logs(db, action_filter=action, limit=limit)
        return {
            "count": len(logs),
            "logs": [
                {
                    "action": log.action,
                    "status": log.status,
                    "message": log.message,
                    "error_details": log.error_details,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs
            ]
        }
    finally:
        db.close()


@app.get("/api/logs/errors")
async def get_error_logs(hours: int = 24):
    """Get error logs"""
    from internal.models import SessionLocal
    
    db = SessionLocal()
    try:
        errors = DatabaseManager.get_error_logs(db, hours=hours)
        return {
            "count": len(errors),
            "errors": [
                {
                    "action": log.action,
                    "message": log.message,
                    "error_details": log.error_details,
                    "created_at": log.created_at.isoformat()
                }
                for log in errors
            ]
        }
    finally:
        db.close()


# ============ Scheduler Endpoints ============

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status"""
    scheduler = get_scheduler()
    jobs = scheduler.list_jobs()
    
    return {
        "is_running": scheduler.is_running,
        "jobs_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in jobs
        ]
    }


@app.post("/api/scheduler/start")
async def start_scheduler():
    """Start scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return {"status": "started", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/scheduler/stop")
async def stop_scheduler():
    """Stop scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"status": "stopped", "timestamp": datetime.utcnow().isoformat()}


# ============ Root/Dashboard HTML ============

@app.get("/", response_class=HTMLResponse)
async def get_dashboard_html():
    """Serve admin dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>G3r4kiHub Admin Dashboard</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            header {
                background: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 10px;
            }
            .subtitle {
                color: #666;
                font-size: 14px;
            }
            .dashboard-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .stat-label {
                color: #999;
                font-size: 12px;
                text-transform: uppercase;
                margin-bottom: 8px;
            }
            .stat-value {
                font-size: 32px;
                font-weight: bold;
                color: #667eea;
            }
            .stat-unit {
                font-size: 14px;
                color: #999;
                margin-left: 5px;
            }
            .main-grid {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 20px;
            }
            @media (max-width: 768px) {
                .main-grid {
                    grid-template-columns: 1fr;
                }
            }
            .card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            }
            .card h2 {
                color: #333;
                margin-bottom: 15px;
                font-size: 18px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th {
                text-align: left;
                padding: 10px;
                border-bottom: 2px solid #eee;
                color: #666;
                font-weight: 600;
                font-size: 12px;
                text-transform: uppercase;
            }
            td {
                padding: 10px;
                border-bottom: 1px solid #eee;
                color: #333;
            }
            .status {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }
            .status.success {
                background: #d4edda;
                color: #155724;
            }
            .status.error {
                background: #f8d7da;
                color: #721c24;
            }
            .footer {
                text-align: center;
                color: white;
                margin-top: 40px;
                font-size: 12px;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: white;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>🤖 G3r4kiHub Admin Dashboard</h1>
                <p class="subtitle">Telegram Amazon Affiliate Bot Analytics & Management</p>
            </header>

            <div id="dashboard" class="loading">Loading dashboard...</div>

            <div class="footer">
                <p>G3r4kiHub v1.0.0 | Last updated: <span id="timestamp"></span></p>
            </div>
        </div>

        <script>
            async function loadDashboard() {
                try {
                    const response = await fetch('/api/dashboard');
                    const data = await response.json();
                    
                    const dashboardHtml = `
                        <div class="dashboard-grid">
                            <div class="stat-card">
                                <div class="stat-label">Total Deals Posted</div>
                                <div class="stat-value">${data.total_deals_posted}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Today's Deals</div>
                                <div class="stat-value">${data.today_deals}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Total Revenue (30d)</div>
                                <div class="stat-value">$<span>${data.total_revenue.toFixed(2)}</span></div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">Average CTR</div>
                                <div class="stat-value">${data.average_ctr.toFixed(2)}<span class="stat-unit">%</span></div>
                            </div>
                        </div>

                        <div class="main-grid">
                            <div class="card">
                                <h2>📊 Top Performing Deals</h2>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Title</th>
                                            <th>Revenue</th>
                                            <th>Clicks</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.top_deals.map(deal => `
                                            <tr>
                                                <td>${deal.title.substring(0, 40)}</td>
                                                <td>$${deal.revenue.toFixed(2)}</td>
                                                <td>${deal.clicks}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>

                            <div class="card">
                                <h2>📝 Recent Logs</h2>
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Action</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.recent_logs.map(log => `
                                            <tr>
                                                <td>${log.action}</td>
                                                <td><span class="status ${log.status}">${log.status}</span></td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    `;
                    
                    document.getElementById('dashboard').innerHTML = dashboardHtml;
                    document.getElementById('timestamp').textContent = new Date().toLocaleString();
                } catch (error) {
                    document.getElementById('dashboard').innerHTML = '<div style="color: red;">Error loading dashboard</div>';
                    console.error('Error:', error);
                }
            }

            // Load dashboard on page load and refresh every 30 seconds
            loadDashboard();
            setInterval(loadDashboard, 30000);
        </script>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
