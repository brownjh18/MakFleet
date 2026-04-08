"""
MakFleet Semantic Data Engineering Pipeline
Handles noisy IoT data with GPS noise, map-matching, and semantic enrichment
"""
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import math
from collections import defaultdict

from backend.models.spatio_temporal_models import (
    GPSPoint, SpatioTemporalPoint, Trajectory, CampusLocation,
    DataQuality, EventType, SemanticEvent
)


@dataclass
class MapMatchingResult:
    """Result of map-matching algorithm"""
    original_point: GPSPoint
    matched_point: GPSPoint
    matched_location: CampusLocation
    distance_meters: float
    confidence: float
    is_on_formal_path: bool


class GPSNoiseHandler:
    """Handles GPS noise and data quality issues"""
    
    def __init__(self, max_accuracy: float = 50.0, max_speed_kmh: float = 120.0):
        self.max_accuracy = max_accuracy
        self.max_speed_kmh = max_speed_kmh
    
    def validate_point(self, point: GPSPoint) -> DataQuality:
        """Validate GPS point quality"""
        # Check basic validity
        if not point.is_valid():
            return DataQuality.INVALID
        
        # Check accuracy
        if point.accuracy > self.max_accuracy:
            return DataQuality.LOW
        elif point.accuracy > 20.0:
            return DataQuality.MEDIUM
        
        return DataQuality.HIGH
    
    def filter_outliers(self, points: List[GPSPoint]) -> List[GPSPoint]:
        """Filter GPS outliers using statistical methods"""
        if len(points) < 3:
            return points
        
        # Calculate median positions
        lats = [p.latitude for p in points]
        lons = [p.longitude for p in points]
        
        median_lat = np.median(lats)
        median_lon = np.median(lons)
        
        # Calculate median absolute deviation
        lat_mad = np.median(np.abs(lats - median_lat))
        lon_mad = np.median(np.abs(lons - median_lon))
        
        # Filter points outside 3 MAD
        filtered = []
        for point in points:
            lat_dev = abs(point.latitude - median_lat)
            lon_dev = abs(point.longitude - median_lon)
            
            if lat_dev < 3 * lat_mad and lon_dev < 3 * lon_mad:
                filtered.append(point)
        
        return filtered
    
    def smooth_trajectory(self, points: List[GPSPoint], window_size: int = 5) -> List[GPSPoint]:
        """Smooth trajectory using moving average"""
        if len(points) < window_size:
            return points
        
        smoothed = []
        for i in range(len(points)):
            start = max(0, i - window_size // 2)
            end = min(len(points), i + window_size // 2 + 1)
            
            window = points[start:end]
            avg_lat = np.mean([p.latitude for p in window])
            avg_lon = np.mean([p.longitude for p in window])
            
            smoothed.append(GPSPoint(
                latitude=avg_lat,
                longitude=avg_lon,
                timestamp=points[i].timestamp,
                accuracy=points[i].accuracy,
                altitude=points[i].altitude,
                bearing=points[i].bearing
            ))
        
        return smoothed
    
    def detect_speed_anomaly(self, point1: GPSPoint, point2: GPSPoint) -> bool:
        """Detect impossible speed between two points"""
        distance = self._haversine_distance(point1, point2)
        time_diff = (point2.timestamp - point1.timestamp).total_seconds()
        
        if time_diff <= 0:
            return True
        
        speed_ms = distance / time_diff
        speed_kmh = speed_ms * 3.6
        
        return speed_kmh > self.max_speed_kmh
    
    def _haversine_distance(self, point1: GPSPoint, point2: GPSPoint) -> float:
        """Calculate distance between two GPS points using Haversine formula"""
        R = 6371000  # Earth's radius in meters
        
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class MapMatcher:
    """Map-matches GPS points to campus road network"""
    
    def __init__(self, campus_locations: List[CampusLocation]):
        self.campus_locations = campus_locations
        self.road_network = self._build_road_network()
    
    def _build_road_network(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build road network graph from campus locations"""
        network = defaultdict(list)
        
        # Create connections between nearby locations
        for i, loc1 in enumerate(self.campus_locations):
            for j, loc2 in enumerate(self.campus_locations):
                if i != j:
                    distance = loc1.distance_to(loc2)
                    # Connect locations within 500 meters
                    if distance < 500:
                        network[loc1.location_id].append({
                            'target': loc2.location_id,
                            'distance': distance,
                            'location': loc2
                        })
        
        return network
    
    def match_point(self, point: GPSPoint, max_distance: float = 100.0) -> Optional[MapMatchingResult]:
        """Match GPS point to nearest campus location"""
        best_match = None
        best_distance = float('inf')
        
        for location in self.campus_locations:
            distance = self._haversine_distance(
                point,
                GPSPoint(location.latitude, location.longitude, point.timestamp, 0)
            )
            
            if distance < best_distance and distance <= max_distance:
                best_distance = distance
                best_match = location
        
        if best_match is None:
            return None
        
        # Calculate confidence based on distance
        confidence = max(0.0, 1.0 - (best_distance / max_distance))
        
        # Create matched point
        matched_point = GPSPoint(
            latitude=best_match.latitude,
            longitude=best_match.longitude,
            timestamp=point.timestamp,
            accuracy=point.accuracy
        )
        
        return MapMatchingResult(
            original_point=point,
            matched_point=matched_point,
            matched_location=best_match,
            distance_meters=best_distance,
            confidence=confidence,
            is_on_formal_path=best_match.is_formal_path
        )
    
    def match_trajectory(self, trajectory: Trajectory) -> List[MapMatchingResult]:
        """Match entire trajectory to road network"""
        results = []
        for point in trajectory.points:
            result = self.match_point(point.location)
            if result:
                results.append(result)
        return results
    
    def _haversine_distance(self, point1: GPSPoint, point2: GPSPoint) -> float:
        """Calculate distance between two GPS points"""
        R = 6371000
        
        lat1, lon1 = math.radians(point1.latitude), math.radians(point1.longitude)
        lat2, lon2 = math.radians(point2.latitude), math.radians(point2.longitude)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class SemanticEnricher:
    """Enriches telemetry data with semantic context"""
    
    def __init__(self, campus_locations: List[CampusLocation]):
        self.campus_locations = campus_locations
        self.location_lookup = {loc.location_id: loc for loc in campus_locations}
    
    def enrich_telemetry(self, point: SpatioTemporalPoint, 
                        matched_location: Optional[CampusLocation] = None) -> Dict[str, Any]:
        """Add semantic context to telemetry point"""
        context = {
            'timestamp': point.location.timestamp.isoformat(),
            'hour_of_day': point.location.timestamp.hour,
            'day_of_week': point.location.timestamp.strftime('%A'),
            'is_peak_hour': self._is_peak_hour(point.location.timestamp),
            'is_class_time': self._is_class_time(point.location.timestamp),
            'speed_category': self._categorize_speed(point.speed),
            'acceleration_category': self._categorize_acceleration(point.acceleration)
        }
        
        if matched_location:
            context.update({
                'zone_type': matched_location.zone_type.value,
                'location_name': matched_location.name,
                'is_formal_path': matched_location.is_formal_path,
                'safety_score': matched_location.safety_score
            })
        
        return context
    
    def _is_peak_hour(self, timestamp: datetime) -> bool:
        """Check if timestamp is during peak hours"""
        hour = timestamp.hour
        # Morning peak: 7-9 AM, Evening peak: 5-7 PM
        return (7 <= hour <= 9) or (17 <= hour <= 19)
    
    def _is_class_time(self, timestamp: datetime) -> bool:
        """Check if timestamp is during class hours"""
        hour = timestamp.hour
        weekday = timestamp.weekday()
        # Monday-Friday, 8 AM - 6 PM
        return weekday < 5 and 8 <= hour <= 18
    
    def _categorize_speed(self, speed_kmh: float) -> str:
        """Categorize speed for semantic understanding"""
        if speed_kmh < 5:
            return 'stopped'
        elif speed_kmh < 20:
            return 'slow'
        elif speed_kmh < 40:
            return 'normal'
        elif speed_kmh < 60:
            return 'fast'
        else:
            return 'very_fast'
    
    def _categorize_acceleration(self, acceleration: float) -> str:
        """Categorize acceleration for semantic understanding"""
        if acceleration < -4.0:
            return 'harsh_braking'
        elif acceleration < -2.0:
            return 'braking'
        elif acceleration < 2.0:
            return 'normal'
        elif acceleration < 4.0:
            return 'accelerating'
        else:
            return 'rapid_acceleration'


class DataProvenanceTracker:
    """Tracks data provenance for trust and audit"""
    
    def __init__(self):
        self.provenance_records = []
    
    def track_ingestion(self, data_id: str, source: str, timestamp: datetime,
                       quality: DataQuality, transformations: List[str]):
        """Track data ingestion provenance"""
        record = {
            'data_id': data_id,
            'source': source,
            'timestamp': timestamp.isoformat(),
            'quality': quality.value,
            'transformations': transformations,
            'ingestion_time': datetime.utcnow().isoformat()
        }
        self.provenance_records.append(record)
        return record
    
    def track_transformation(self, data_id: str, transformation: str,
                           input_data: Dict[str, Any], output_data: Dict[str, Any]):
        """Track data transformation provenance"""
        record = {
            'data_id': data_id,
            'transformation': transformation,
            'input_summary': self._summarize_data(input_data),
            'output_summary': self._summarize_data(output_data),
            'timestamp': datetime.utcnow().isoformat()
        }
        self.provenance_records.append(record)
        return record
    
    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of data for provenance tracking"""
        return {
            'keys': list(data.keys()),
            'size': len(str(data)),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_provenance(self, data_id: str) -> List[Dict[str, Any]]:
        """Get provenance records for data ID"""
        return [r for r in self.provenance_records if r.get('data_id') == data_id]


class SemanticDataPipeline:
    """Main semantic data engineering pipeline"""
    
    def __init__(self, campus_locations: List[CampusLocation]):
        self.gps_handler = GPSNoiseHandler()
        self.map_matcher = MapMatcher(campus_locations)
        self.enricher = SemanticEnricher(campus_locations)
        self.provenance_tracker = DataProvenanceTracker()
    
    def process_telemetry_batch(self, raw_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process batch of raw telemetry points"""
        processed_points = []
        
        for raw_point in raw_points:
            try:
                # Step 1: Create GPS point
                gps_point = GPSPoint(
                    latitude=raw_point['latitude'],
                    longitude=raw_point['longitude'],
                    timestamp=datetime.fromisoformat(raw_point['timestamp']),
                    accuracy=raw_point.get('gps_accuracy', 10.0)
                )
                
                # Step 2: Validate GPS quality
                quality = self.gps_handler.validate_point(gps_point)
                
                if quality == DataQuality.INVALID:
                    continue
                
                # Step 3: Create spatio-temporal point
                st_point = SpatioTemporalPoint(
                    location=gps_point,
                    speed=raw_point.get('speed', 0.0),
                    acceleration=raw_point.get('acceleration', 0.0),
                    heading=raw_point.get('heading', 0.0),
                    data_quality=quality
                )
                
                # Step 4: Map-match to campus locations
                match_result = self.map_matcher.match_point(gps_point)
                
                # Step 5: Enrich with semantic context
                semantic_context = self.enricher.enrich_telemetry(
                    st_point,
                    match_result.matched_location if match_result else None
                )
                
                # Step 6: Track provenance
                provenance = self.provenance_tracker.track_ingestion(
                    data_id=raw_point.get('telemetry_id', 'unknown'),
                    source='iot_device',
                    timestamp=gps_point.timestamp,
                    quality=quality,
                    transformations=['validation', 'map_matching', 'semantic_enrichment']
                )
                
                # Step 7: Create processed point
                processed_point = {
                    'telemetry_id': raw_point.get('telemetry_id'),
                    'vehicle_id': raw_point.get('vehicle_id'),
                    'latitude': gps_point.latitude,
                    'longitude': gps_point.longitude,
                    'speed': st_point.speed,
                    'acceleration': st_point.acceleration,
                    'timestamp': gps_point.timestamp.isoformat(),
                    'data_quality': quality.value,
                    'semantic_context': semantic_context,
                    'map_matched': match_result is not None,
                    'matched_location_id': match_result.matched_location.location_id if match_result else None,
                    'match_confidence': match_result.confidence if match_result else 0.0,
                    'provenance_id': provenance['data_id']
                }
                
                processed_points.append(processed_point)
                
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing telemetry point: {e}")
                continue
        
        return processed_points
    
    def detect_anomalies(self, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in processed telemetry"""
        anomalies = []
        
        for i in range(1, len(points)):
            prev = points[i-1]
            curr = points[i]
            
            # Check for speed anomalies
            if curr['speed'] > 70:  # Over speed limit
                anomalies.append({
                    'type': 'OVERSPEED',
                    'timestamp': curr['timestamp'],
                    'vehicle_id': curr['vehicle_id'],
                    'severity': 'high' if curr['speed'] > 90 else 'medium',
                    'confidence': 0.9,
                    'explanation': f"Vehicle speed {curr['speed']} km/h exceeds campus limit",
                    'causal_factors': ['speeding', 'time_pressure']
                })
            
            # Check for harsh braking
            if curr['acceleration'] < -4.0:
                anomalies.append({
                    'type': 'HARSH_BRAKING',
                    'timestamp': curr['timestamp'],
                    'vehicle_id': curr['vehicle_id'],
                    'severity': 'high' if curr['acceleration'] < -6.0 else 'medium',
                    'confidence': 0.85,
                    'explanation': f"Harsh braking detected with deceleration {curr['acceleration']} m/s²",
                    'causal_factors': ['sudden_stop', 'obstacle_avoidance']
                })
            
            # Check for rapid acceleration
            if curr['acceleration'] > 4.0:
                anomalies.append({
                    'type': 'RAPID_ACCELERATION',
                    'timestamp': curr['timestamp'],
                    'vehicle_id': curr['vehicle_id'],
                    'severity': 'medium',
                    'confidence': 0.8,
                    'explanation': f"Rapid acceleration detected with {curr['acceleration']} m/s²",
                    'causal_factors': ['aggressive_driving', 'late_departure']
                })
        
        return anomalies
