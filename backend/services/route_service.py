"""
MakFleet Route and Trip Management Service
Handles route tracking, trip management, and route analytics.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TripStatus(str, Enum):
    """Trip status enumeration"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MaintenanceStatus(str, Enum):
    """Maintenance status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


@dataclass
class Route:
    """Route data structure"""
    route_id: Optional[int]
    name: str
    description: Optional[str]
    start_location_id: Optional[int]
    end_location_id: Optional[int]
    distance_km: Optional[float]
    estimated_duration_min: Optional[float]
    is_common_route: bool = False
    usage_count: int = 0
    safety_score: float = 0.8


@dataclass
class Trip:
    """Trip data structure"""
    trip_id: Optional[int]
    vehicle_id: int
    driver_id: int
    route_id: Optional[int]
    start_time: datetime
    end_time: Optional[datetime]
    start_location_id: Optional[int]
    end_location_id: Optional[int]
    distance_km: Optional[float]
    duration_min: Optional[float]
    avg_speed: Optional[float]
    max_speed: Optional[float]
    status: str = "in_progress"


@dataclass
class DriverPerformance:
    """Driver performance data structure"""
    performance_id: Optional[int]
    driver_id: int
    date: datetime
    total_trips: int = 0
    total_distance_km: float = 0.0
    total_duration_min: float = 0.0
    avg_speed: Optional[float] = None
    max_speed: Optional[float] = None
    harsh_braking_count: int = 0
    overspeed_count: int = 0
    rapid_acceleration_count: int = 0
    risk_score: float = 0.0
    safety_score: float = 1.0
    efficiency_score: float = 0.8
    incidents_count: int = 0


@dataclass
class VehicleMaintenance:
    """Vehicle maintenance data structure"""
    maintenance_id: Optional[int]
    vehicle_id: int
    maintenance_type: str
    description: Optional[str]
    scheduled_date: Optional[datetime]
    completed_date: Optional[datetime]
    cost: Optional[float]
    mileage_at_service: Optional[float]
    next_service_due: Optional[datetime]
    next_service_mileage: Optional[float]
    service_provider: Optional[str]
    status: str = "scheduled"
    notes: Optional[str] = None


class RouteService:
    """
    Service for route management and tracking.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize route service.
        
        Args:
            db_session: Database session for data persistence
        """
        self.db_session = db_session
    
    def create_route(
        self,
        name: str,
        start_location_id: int,
        end_location_id: int,
        description: Optional[str] = None,
        distance_km: Optional[float] = None,
        estimated_duration_min: Optional[float] = None
    ) -> Optional[Route]:
        """
        Create a new route.
        
        Args:
            name: Route name
            start_location_id: Starting location ID
            end_location_id: Ending location ID
            description: Optional description
            distance_km: Distance in kilometers
            estimated_duration_min: Estimated duration in minutes
            
        Returns:
            Created Route object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO routes (
                    name, description, start_location_id, end_location_id,
                    distance_km, estimated_duration_min, is_common_route
                ) VALUES (
                    :name, :description, :start_location_id, :end_location_id,
                    :distance_km, :estimated_duration_min, FALSE
                ) RETURNING route_id, name, description, start_location_id,
                           end_location_id, distance_km, estimated_duration_min,
                           is_common_route, usage_count, safety_score
            """)
            
            result = self.db_session.execute(query, {
                'name': name,
                'description': description,
                'start_location_id': start_location_id,
                'end_location_id': end_location_id,
                'distance_km': distance_km,
                'estimated_duration_min': estimated_duration_min
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            return Route(
                route_id=row.route_id,
                name=row.name,
                description=row.description,
                start_location_id=row.start_location_id,
                end_location_id=row.end_location_id,
                distance_km=row.distance_km,
                estimated_duration_min=row.estimated_duration_min,
                is_common_route=row.is_common_route,
                usage_count=row.usage_count,
                safety_score=row.safety_score
            )
            
        except Exception as e:
            logger.error(f"Failed to create route: {e}")
            self.db_session.rollback()
            return None
    
    def get_route_by_id(self, route_id: int) -> Optional[Route]:
        """
        Get route by ID.
        
        Args:
            route_id: Route ID
            
        Returns:
            Route object or None if not found
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT route_id, name, description, start_location_id,
                       end_location_id, distance_km, estimated_duration_min,
                       is_common_route, usage_count, safety_score
                FROM routes
                WHERE route_id = :route_id
            """)
            
            result = self.db_session.execute(query, {'route_id': route_id})
            row = result.fetchone()
            
            if row:
                return Route(
                    route_id=row.route_id,
                    name=row.name,
                    description=row.description,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    estimated_duration_min=row.estimated_duration_min,
                    is_common_route=row.is_common_route,
                    usage_count=row.usage_count,
                    safety_score=row.safety_score
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get route: {e}")
            return None
    
    def get_common_routes(self) -> List[Route]:
        """
        Get all common routes.
        
        Returns:
            List of Route objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT route_id, name, description, start_location_id,
                       end_location_id, distance_km, estimated_duration_min,
                       is_common_route, usage_count, safety_score
                FROM routes
                WHERE is_common_route = TRUE
                ORDER BY usage_count DESC
            """)
            
            result = self.db_session.execute(query)
            routes = []
            for row in result:
                routes.append(Route(
                    route_id=row.route_id,
                    name=row.name,
                    description=row.description,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    estimated_duration_min=row.estimated_duration_min,
                    is_common_route=row.is_common_route,
                    usage_count=row.usage_count,
                    safety_score=row.safety_score
                ))
            
            return routes
            
        except Exception as e:
            logger.error(f"Failed to get common routes: {e}")
            return []
    
    def increment_route_usage(self, route_id: int) -> bool:
        """
        Increment route usage count.
        
        Args:
            route_id: Route ID
            
        Returns:
            True if successful, False otherwise
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return False
        
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE routes
                SET usage_count = usage_count + 1
                WHERE route_id = :route_id
            """)
            
            self.db_session.execute(query, {'route_id': route_id})
            self.db_session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to increment route usage: {e}")
            self.db_session.rollback()
            return False
    
    def get_route_safety_analysis(self, route_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Analyze safety for a specific route.
        
        Args:
            route_id: Route ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with safety analysis
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return {}
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT 
                    COUNT(DISTINCT t.trip_id) AS total_trips,
                    COUNT(e.event_id) AS total_events,
                    COUNT(CASE WHEN e.event_type = 'harsh_braking' THEN 1 END) AS harsh_braking_count,
                    COUNT(CASE WHEN e.event_type = 'overspeed' THEN 1 END) AS overspeed_count,
                    COUNT(CASE WHEN e.event_type = 'rapid_acceleration' THEN 1 END) AS rapid_acceleration_count,
                    COUNT(CASE WHEN e.severity = 'high' THEN 1 END) AS high_severity_events,
                    AVG(t.avg_speed) AS avg_speed,
                    MAX(t.max_speed) AS max_speed
                FROM trips t
                LEFT JOIN events e ON t.vehicle_id = e.vehicle_id 
                    AND e.timestamp >= t.start_time 
                    AND e.timestamp <= COALESCE(t.end_time, NOW())
                WHERE t.route_id = :route_id
                    AND t.start_time >= :start_date
                    AND t.status = 'completed'
            """)
            
            result = self.db_session.execute(query, {
                'route_id': route_id,
                'start_date': datetime.utcnow() - timedelta(days=days)
            })
            
            row = result.fetchone()
            
            if row:
                total_events = row.total_events or 0
                total_trips = row.total_trips or 0
                
                return {
                    'route_id': route_id,
                    'analysis_period_days': days,
                    'total_trips': total_trips,
                    'total_events': total_events,
                    'events_per_trip': total_events / max(total_trips, 1),
                    'harsh_braking_count': row.harsh_braking_count or 0,
                    'overspeed_count': row.overspeed_count or 0,
                    'rapid_acceleration_count': row.rapid_acceleration_count or 0,
                    'high_severity_events': row.high_severity_events or 0,
                    'avg_speed': row.avg_speed,
                    'max_speed': row.max_speed,
                    'safety_score': max(0, 1.0 - (total_events / max(total_trips * 10, 1)))
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to analyze route safety: {e}")
            return {}


class TripService:
    """
    Service for trip management and tracking.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize trip service.
        
        Args:
            db_session: Database session for data persistence
        """
        self.db_session = db_session
    
    def start_trip(
        self,
        vehicle_id: int,
        driver_id: int,
        start_location_id: int,
        route_id: Optional[int] = None
    ) -> Optional[Trip]:
        """
        Start a new trip.
        
        Args:
            vehicle_id: Vehicle ID
            driver_id: Driver ID
            start_location_id: Starting location ID
            route_id: Optional route ID
            
        Returns:
            Created Trip object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO trips (
                    vehicle_id, driver_id, route_id, start_time,
                    start_location_id, status
                ) VALUES (
                    :vehicle_id, :driver_id, :route_id, :start_time,
                    :start_location_id, 'in_progress'
                ) RETURNING trip_id, vehicle_id, driver_id, route_id,
                           start_time, end_time, start_location_id,
                           end_location_id, distance_km, duration_min,
                           avg_speed, max_speed, status
            """)
            
            result = self.db_session.execute(query, {
                'vehicle_id': vehicle_id,
                'driver_id': driver_id,
                'route_id': route_id,
                'start_time': datetime.utcnow(),
                'start_location_id': start_location_id
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            return Trip(
                trip_id=row.trip_id,
                vehicle_id=row.vehicle_id,
                driver_id=row.driver_id,
                route_id=row.route_id,
                start_time=row.start_time,
                end_time=row.end_time,
                start_location_id=row.start_location_id,
                end_location_id=row.end_location_id,
                distance_km=row.distance_km,
                duration_min=row.duration_min,
                avg_speed=row.avg_speed,
                max_speed=row.max_speed,
                status=row.status
            )
            
        except Exception as e:
            logger.error(f"Failed to start trip: {e}")
            self.db_session.rollback()
            return None
    
    def end_trip(
        self,
        trip_id: int,
        end_location_id: int,
        distance_km: float,
        duration_min: float,
        avg_speed: float,
        max_speed: float
    ) -> Optional[Trip]:
        """
        End a trip.
        
        Args:
            trip_id: Trip ID
            end_location_id: Ending location ID
            distance_km: Distance traveled in km
            duration_min: Duration in minutes
            avg_speed: Average speed
            max_speed: Maximum speed
            
        Returns:
            Updated Trip object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE trips
                SET end_time = :end_time,
                    end_location_id = :end_location_id,
                    distance_km = :distance_km,
                    duration_min = :duration_min,
                    avg_speed = :avg_speed,
                    max_speed = :max_speed,
                    status = 'completed'
                WHERE trip_id = :trip_id AND status = 'in_progress'
                RETURNING trip_id, vehicle_id, driver_id, route_id,
                          start_time, end_time, start_location_id,
                          end_location_id, distance_km, duration_min,
                          avg_speed, max_speed, status
            """)
            
            result = self.db_session.execute(query, {
                'trip_id': trip_id,
                'end_time': datetime.utcnow(),
                'end_location_id': end_location_id,
                'distance_km': distance_km,
                'duration_min': duration_min,
                'avg_speed': avg_speed,
                'max_speed': max_speed
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            if row:
                return Trip(
                    trip_id=row.trip_id,
                    vehicle_id=row.vehicle_id,
                    driver_id=row.driver_id,
                    route_id=row.route_id,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    duration_min=row.duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    status=row.status
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to end trip: {e}")
            self.db_session.rollback()
            return None
    
    def get_active_trips(self) -> List[Trip]:
        """
        Get all active trips.
        
        Returns:
            List of Trip objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT trip_id, vehicle_id, driver_id, route_id,
                       start_time, end_time, start_location_id,
                       end_location_id, distance_km, duration_min,
                       avg_speed, max_speed, status
                FROM active_trips
                ORDER BY start_time DESC
            """)
            
            result = self.db_session.execute(query)
            trips = []
            for row in result:
                trips.append(Trip(
                    trip_id=row.trip_id,
                    vehicle_id=row.vehicle_id,
                    driver_id=row.driver_id,
                    route_id=row.route_id,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    duration_min=row.duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    status=row.status
                ))
            
            return trips
            
        except Exception as e:
            logger.error(f"Failed to get active trips: {e}")
            return []
    
    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        """
        Get trip by ID.
        
        Args:
            trip_id: Trip ID
            
        Returns:
            Trip object or None if not found
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT trip_id, vehicle_id, driver_id, route_id,
                       start_time, end_time, start_location_id,
                       end_location_id, distance_km, duration_min,
                       avg_speed, max_speed, status
                FROM trips
                WHERE trip_id = :trip_id
            """)
            
            result = self.db_session.execute(query, {'trip_id': trip_id})
            row = result.fetchone()
            
            if row:
                return Trip(
                    trip_id=row.trip_id,
                    vehicle_id=row.vehicle_id,
                    driver_id=row.driver_id,
                    route_id=row.route_id,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    duration_min=row.duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    status=row.status
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to get trip: {e}")
            return None
    
    def get_trips_for_driver(
        self,
        driver_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Trip]:
        """
        Get trips for a specific driver.
        
        Args:
            driver_id: Driver ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of Trip objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT trip_id, vehicle_id, driver_id, route_id,
                       start_time, end_time, start_location_id,
                       end_location_id, distance_km, duration_min,
                       avg_speed, max_speed, status
                FROM trips
                WHERE driver_id = :driver_id
                    AND (:start_date IS NULL OR start_time >= :start_date)
                    AND (:end_date IS NULL OR start_time <= :end_date)
                ORDER BY start_time DESC
            """)
            
            result = self.db_session.execute(query, {
                'driver_id': driver_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            trips = []
            for row in result:
                trips.append(Trip(
                    trip_id=row.trip_id,
                    vehicle_id=row.vehicle_id,
                    driver_id=row.driver_id,
                    route_id=row.route_id,
                    start_time=row.start_time,
                    end_time=row.end_time,
                    start_location_id=row.start_location_id,
                    end_location_id=row.end_location_id,
                    distance_km=row.distance_km,
                    duration_min=row.duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    status=row.status
                ))
            
            return trips
            
        except Exception as e:
            logger.error(f"Failed to get driver trips: {e}")
            return []


class DriverPerformanceService:
    """
    Service for driver performance tracking and analytics.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize driver performance service.
        
        Args:
            db_session: Database session for data persistence
        """
        self.db_session = db_session
    
    def calculate_daily_performance(self, driver_id: int, date: datetime) -> Optional[DriverPerformance]:
        """
        Calculate and store daily performance for a driver.
        
        Args:
            driver_id: Driver ID
            date: Date to calculate performance for
            
        Returns:
            DriverPerformance object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            # Calculate performance metrics from events and trips
            query = text("""
                SELECT 
                    COUNT(DISTINCT t.trip_id) AS total_trips,
                    COALESCE(SUM(t.distance_km), 0) AS total_distance_km,
                    COALESCE(SUM(t.duration_min), 0) AS total_duration_min,
                    AVG(t.avg_speed) AS avg_speed,
                    MAX(t.max_speed) AS max_speed,
                    COUNT(CASE WHEN e.event_type = 'harsh_braking' THEN 1 END) AS harsh_braking_count,
                    COUNT(CASE WHEN e.event_type = 'overspeed' THEN 1 END) AS overspeed_count,
                    COUNT(CASE WHEN e.event_type = 'rapid_acceleration' THEN 1 END) AS rapid_acceleration_count
                FROM trips t
                LEFT JOIN events e ON t.vehicle_id = e.vehicle_id 
                    AND e.timestamp >= :start_date 
                    AND e.timestamp < :end_date
                WHERE t.driver_id = :driver_id
                    AND t.start_time >= :start_date 
                    AND t.start_time < :end_date
                    AND t.status = 'completed'
            """)
            
            result = self.db_session.execute(query, {
                'driver_id': driver_id,
                'start_date': date.replace(hour=0, minute=0, second=0, microsecond=0),
                'end_date': date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            })
            
            row = result.fetchone()
            
            if row:
                # Calculate risk and safety scores
                total_events = (row.harsh_braking_count + row.overspeed_count + row.rapid_acceleration_count)
                risk_score = min(100, total_events * 5)  # Simple risk calculation
                safety_score = max(0, 1.0 - (total_events / max(row.total_trips * 10, 1)))
                efficiency_score = min(1.0, row.total_distance_km / max(row.total_duration_min, 1) * 10)
                
                # Store performance
                perf = self.store_performance(
                    driver_id=driver_id,
                    date=date,
                    total_trips=row.total_trips,
                    total_distance_km=row.total_distance_km,
                    total_duration_min=row.total_duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    harsh_braking_count=row.harsh_braking_count,
                    overspeed_count=row.overspeed_count,
                    rapid_acceleration_count=row.rapid_acceleration_count,
                    risk_score=risk_score,
                    safety_score=safety_score,
                    efficiency_score=efficiency_score
                )
                
                return perf
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate driver performance: {e}")
            return None
    
    def store_performance(
        self,
        driver_id: int,
        date: datetime,
        total_trips: int,
        total_distance_km: float,
        total_duration_min: float,
        avg_speed: Optional[float],
        max_speed: Optional[float],
        harsh_braking_count: int,
        overspeed_count: int,
        rapid_acceleration_count: int,
        risk_score: float,
        safety_score: float,
        efficiency_score: float
    ) -> Optional[DriverPerformance]:
        """
        Store driver performance in database.
        
        Args:
            Various performance metrics
            
        Returns:
            DriverPerformance object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO driver_performance (
                    driver_id, date, total_trips, total_distance_km,
                    total_duration_min, avg_speed, max_speed,
                    harsh_braking_count, overspeed_count, rapid_acceleration_count,
                    risk_score, safety_score, efficiency_score
                ) VALUES (
                    :driver_id, :date, :total_trips, :total_distance_km,
                    :total_duration_min, :avg_speed, :max_speed,
                    :harsh_braking_count, :overspeed_count, :rapid_acceleration_count,
                    :risk_score, :safety_score, :efficiency_score
                ) ON CONFLICT (driver_id, date) DO UPDATE SET
                    total_trips = EXCLUDED.total_trips,
                    total_distance_km = EXCLUDED.total_distance_km,
                    total_duration_min = EXCLUDED.total_duration_min,
                    avg_speed = EXCLUDED.avg_speed,
                    max_speed = EXCLUDED.max_speed,
                    harsh_braking_count = EXCLUDED.harsh_braking_count,
                    overspeed_count = EXCLUDED.overspeed_count,
                    rapid_acceleration_count = EXCLUDED.rapid_acceleration_count,
                    risk_score = EXCLUDED.risk_score,
                    safety_score = EXCLUDED.safety_score,
                    efficiency_score = EXCLUDED.efficiency_score
                RETURNING performance_id, driver_id, date, total_trips,
                          total_distance_km, total_duration_min, avg_speed,
                          max_speed, harsh_braking_count, overspeed_count,
                          rapid_acceleration_count, risk_score, safety_score,
                          efficiency_score, incidents_count
            """)
            
            result = self.db_session.execute(query, {
                'driver_id': driver_id,
                'date': date,
                'total_trips': total_trips,
                'total_distance_km': total_distance_km,
                'total_duration_min': total_duration_min,
                'avg_speed': avg_speed,
                'max_speed': max_speed,
                'harsh_braking_count': harsh_braking_count,
                'overspeed_count': overspeed_count,
                'rapid_acceleration_count': rapid_acceleration_count,
                'risk_score': risk_score,
                'safety_score': safety_score,
                'efficiency_score': efficiency_score
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            if row:
                return DriverPerformance(
                    performance_id=row.performance_id,
                    driver_id=row.driver_id,
                    date=row.date,
                    total_trips=row.total_trips,
                    total_distance_km=row.total_distance_km,
                    total_duration_min=row.total_duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    harsh_braking_count=row.harsh_braking_count,
                    overspeed_count=row.overspeed_count,
                    rapid_acceleration_count=row.rapid_acceleration_count,
                    risk_score=row.risk_score,
                    safety_score=row.safety_score,
                    efficiency_score=row.efficiency_score,
                    incidents_count=row.incidents_count
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to store driver performance: {e}")
            self.db_session.rollback()
            return None
    
    def get_driver_performance_history(
        self,
        driver_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[DriverPerformance]:
        """
        Get performance history for a driver.
        
        Args:
            driver_id: Driver ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of DriverPerformance objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT performance_id, driver_id, date, total_trips,
                       total_distance_km, total_duration_min, avg_speed,
                       max_speed, harsh_braking_count, overspeed_count,
                       rapid_acceleration_count, risk_score, safety_score,
                       efficiency_score, incidents_count
                FROM driver_performance
                WHERE driver_id = :driver_id
                    AND (:start_date IS NULL OR date >= :start_date)
                    AND (:end_date IS NULL OR date <= :end_date)
                ORDER BY date DESC
            """)
            
            result = self.db_session.execute(query, {
                'driver_id': driver_id,
                'start_date': start_date,
                'end_date': end_date
            })
            
            performances = []
            for row in result:
                performances.append(DriverPerformance(
                    performance_id=row.performance_id,
                    driver_id=row.driver_id,
                    date=row.date,
                    total_trips=row.total_trips,
                    total_distance_km=row.total_distance_km,
                    total_duration_min=row.total_duration_min,
                    avg_speed=row.avg_speed,
                    max_speed=row.max_speed,
                    harsh_braking_count=row.harsh_braking_count,
                    overspeed_count=row.overspeed_count,
                    rapid_acceleration_count=row.rapid_acceleration_count,
                    risk_score=row.risk_score,
                    safety_score=row.safety_score,
                    efficiency_score=row.efficiency_score,
                    incidents_count=row.incidents_count
                ))
            
            return performances
            
        except Exception as e:
            logger.error(f"Failed to get driver performance history: {e}")
            return []
    
    def get_driver_performance_summary(self, driver_id: int) -> Dict[str, Any]:
        """
        Get summary of driver performance.
        
        Args:
            driver_id: Driver ID
            
        Returns:
            Dictionary with performance summary
        """
        performances = self.get_driver_performance_history(driver_id)
        
        if not performances:
            return {
                'driver_id': driver_id,
                'message': 'No performance data available'
            }
        
        # Calculate averages and trends
        total_trips = sum(p.total_trips for p in performances)
        total_distance = sum(p.total_distance_km for p in performances)
        avg_risk_score = sum(p.risk_score for p in performances) / len(performances)
        avg_safety_score = sum(p.safety_score for p in performances) / len(performances)
        
        # Calculate trend (last 7 days vs previous 7 days)
        recent_performances = [p for p in performances[:7]]
        previous_performances = [p for p in performances[7:14]]
        
        recent_avg_risk = sum(p.risk_score for p in recent_performances) / max(len(recent_performances), 1)
        previous_avg_risk = sum(p.risk_score for p in previous_performances) / max(len(previous_performances), 1)
        
        trend = "improving" if recent_avg_risk < previous_avg_risk else "declining"
        
        return {
            'driver_id': driver_id,
            'total_trips': total_trips,
            'total_distance_km': round(total_distance, 2),
            'avg_risk_score': round(avg_risk_score, 2),
            'avg_safety_score': round(avg_safety_score, 3),
            'trend': trend,
            'records_analyzed': len(performances)
        }


class VehicleMaintenanceService:
    """
    Service for vehicle maintenance tracking.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize vehicle maintenance service.
        
        Args:
            db_session: Database session for data persistence
        """
        self.db_session = db_session
    
    def schedule_maintenance(
        self,
        vehicle_id: int,
        maintenance_type: str,
        scheduled_date: datetime,
        description: Optional[str] = None,
        next_service_due: Optional[datetime] = None,
        next_service_mileage: Optional[float] = None,
        service_provider: Optional[str] = None
    ) -> Optional[VehicleMaintenance]:
        """
        Schedule maintenance for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            maintenance_type: Type of maintenance (routine, repair, inspection)
            scheduled_date: Scheduled maintenance date
            description: Optional description
            next_service_due: Next service due date
            next_service_mileage: Mileage at next service
            service_provider: Service provider name
            
        Returns:
            VehicleMaintenance object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO vehicle_maintenance (
                    vehicle_id, maintenance_type, scheduled_date, description,
                    next_service_due, next_service_mileage, service_provider, status
                ) VALUES (
                    :vehicle_id, :maintenance_type, :scheduled_date, :description,
                    :next_service_due, :next_service_mileage, :service_provider, 'scheduled'
                ) RETURNING maintenance_id, vehicle_id, maintenance_type,
                          description, scheduled_date, completed_date, cost,
                          mileage_at_service, next_service_due, next_service_mileage,
                          service_provider, status, notes
            """)
            
            result = self.db_session.execute(query, {
                'vehicle_id': vehicle_id,
                'maintenance_type': maintenance_type,
                'scheduled_date': scheduled_date,
                'description': description,
                'next_service_due': next_service_due,
                'next_service_mileage': next_service_mileage,
                'service_provider': service_provider
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            return VehicleMaintenance(
                maintenance_id=row.maintenance_id,
                vehicle_id=row.vehicle_id,
                maintenance_type=row.maintenance_type,
                description=row.description,
                scheduled_date=row.scheduled_date,
                completed_date=row.completed_date,
                cost=row.cost,
                mileage_at_service=row.mileage_at_service,
                next_service_due=row.next_service_due,
                next_service_mileage=row.next_service_mileage,
                service_provider=row.service_provider,
                status=row.status,
                notes=row.notes
            )
            
        except Exception as e:
            logger.error(f"Failed to schedule maintenance: {e}")
            self.db_session.rollback()
            return None
    
    def complete_maintenance(
        self,
        maintenance_id: int,
        cost: float,
        mileage_at_service: float,
        completed_date: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Optional[VehicleMaintenance]:
        """
        Mark maintenance as completed.
        
        Args:
            maintenance_id: Maintenance ID
            cost: Cost of maintenance
            mileage_at_service: Mileage at time of service
            completed_date: Completion date (defaults to now)
            notes: Optional notes
            
        Returns:
            Updated VehicleMaintenance object or None if failed
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE vehicle_maintenance
                SET status = 'completed',
                    completed_date = :completed_date,
                    cost = :cost,
                    mileage_at_service = :mileage_at_service,
                    notes = :notes
                WHERE maintenance_id = :maintenance_id
                    AND status IN ('scheduled', 'in_progress')
                RETURNING maintenance_id, vehicle_id, maintenance_type,
                          description, scheduled_date, completed_date, cost,
                          mileage_at_service, next_service_due, next_service_mileage,
                          service_provider, status, notes
            """)
            
            result = self.db_session.execute(query, {
                'maintenance_id': maintenance_id,
                'completed_date': completed_date or datetime.utcnow(),
                'cost': cost,
                'mileage_at_service': mileage_at_service,
                'notes': notes
            })
            
            row = result.fetchone()
            self.db_session.commit()
            
            if row:
                return VehicleMaintenance(
                    maintenance_id=row.maintenance_id,
                    vehicle_id=row.vehicle_id,
                    maintenance_type=row.maintenance_type,
                    description=row.description,
                    scheduled_date=row.scheduled_date,
                    completed_date=row.completed_date,
                    cost=row.cost,
                    mileage_at_service=row.mileage_at_service,
                    next_service_due=row.next_service_due,
                    next_service_mileage=row.next_service_mileage,
                    service_provider=row.service_provider,
                    status=row.status,
                    notes=row.notes
                )
            return None
            
        except Exception as e:
            logger.error(f"Failed to complete maintenance: {e}")
            self.db_session.rollback()
            return None
    
    def get_upcoming_maintenance(self, days: int = 30) -> List[VehicleMaintenance]:
        """
        Get upcoming maintenance tasks.
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of VehicleMaintenance objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT vm.maintenance_id, vm.vehicle_id, vm.maintenance_type,
                       vm.description, vm.scheduled_date, vm.completed_date,
                       vm.cost, vm.mileage_at_service, vm.next_service_due,
                       vm.next_service_mileage, vm.service_provider, vm.status, vm.notes,
                       v.plate_number
                FROM vehicle_maintenance vm
                JOIN vehicles v ON vm.vehicle_id = v.vehicle_id
                WHERE vm.status IN ('scheduled', 'overdue')
                    AND vm.scheduled_date <= :end_date
                ORDER BY vm.scheduled_date ASC
            """)
            
            result = self.db_session.execute(query, {
                'end_date': datetime.utcnow() + timedelta(days=days)
            })
            
            maintenance_list = []
            for row in result:
                maintenance_list.append(VehicleMaintenance(
                    maintenance_id=row.maintenance_id,
                    vehicle_id=row.vehicle_id,
                    maintenance_type=row.maintenance_type,
                    description=row.description,
                    scheduled_date=row.scheduled_date,
                    completed_date=row.completed_date,
                    cost=row.cost,
                    mileage_at_service=row.mileage_at_service,
                    next_service_due=row.next_service_due,
                    next_service_mileage=row.next_service_mileage,
                    service_provider=row.service_provider,
                    status=row.status,
                    notes=row.notes
                ))
            
            return maintenance_list
            
        except Exception as e:
            logger.error(f"Failed to get upcoming maintenance: {e}")
            return []
    
    def get_overdue_maintenance(self) -> List[VehicleMaintenance]:
        """
        Get overdue maintenance tasks.
        
        Returns:
            List of VehicleMaintenance objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT vm.maintenance_id, vm.vehicle_id, vm.maintenance_type,
                       vm.description, vm.scheduled_date, vm.completed_date,
                       vm.cost, vm.mileage_at_service, vm.next_service_due,
                       vm.next_service_mileage, vm.service_provider, vm.status, vm.notes,
                       v.plate_number
                FROM vehicle_maintenance vm
                JOIN vehicles v ON vm.vehicle_id = v.vehicle_id
                WHERE vm.status IN ('scheduled', 'overdue')
                    AND vm.scheduled_date < CURRENT_DATE
                ORDER BY vm.scheduled_date ASC
            """)
            
            result = self.db_session.execute(query)
            
            maintenance_list = []
            for row in result:
                maintenance_list.append(VehicleMaintenance(
                    maintenance_id=row.maintenance_id,
                    vehicle_id=row.vehicle_id,
                    maintenance_type=row.maintenance_type,
                    description=row.description,
                    scheduled_date=row.scheduled_date,
                    completed_date=row.completed_date,
                    cost=row.cost,
                    mileage_at_service=row.mileage_at_service,
                    next_service_due=row.next_service_due,
                    next_service_mileage=row.next_service_mileage,
                    service_provider=row.service_provider,
                    status=row.status,
                    notes=row.notes
                ))
            
            return maintenance_list
            
        except Exception as e:
            logger.error(f"Failed to get overdue maintenance: {e}")
            return []
    
    def get_vehicle_maintenance_history(self, vehicle_id: int) -> List[VehicleMaintenance]:
        """
        Get maintenance history for a vehicle.
        
        Args:
            vehicle_id: Vehicle ID
            
        Returns:
            List of VehicleMaintenance objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT maintenance_id, vehicle_id, maintenance_type,
                       description, scheduled_date, completed_date, cost,
                       mileage_at_service, next_service_due, next_service_mileage,
                       service_provider, status, notes
                FROM vehicle_maintenance
                WHERE vehicle_id = :vehicle_id
                ORDER BY scheduled_date DESC
            """)
            
            result = self.db_session.execute(query, {'vehicle_id': vehicle_id})
            
            maintenance_list = []
            for row in result:
                maintenance_list.append(VehicleMaintenance(
                    maintenance_id=row.maintenance_id,
                    vehicle_id=row.vehicle_id,
                    maintenance_type=row.maintenance_type,
                    description=row.description,
                    scheduled_date=row.scheduled_date,
                    completed_date=row.completed_date,
                    cost=row.cost,
                    mileage_at_service=row.mileage_at_service,
                    next_service_due=row.next_service_due,
                    next_service_mileage=row.next_service_mileage,
                    service_provider=row.service_provider,
                    status=row.status,
                    notes=row.notes
                ))
            
            return maintenance_list
            
        except Exception as e:
            logger.error(f"Failed to get vehicle maintenance history: {e}")
            return []
    
    def update_overdue_maintenance(self) -> int:
        """
        Update maintenance status to overdue where applicable.
        
        Returns:
            Number of records updated
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return 0
        
        try:
            from sqlalchemy import text
            
            query = text("""
                UPDATE vehicle_maintenance
                SET status = 'overdue'
                WHERE status = 'scheduled'
                    AND scheduled_date < CURRENT_DATE
            """)
            
            result = self.db_session.execute(query)
            updated_count = result.rowcount
            self.db_session.commit()
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update overdue maintenance: {e}")
            self.db_session.rollback()
            return 0


# Singleton instances for easy access
_route_service_instance = None
_trip_service_instance = None
_driver_performance_service_instance = None
_vehicle_maintenance_service_instance = None


def get_route_service(db_session=None) -> RouteService:
    """Get or create route service instance."""
    global _route_service_instance
    if _route_service_instance is None:
        _route_service_instance = RouteService(db_session)
    return _route_service_instance


def get_trip_service(db_session=None) -> TripService:
    """Get or create trip service instance."""
    global _trip_service_instance
    if _trip_service_instance is None:
        _trip_service_instance = TripService(db_session)
    return _trip_service_instance


def get_driver_performance_service(db_session=None) -> DriverPerformanceService:
    """Get or create driver performance service instance."""
    global _driver_performance_service_instance
    if _driver_performance_service_instance is None:
        _driver_performance_service_instance = DriverPerformanceService(db_session)
    return _driver_performance_service_instance


def get_vehicle_maintenance_service(db_session=None) -> VehicleMaintenanceService:
    """Get or create vehicle maintenance service instance."""
    global _vehicle_maintenance_service_instance
    if _vehicle_maintenance_service_instance is None:
        _vehicle_maintenance_service_instance = VehicleMaintenanceService(db_session)
    return _vehicle_maintenance_service_instance