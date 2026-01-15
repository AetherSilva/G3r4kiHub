"""
API Routes for deals management
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from internal.models import SessionLocal
from internal.db_manager import DatabaseManager
from internal.deal_fetcher import DealFetcher

router = APIRouter(prefix="/api/deals", tags=["deals"])


class DealCreate(BaseModel):
    asin: str
    title: str
    price: float
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None
    image_url: Optional[str] = None
    affiliate_url: str
    category: Optional[str] = None


class DealUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    discount_percent: Optional[float] = None


@router.get("/")
async def list_deals(
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None
):
    """List all deals with pagination"""
    db = SessionLocal()
    try:
        query = db.query(DatabaseManager)
        if category:
            # Filter by category if provided
            pass
        
        deals = DatabaseManager.get_all_posted_deals(db, limit=limit + offset)
        return {
            "total": len(deals),
            "limit": limit,
            "offset": offset,
            "deals": deals[offset:offset + limit]
        }
    finally:
        db.close()


@router.get("/{asin}")
async def get_deal(asin: str):
    """Get deal by ASIN"""
    db = SessionLocal()
    try:
        deal = DatabaseManager.get_posted_deal(db, asin)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        return deal
    finally:
        db.close()


@router.post("/")
async def create_deal(deal: DealCreate):
    """Create new deal (manual entry)"""
    db = SessionLocal()
    try:
        # Check if deal already exists
        if DatabaseManager.is_deal_posted(db, deal.asin):
            raise HTTPException(status_code=409, detail="Deal already exists")
        
        deal_data = deal.dict()
        deal_data["posted_at"] = datetime.utcnow()
        
        new_deal = DatabaseManager.add_posted_deal(db, deal_data)
        
        DatabaseManager.log_action(
            db,
            action="create_deal",
            status="success",
            message=f"Created deal: {deal.title}"
        )
        
        return new_deal
    finally:
        db.close()


@router.put("/{asin}")
async def update_deal(asin: str, deal_update: DealUpdate):
    """Update deal information"""
    db = SessionLocal()
    try:
        deal = DatabaseManager.get_posted_deal(db, asin)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        update_data = deal_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(deal, key, value)
        
        db.commit()
        
        DatabaseManager.log_action(
            db,
            action="update_deal",
            status="success",
            message=f"Updated deal: {asin}"
        )
        
        return deal
    finally:
        db.close()


@router.delete("/{asin}")
async def delete_deal(asin: str):
    """Delete a deal"""
    db = SessionLocal()
    try:
        deal = DatabaseManager.get_posted_deal(db, asin)
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")
        
        db.delete(deal)
        db.commit()
        
        DatabaseManager.log_action(
            db,
            action="delete_deal",
            status="success",
            message=f"Deleted deal: {asin}"
        )
        
        return {"status": "deleted", "asin": asin}
    finally:
        db.close()


@router.get("/fetch/{asin}")
async def fetch_and_save_deal(asin: str):
    """Fetch deal from Amazon API and save"""
    db = SessionLocal()
    try:
        fetcher = DealFetcher()
        
        # Check if already posted
        if DatabaseManager.is_deal_posted(db, asin):
            raise HTTPException(status_code=409, detail="Deal already posted")
        
        # Fetch from Amazon
        deal = fetcher.fetch_deal_by_asin(db, asin)
        if not deal:
            raise HTTPException(status_code=404, detail="Failed to fetch deal from Amazon")
        
        # Save to database
        deal["posted_at"] = datetime.utcnow()
        saved_deal = DatabaseManager.add_posted_deal(db, deal)
        
        DatabaseManager.log_action(
            db,
            action="fetch_deal",
            status="success",
            message=f"Fetched and saved: {deal.get('title')}"
        )
        
        return saved_deal
    finally:
        db.close()
