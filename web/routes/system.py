"""
API Routes for system management and logs
"""

from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional

from internal.models import SessionLocal
from internal.db_manager import DatabaseManager
from services.scheduler import get_scheduler

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/logs")
async def get_system_logs(
    action: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0)
):
    """Get system logs with filtering"""
    db = SessionLocal()
    try:
        logs = DatabaseManager.get_logs(db, action_filter=action, limit=limit + offset)
        
        # Filter by status if provided
        if status:
            logs = [log for log in logs if log.status == status]
        
        return {
            "total": len(logs),
            "limit": limit,
            "offset": offset,
            "logs": [
                {
                    "id": log.id,
                    "action": log.action,
                    "status": log.status,
                    "message": log.message,
                    "error_details": log.error_details,
                    "created_at": log.created_at.isoformat()
                }
                for log in logs[offset:offset + limit]
            ]
        }
    finally:
        db.close()


@router.get("/logs/errors")
async def get_error_logs(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(50, le=500)
):
    """Get recent error logs"""
    db = SessionLocal()
    try:
        errors = DatabaseManager.get_error_logs(db, hours=hours, limit=limit)
        
        return {
            "period_hours": hours,
            "count": len(errors),
            "errors": [
                {
                    "id": log.id,
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


@router.get("/logs/summary")
async def get_logs_summary(hours: int = Query(24, ge=1, le=720)):
    """Get logs summary for period"""
    db = SessionLocal()
    try:
        logs = DatabaseManager.get_logs(db, limit=1000)
        
        # Count by status
        status_counts = {"success": 0, "error": 0, "pending": 0}
        action_counts = {}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        for log in logs:
            if log.created_at >= cutoff_time:
                status_counts[log.status] = status_counts.get(log.status, 0) + 1
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        return {
            "period_hours": hours,
            "status_summary": status_counts,
            "action_summary": action_counts,
            "total_logs": sum(status_counts.values())
        }
    finally:
        db.close()


@router.get("/scheduler/jobs")
async def get_scheduler_jobs():
    """Get scheduled jobs info"""
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
                "trigger": str(job.trigger),
                "max_instances": job.max_instances
            }
            for job in jobs
        ]
    }


@router.post("/scheduler/start")
async def start_scheduler():
    """Start the scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    
    return {
        "status": "started",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
    
    return {
        "status": "stopped",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/info")
async def get_system_info():
    """Get system information"""
    import sys
    import platform
    
    scheduler = get_scheduler()
    db = SessionLocal()
    
    try:
        # Get database stats
        stats = DatabaseManager.get_dashboard_stats(db)
        
        return {
            "system": {
                "python_version": sys.version,
                "platform": platform.platform(),
                "processor": platform.processor()
            },
            "application": {
                "name": "G3r4kiHub",
                "version": "1.0.0",
                "status": "running"
            },
            "scheduler": {
                "is_running": scheduler.is_running,
                "jobs_count": len(scheduler.list_jobs())
            },
            "database": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    finally:
        db.close()
