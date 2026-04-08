"""
MakFleet Spatio-Temporal Data Models
Advanced data models for semantic AI system
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

# Try to import numpy, but make it optional for serverless deployment
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


class EventType(Enum):
    """Event types with semantic meaning"""
    HARSH_BRAKING = "HARSH_BRAKING"
    RAPID_ACCELERATION = "RAPID_ACCELERATION"
    OVERSPEED = "OVERSPEED"
    IDLING = "IDLING"
    SHARP_TURN = "SHARP_TURN"
    WRONG_DIRECTION = "WRONG_DIRECTION"
    NEAR_MISS = "NEAR_MISS"
    STOP_ANOMALY = "STOP_ANOMALY"


class ZoneType(Enum):
    """Campus zone types with safety context"""
    ACADEMIC = "Academic"
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    RECREATION = "Recreation"
    CENTRAL = "Central"
    PARKING = "Parking"
    ROAD = "Road"
    FOOTPATH = "Footpath"


class DataQuality(Enum):
    """Data quality levels for IoT data validation"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INVALID = "INVALID"


@dataclass
class GPSPoint:
    """GPS point with noise handling"""
    latitude: float
    longitude: float
    timestamp: datetime
    accuracy: float  # GPS accuracy in meters
    altitude: Optional[float] = None
    bearing: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Validate GPS point"""
        # Check latitude range
        if not (-90 <= self.latitude <= 90):
            return False
        # Check longitude range
        if not (-180 <= self.longitude <= 180):
            return False
        # Check accuracy (reject if > 50 meters)
        if self.accuracy > 50.0:
            return False
        return True
    
    def to_numpy(self):
        """Convert to numpy array for ML processing"""
        if not NUMPY_AVAILABLE:
            return [self.latitude, self.longitude, self.timestamp.timestamp()]
        return np.array([self.latitude, self.longitude, self.timestamp.timestamp()])


@dataclass
class SpatioTemporalPoint:
    """Spatio-temporal point with semantic attributes"""
    location: GPSPoint
    speed: float  # km/h
    acceleration: float  # m/s²
    heading: float  # degrees
    semantic_context: Dict[str, Any] = field(default_factory=dict)
    data_quality: DataQuality = DataQuality.HIGH
    
    def compute_jerk(self, prev_acceleration: float, time_diff: float) -> float:
        """Compute jerk (rate of change of acceleration)"""
        if time_diff <= 0:
            return 0.0
        return (self.acceleration - prev_acceleration) / time_diff


@dataclass
class Trajectory:
    """Vehicle trajectory with spatio-temporal properties"""
    vehicle_id: str
    points: List[SpatioTemporalPoint]
    start_time: datetime
    end_time: datetime
    total_distance: float  # meters
    avg_speed: float  # km/h
    max_speed: float  # km/h
    
    def compute_features(self) -> Dict[str, float]:
        """Extract features for ML models"""
        if len(self.points) < 2:
            return {}
        
        speeds = [p.speed for p in self.points]
        accelerations = [p.acceleration for p in self.points]
        
        # Use numpy if available, otherwise use basic Python
        if NUMPY_AVAILABLE:
            return {
                'avg_speed': float(np.mean(speeds)),
                'speed_std': float(np.std(speeds)),
                'max_speed': float(np.max(speeds)),
                'avg_acceleration': float(np.mean(accelerations)),
                'acceleration_std': float(np.std(accelerations)),
                'harsh_braking_count': sum(1 for a in accelerations if a < -4.0),
                'rapid_accel_count': sum(1 for a in accelerations if a > 4.0),
                'duration_seconds': (self.end_time - self.start_time).total_seconds(),
                'point_count': len(self.points)
            }
        else:
            # Basic Python fallback
            return {
                'avg_speed': sum(speeds) / len(speeds),
                'speed_std': (sum((s - sum(speeds)/len(speeds))**2 for s in speeds) / len(speeds)) ** 0.5,
                'max_speed': max(speeds),
                'avg_acceleration': sum(accelerations) / len(accelerations),
                'acceleration_std': (sum((a - sum(accelerations)/len(accelerations))**2 for a in accelerations) / len(accelerations)) ** 0.5,
                'harsh_braking_count': sum(1 for a in accelerations if a < -4.0),
                'rapid_accel_count': sum(1 for a in accelerations if a > 4.0),
                'duration_seconds': (self.end_time - self.start_time).total_seconds(),
                'point_count': len(self.points)
            }


@dataclass
class CampusLocation:
    """Campus location with semantic attributes"""
    location_id: str
    name: str
    latitude: float
    longitude: float
    zone_type: ZoneType
    is_formal_path: bool
    safety_score: float  # 0.0 to 1.0
    capacity: Optional[int] = None  # For parking zones
    operating_hours: Optional[Dict[str, Any]] = None
    
    def distance_to(self, other: 'CampusLocation') -> float:
        """Calculate distance to another location using Haversine formula"""
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371000  # Earth's radius in meters
        
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(other.latitude), radians(other.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


@dataclass
class Route:
    """Route with semantic and graph properties"""
    route_id: str
    start_location: CampusLocation
    end_location: CampusLocation
    waypoints: List[CampusLocation]
    distance_km: float
    estimated_time_min: float
    difficulty_score: float  # 0.0 to 1.0
    is_common_route: bool
    path_types: List[str]  # road, footpath, shortcut
    
    def to_graph_edges(self) -> List[Dict[str, Any]]:
        """Convert route to graph edges for knowledge graph"""
        edges = []
        locations = [self.start_location] + self.waypoints + [self.end_location]
        
        for i in range(len(locations) - 1):
            edges.append({
                'source': locations[i].location_id,
                'target': locations[i+1].location_id,
                'distance': locations[i].distance_to(locations[i+1]),
                'path_type': self.path_types[i] if i < len(self.path_types) else 'road'
            })
        
        return edges


@dataclass
class DriverBehavior:
    """Driver behavior profile with AI insights"""
    driver_id: str
    anonymized_id: str  # Privacy: pseudonymized
    risk_score: float  # 0.0 to 1.0
    event_counts: Dict[str, int] = field(default_factory=dict)
    avg_speed: float = 0.0
    harsh_braking_frequency: float = 0.0
    overspeed_frequency: float = 0.0
    preferred_routes: List[str] = field(default_factory=list)
    peak_hours: List[int] = field(default_factory=list)
    behavior_clusters: List[str] = field(default_factory=list)  # ML-based clusters
    
    def compute_risk_score(self) -> float:
        """Compute risk score using weighted formula"""
        weights = {
            'HARSH_BRAKING': 3.0,
            'OVERSPEED': 2.0,
            'RAPID_ACCELERATION': 1.0,
            'IDLING': 0.5,
            'SHARP_TURN': 1.5,
            'WRONG_DIRECTION': 2.5
        }
        
        total_events = sum(self.event_counts.values())
        if total_events == 0:
            return 0.0
        
        weighted_sum = sum(
            self.event_counts.get(event_type, 0) * weight
            for event_type, weight in weights.items()
        )
        
        # Normalize to 0-1 range
        max_possible = total_events * max(weights.values())
        return min(weighted_sum / max_possible, 1.0) if max_possible > 0 else 0.0


@dataclass
class Anomaly:
    """AI-detected anomaly with explainability"""
    anomaly_id: str
    timestamp: datetime
    anomaly_type: str
    severity_score: float  # 0.0 to 1.0
    detection_model: str
    confidence: float
    explanation: str  # Explainable AI
    causal_factors: List[str]  # Explainable AI
    affected_entities: List[str]  # vehicle_ids, driver_ids
    recommended_action: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'anomaly_id': self.anomaly_id,
            'timestamp': self.timestamp.isoformat(),
            'anomaly_type': self.anomaly_type,
            'severity_score': self.severity_score,
            'detection_model': self.detection_model,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'causal_factors': self.causal_factors,
            'affected_entities': self.affected_entities,
            'recommended_action': self.recommended_action
        }


@dataclass
class SemanticEvent:
    """Event with semantic context and explainability"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    location: GPSPoint
    vehicle_id: str
    driver_id: str
    severity: str
    confidence: float
    explanation: str  # Why this event occurred
    causal_factors: List[str]  # Contributing factors
    context: Dict[str, Any] = field(default_factory=dict)  # Weather, time, etc.
    
    def to_knowledge_graph_node(self) -> Dict[str, Any]:
        """Convert to knowledge graph node"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'latitude': self.location.latitude,
            'longitude': self.location.longitude,
            'severity': self.severity,
            'confidence_score': self.confidence,
            'explanation': self.explanation,
            'causal_factors': self.causal_factors
        }


@dataclass
class PrivacyConfig:
    """Privacy-by-design configuration"""
    anonymization_enabled: bool = True
    data_retention_days: int = 30
    pseudonymization_key: str = ""
    access_control_enabled: bool = True
    audit_logging_enabled: bool = True
    consent_required: bool = True
    data_minimization: bool = True  # Only collect necessary data
    purpose_limitation: bool = True  # Use data only for stated purpose
    
    def should_anonymize(self, data_type: str) -> bool:
        """Check if data type should be anonymized"""
        sensitive_types = ['driver_id', 'license_number', 'phone', 'name']
        return self.anonymization_enabled and data_type in sensitive_types


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for system benchmarking"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    inference_time_ms: float
    memory_usage_mb: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            'model_name': self.model_name,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'auc_roc': self.auc_roc,
            'inference_time_ms': self.inference_time_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'timestamp': self.timestamp.isoformat()
        }
