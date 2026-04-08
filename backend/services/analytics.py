"""
MakFleet Prototype - Analytics Service
Provides analytics and statistics for the dashboard
"""
from sqlalchemy import func, extract
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any
from ..models import Telemetry, Event, Vehicle, Driver


class AnalyticsService:
    """Service for generating analytics and statistics"""

    @staticmethod
    def get_vehicle_telemetry_summary(db: Session, vehicle_id: int, 
                                       hours: int = 24) -> Dict[str, Any]:
        """
        Get telemetry summary for a vehicle
        
        Args:
            db: Database session
            vehicle_id: Vehicle ID
            hours: Number of hours to look back
            
        Returns:
            Dictionary with telemetry statistics
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        result = db.query(
            func.count(Telemetry.telemetry_id).label('total_readings'),
            func.avg(Telemetry.speed).label('avg_speed'),
            func.max(Telemetry.speed).label('max_speed'),
            func.min(Telemetry.speed).label('min_speed'),
            func.avg(Telemetry.acceleration).label('avg_acceleration')
        ).filter(
            Telemetry.vehicle_id == vehicle_id,
            Telemetry.timestamp >= since
        ).first()
        
        return {
            "total_readings": result.total_readings or 0,
            "avg_speed": round(result.avg_speed or 0, 2),
            "max_speed": result.max_speed or 0,
            "min_speed": result.min_speed or 0,
            "avg_acceleration": round(result.avg_acceleration or 0, 2)
        }

    @staticmethod
    def get_event_summary(db: Session, hours: int = 24) -> Dict[str, Any]:
        """
        Get event summary for all vehicles
        
        Args:
            db: Database session
            hours: Number of hours to look back
            
        Returns:
            Dictionary with event counts
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get counts by event type
        event_counts = db.query(
            Event.event_type,
            func.count(Event.event_id).label('count')
        ).filter(
            Event.timestamp >= since
        ).group_by(Event.event_type).all()
        
        result = {
            "HARSH_BRAKING": 0,
            "RAPID_ACCELERATION": 0,
            "OVERSPEED": 0,
            "IDLING": 0,
            "total": 0
        }
        
        for event_type, count in event_counts:
            if event_type in result:
                result[event_type] = count
                result["total"] += count
        
        return result

    @staticmethod
    def get_driver_risk_scores(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """
        Calculate risk scores for all drivers
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            List of driver risk scores
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Weight factors for each event type
        weights = {
            "HARSH_BRAKING": 3,
            "OVERSPEED": 2,
            "RAPID_ACCELERATION": 1,
            "IDLING": 0.5
        }
        
        # Get all events in the time period
        events = db.query(Event).filter(Event.timestamp >= since).all()
        
        # Calculate risk scores per driver
        driver_scores = {}
        
        for event in events:
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == event.vehicle_id).first()
            if not vehicle or not vehicle.driver_id:
                continue
                
            driver_id = vehicle.driver_id
            
            if driver_id not in driver_scores:
                driver_scores[driver_id] = {
                    "driver_id": driver_id,
                    "harsh_braking": 0,
                    "overspeed": 0,
                    "rapid_acceleration": 0,
                    "idling": 0,
                    "total_score": 0
                }
            
            weight = weights.get(event.event_type, 0)
            driver_scores[driver_id]["total_score"] += weight
            
            if event.event_type == "HARSH_BRAKING":
                driver_scores[driver_id]["harsh_braking"] += 1
            elif event.event_type == "OVERSPEED":
                driver_scores[driver_id]["overspeed"] += 1
            elif event.event_type == "RAPID_ACCELERATION":
                driver_scores[driver_id]["rapid_acceleration"] += 1
            elif event.event_type == "IDLING":
                driver_scores[driver_id]["idling"] += 1
        
        # Add driver names
        result = []
        for driver_id, scores in driver_scores.items():
            driver = db.query(Driver).filter(Driver.driver_id == driver_id).first()
            if driver:
                scores["driver_name"] = driver.name
                scores["plate_number"] = db.query(Vehicle).filter(
                    Vehicle.driver_id == driver_id
                ).first().plate_number if db.query(Vehicle).filter(
                    Vehicle.driver_id == driver_id
                ).first() else "N/A"
            result.append(scores)
        
        # Sort by risk score descending
        result.sort(key=lambda x: x["total_score"], reverse=True)
        
        return result

    @staticmethod
    def get_daily_trips(db: Session, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily trip counts
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            List of daily trip counts
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        daily_counts = db.query(
            extract('day', Telemetry.timestamp).label('day'),
            func.count(func.distinct(Telemetry.vehicle_id)).label('vehicles'),
            func.count(Telemetry.telemetry_id).label('readings')
        ).filter(
            Telemetry.timestamp >= since
        ).group_by(
            extract('day', Telemetry.timestamp)
        ).all()
        
        result = []
        for day, vehicles, readings in daily_counts:
            result.append({
                "day": int(day),
                "active_vehicles": vehicles,
                "total_readings": readings
            })
        
        return result

    @staticmethod
    def get_dangerous_zones(db: Session, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get dangerous zones based on event density
        
        Args:
            db: Database session
            hours: Number of hours to look back
            
        Returns:
            List of dangerous zones with event counts
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Group events by approximate location (rounded to 4 decimal places ~ 11m)
        zones = db.query(
            func.round(Event.latitude, 4).label('lat'),
            func.round(Event.longitude, 4).label('lng'),
            Event.event_type,
            func.count(Event.event_id).label('count')
        ).filter(
            Event.timestamp >= since
        ).group_by(
            func.round(Event.latitude, 4),
            func.round(Event.longitude, 4),
            Event.event_type
        ).all()
        
        # Aggregate by location
        zone_dict = {}
        for lat, lng, event_type, count in zones:
            key = f"{lat},{lng}"
            if key not in zone_dict:
                zone_dict[key] = {
                    "latitude": lat,
                    "longitude": lng,
                    "events": 0,
                    "types": {}
                }
            zone_dict[key]["events"] += count
            zone_dict[key]["types"][event_type] = count
        
        # Sort by event count and return top 10
        result = sorted(zone_dict.values(), key=lambda x: x["events"], reverse=True)[:10]
        
        return result

    @staticmethod
    def get_recent_telemetry(db: Session, vehicle_id: int = None, 
                            limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent telemetry readings
        
        Args:
            db: Database session
            vehicle_id: Optional vehicle ID filter
            limit: Maximum number of records
            
        Returns:
            List of telemetry records
        """
        query = db.query(Telemetry).order_by(Telemetry.timestamp.desc())
        
        if vehicle_id:
            query = query.filter(Telemetry.vehicle_id == vehicle_id)
        
        telemetry = query.limit(limit).all()
        
        result = []
        for t in telemetry:
            vehicle = db.query(Vehicle).filter(Vehicle.vehicle_id == t.vehicle_id).first()
            driver = None
            if vehicle and vehicle.driver_id:
                driver = db.query(Driver).filter(Driver.driver_id == vehicle.driver_id).first()
            
            result.append({
                "telemetry_id": t.telemetry_id,
                "vehicle_id": t.vehicle_id,
                "plate_number": vehicle.plate_number if vehicle else "Unknown",
                "driver_name": driver.name if driver else "Unknown",
                "latitude": t.latitude,
                "longitude": t.longitude,
                "speed": t.speed,
                "acceleration": t.acceleration,
                "engine_temp": t.engine_temp,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            })
        
        return result
