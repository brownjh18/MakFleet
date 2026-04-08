"""
MakFleet Prototype - Event Routes
API endpoints for event retrieval and analytics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from backend.models import Event, Vehicle, Driver
from ..services.analytics import AnalyticsService


router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/")
def get_events(
    vehicle_id: Optional[int] = None,
    event_type: Optional[str] = None,
    hours: int = 24,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get events with optional filters
    
    Args:
        vehicle_id: Filter by vehicle ID
        event_type: Filter by event type (HARSH_BRAKING, OVERSPEED, etc.)
        hours: Number of hours to look back
        limit: Maximum number of records
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    
    query = db.query(Event).filter(Event.timestamp >= since)
    
    if vehicle_id:
        query = query.filter(Event.vehicle_id == vehicle_id)
    
    if event_type:
        query = query.filter(Event.event_type == event_type)
    
    events = query.order_by(Event.timestamp.desc()).limit(limit).all()
    
    result = []
    for event in events:
        vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == event.vehicle_id).first()
        driver = None
        if vehicle and vehicle.driver_id:
            driver = db.query(Driver).filter(Driver.driver_id == vehicle.driver_id).first()
        
        result.append({
            "event_id": event.event_id,
            "vehicle_id": event.vehicle_id,
            "plate_number": vehicle.plate_number if vehicle else "Unknown",
            "driver_name": driver.name if driver else "Unknown",
            "event_type": event.event_type,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "speed": event.speed,
            "acceleration": event.acceleration,
            "severity": event.severity,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None
        })
    
    return result


@router.get("/summary")
def get_event_summary(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get event summary statistics
    
    Args:
        hours: Number of hours to look back
    """
    return AnalyticsService.get_event_summary(db, hours)


@router.get("/dangerous-zones")
def get_dangerous_zones(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """
    Get dangerous zones based on event density
    
    Args:
        hours: Number of hours to look back
    """
    return AnalyticsService.get_dangerous_zones(db, hours)


@router.get("/driver-risk")
def get_driver_risk_scores(
    days: int = 7,
    db: Session = Depends(get_db)
):
    """
    Get risk scores for all drivers
    
    Args:
        days: Number of days to look back
    """
    return AnalyticsService.get_driver_risk_scores(db, days)
