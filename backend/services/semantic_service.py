"""
MakFleet Semantic Data Service
Integrates semantic data pipeline with FastAPI backend
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
import json

# Try to import semantic pipeline, but make it optional for serverless
try:
    from data_pipeline.semantic_pipeline import (
        SemanticDataPipeline, MapMatcher, GPSNoiseHandler
    )
    SEMANTIC_PIPELINE_AVAILABLE = True
except ImportError:
    SemanticDataPipeline = None
    MapMatcher = None
    GPSNoiseHandler = None
    SEMANTIC_PIPELINE_AVAILABLE = False

from backend.models.spatio_temporal_models import CampusLocation, ZoneType
from backend.database import get_db
from sqlalchemy.orm import Session


class SemanticDataService:
    """Service for semantic data processing operations"""

    def __init__(self):
        # Initialize campus locations (would be loaded from database in production)
        self.campus_locations = self._load_campus_locations()
        self.pipeline = None
        self.map_matcher = None
        self.gps_handler = None

        if SEMANTIC_PIPELINE_AVAILABLE:
            try:
                self.pipeline = SemanticDataPipeline(self.campus_locations)
                self.map_matcher = MapMatcher(self.campus_locations)
                self.gps_handler = GPSNoiseHandler()
            except Exception as e:
                print(f"Warning: Could not initialize semantic pipeline: {e}")

    def _load_campus_locations(self) -> List[CampusLocation]:
        """Load campus locations from database"""
        # For now, return hardcoded locations matching the original schema
        return [
            CampusLocation(
                location_id="LOC001",
                name="Main Library",
                latitude=0.3336,
                longitude=32.5656,
                zone_type=ZoneType.ACADEMIC,
                is_formal_path=True,
                safety_score=0.9
            ),
            CampusLocation(
                location_id="LOC002",
                name="Freedom Square",
                latitude=0.3342,
                longitude=32.5671,
                zone_type=ZoneType.CENTRAL,
                is_formal_path=True,
                safety_score=0.85
            ),
            CampusLocation(
                location_id="LOC003",
                name="Engineering Block",
                latitude=0.3351,
                longitude=32.5634,
                zone_type=ZoneType.ACADEMIC,
                is_formal_path=True,
                safety_score=0.88
            ),
            CampusLocation(
                location_id="LOC004",
                name="Mary Stuart Hall",
                latitude=0.3328,
                longitude=32.5689,
                zone_type=ZoneType.RESIDENTIAL,
                is_formal_path=True,
                safety_score=0.82
            ),
            CampusLocation(
                location_id="LOC005",
                name="Central Teaching Facility",
                latitude=0.3345,
                longitude=32.5662,
                zone_type=ZoneType.ACADEMIC,
                is_formal_path=True,
                safety_score=0.87
            ),
            CampusLocation(
                location_id="LOC006",
                name="Food Court",
                latitude=0.3339,
                longitude=32.5685,
                zone_type=ZoneType.COMMERCIAL,
                is_formal_path=True,
                safety_score=0.75
            )
        ]

    async def process_telemetry_batch(self, raw_telemetry: List[Dict[str, Any]], db: Session) -> Dict[str, Any]:
        """Process a batch of raw telemetry data through semantic pipeline"""
        try:
            # Process through semantic pipeline
            processed_data = self.pipeline.process_telemetry_batch(raw_telemetry)

            # Store processed data
            stored_count = 0
            for point in processed_data:
                # Update or create telemetry record with semantic data
                await self._store_processed_telemetry(point, db)
                stored_count += 1

            # Detect anomalies
            anomalies = self.pipeline.detect_anomalies(processed_data)

            # Store anomalies
            anomaly_count = 0
            for anomaly in anomalies:
                await self._store_anomaly(anomaly, db)
                anomaly_count += 1

            return {
                "status": "success",
                "processed_points": stored_count,
                "anomalies_detected": anomaly_count,
                "data_quality": self._calculate_batch_quality(processed_data)
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Semantic processing failed: {str(e)}")

    async def validate_gps_data(self, latitude: float, longitude: float,
                              accuracy: float = 10.0) -> Dict[str, Any]:
        """Validate GPS point quality"""
        from backend.models.spatio_temporal_models import GPSPoint

        gps_point = GPSPoint(
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.utcnow(),
            accuracy=accuracy
        )

        quality = self.gps_handler.validate_point(gps_point)
        is_valid = quality.value != "INVALID"

        # Map matching
        match_result = self.map_matcher.match_point(gps_point)

        return {
            "is_valid": is_valid,
            "quality": quality.value,
            "map_matched": match_result is not None,
            "matched_location": match_result.matched_location.name if match_result else None,
            "match_confidence": match_result.confidence if match_result else 0.0,
            "is_formal_path": match_result.is_on_formal_path if match_result else False
        }

    async def get_semantic_context(self, vehicle_id: str, latitude: float,
                                 longitude: float, timestamp: str) -> Dict[str, Any]:
        """Get semantic context for a location and time"""
        from backend.models.spatio_temporal_models import GPSPoint, SpatioTemporalPoint

        gps_point = GPSPoint(
            latitude=latitude,
            longitude=longitude,
            timestamp=datetime.fromisoformat(timestamp),
            accuracy=10.0
        )

        st_point = SpatioTemporalPoint(
            location=gps_point,
            speed=0.0,  # Not available in this context
            acceleration=0.0,
            heading=0.0
        )

        # Get semantic context
        match_result = self.map_matcher.match_point(gps_point)
        context = self.pipeline.enricher.enrich_telemetry(st_point, match_result.matched_location if match_result else None)

        return {
            "semantic_context": context,
            "location_info": {
                "matched": match_result is not None,
                "location_name": match_result.matched_location.name if match_result else None,
                "zone_type": match_result.matched_location.zone_type.value if match_result else None,
                "safety_score": match_result.matched_location.safety_score if match_result else None
            } if match_result else None
        }

    async def get_danger_zones(self, db: Session) -> List[Dict[str, Any]]:
        """Get dangerous zones based on anomaly patterns"""
        # Query for frequent anomaly locations
        query = """
        SELECT
            ROUND(latitude, 3) as lat_rounded,
            ROUND(longitude, 3) as lon_rounded,
            COUNT(*) as anomaly_count,
            AVG(severity_score) as avg_severity,
            STRING_AGG(DISTINCT anomaly_type, ', ') as anomaly_types
        FROM anomalies
        WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days'
        GROUP BY lat_rounded, lon_rounded
        HAVING COUNT(*) > 5
        ORDER BY anomaly_count DESC
        LIMIT 20
        """

        try:
            result = db.execute(query)
            danger_zones = []

            for row in result:
                danger_zones.append({
                    "latitude": row[0],
                    "longitude": row[1],
                    "anomaly_count": row[2],
                    "avg_severity": row[3],
                    "anomaly_types": row[4],
                    "risk_level": "high" if row[2] > 15 else "medium" if row[2] > 10 else "low"
                })

            return danger_zones

        except Exception as e:
            # Fallback for databases without advanced SQL
            return []

    async def _store_processed_telemetry(self, point: Dict[str, Any], db: Session):
        """Store processed telemetry with semantic data"""
        from backend.models import Telemetry

        # Check if telemetry already exists
        existing = db.query(Telemetry).filter_by(telemetry_id=point["telemetry_id"]).first()

        if existing:
            # Update with semantic data
            existing.data_quality_score = point.get("data_quality_score", 0.8)
            existing.is_validated = True
            existing.semantic_context = json.dumps(point.get("semantic_context", {}))
            existing.map_matched = point.get("map_matched", False)
            existing.matched_location_id = point.get("matched_location_id")
            existing.match_confidence = point.get("match_confidence", 0.0)
            existing.provenance_id = point.get("provenance_id")
        else:
            # Create new record
            telemetry = Telemetry(
                telemetry_id=point["telemetry_id"],
                vehicle_id=point["vehicle_id"],
                latitude=point["latitude"],
                longitude=point["longitude"],
                speed=point["speed"],
                acceleration=point["acceleration"],
                timestamp=datetime.fromisoformat(point["timestamp"]),
                gps_accuracy=point.get("gps_accuracy", 10.0),
                data_quality_score=point.get("data_quality_score", 0.8),
                is_validated=True,
                semantic_context=json.dumps(point.get("semantic_context", {})),
                map_matched=point.get("map_matched", False),
                matched_location_id=point.get("matched_location_id"),
                match_confidence=point.get("match_confidence", 0.0),
                provenance_id=point.get("provenance_id")
            )
            db.add(telemetry)

        db.commit()

    async def _store_anomaly(self, anomaly: Dict[str, Any], db: Session):
        """Store detected anomaly"""
        from backend.models import Anomaly

        anomaly_record = Anomaly(
            anomaly_id=f"anomaly_{datetime.utcnow().timestamp()}",
            timestamp=datetime.fromisoformat(anomaly["timestamp"]),
            anomaly_type=anomaly["type"],
            severity_score=anomaly.get("severity", 0.5),
            detection_model="semantic_pipeline",
            confidence=anomaly.get("confidence", 0.8),
            explanation=anomaly.get("explanation", ""),
            causal_factors=json.dumps(anomaly.get("causal_factors", [])),
            affected_entities=json.dumps([anomaly.get("vehicle_id", "")]),
            recommended_action=self._generate_anomaly_action(anomaly)
        )

        db.add(anomaly_record)
        db.commit()

    def _generate_anomaly_action(self, anomaly: Dict[str, Any]) -> str:
        """Generate recommended action for anomaly"""
        anomaly_type = anomaly["type"]

        actions = {
            "HARSH_BRAKING": "Review driver training on emergency braking procedures",
            "OVERSPEED": "Implement speed limit enforcement in the area",
            "RAPID_ACCELERATION": "Monitor driver behavior for aggressive driving patterns",
            "IDLING": "Investigate potential mechanical issues or inefficient routing"
        }

        return actions.get(anomaly_type, "Investigate and monitor the incident")

    def _calculate_batch_quality(self, processed_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate quality metrics for processed batch"""
        if not processed_data:
            return {"overall_quality": 0.0, "valid_points": 0, "map_matched_ratio": 0.0}

        total_points = len(processed_data)
        valid_points = sum(1 for p in processed_data if p.get("data_quality_score", 0) > 0.5)
        map_matched = sum(1 for p in processed_data if p.get("map_matched", False))

        return {
            "overall_quality": sum(p.get("data_quality_score", 0) for p in processed_data) / total_points,
            "valid_points": valid_points,
            "map_matched_ratio": map_matched / total_points,
            "total_points": total_points
        }


# Global service instance
semantic_service = SemanticDataService()
