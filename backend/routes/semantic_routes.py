"""
MakFleet Semantic Data API Routes
FastAPI routes for semantic data processing
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from backend.services.semantic_service import semantic_service
from backend.database import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/semantic", tags=["semantic"])


class TelemetryBatchRequest(BaseModel):
    telemetry_data: List[Dict[str, Any]]
    process_anomalies: bool = True
    validate_quality: bool = True


class GPSValidationRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[float] = 10.0


class SemanticContextRequest(BaseModel):
    vehicle_id: str
    latitude: float
    longitude: float
    timestamp: str


@router.post("/process-telemetry-batch")
async def process_telemetry_batch(
    request: TelemetryBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process a batch of telemetry data through semantic pipeline"""
    try:
        result = await semantic_service.process_telemetry_batch(
            request.telemetry_data, db
        )

        # Add background task for additional processing if needed
        if request.process_anomalies and result.get('anomalies_detected', 0) > 0:
            background_tasks.add_task(
                _process_anomaly_followup,
                result['anomalies_detected'],
                db
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")


@router.post("/validate-gps")
async def validate_gps_point(request: GPSValidationRequest):
    """Validate GPS point quality and provide semantic context"""
    try:
        result = await semantic_service.validate_gps_data(
            request.latitude,
            request.longitude,
            request.accuracy
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GPS validation failed: {str(e)}")


@router.post("/get-semantic-context")
async def get_semantic_context(request: SemanticContextRequest):
    """Get semantic context for a location and time"""
    try:
        result = await semantic_service.get_semantic_context(
            request.vehicle_id,
            request.latitude,
            request.longitude,
            request.timestamp
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic context retrieval failed: {str(e)}")


@router.get("/danger-zones")
async def get_danger_zones(db: Session = Depends(get_db)):
    """Get danger zones based on anomaly patterns"""
    try:
        danger_zones = await semantic_service.get_danger_zones(db)

        return {
            "danger_zones": danger_zones,
            "total_zones": len(danger_zones),
            "generated_at": datetime.utcnow().isoformat(),
            "analysis_period_days": 30
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Danger zones analysis failed: {str(e)}")


@router.get("/data-quality-summary")
async def get_data_quality_summary(db: Session = Depends(get_db)):
    """Get summary of data quality metrics"""
    try:
        from backend.models import Telemetry

        # Get recent telemetry data (last 24 hours)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)

        telemetry_query = db.query(Telemetry).filter(
            Telemetry.timestamp >= twenty_four_hours_ago
        )

        telemetry_data = telemetry_query.all()

        if not telemetry_data:
            return {
                "quality_summary": {
                    "total_points": 0,
                    "quality_distribution": {},
                    "map_matching_rate": 0.0,
                    "validation_rate": 0.0
                },
                "period": "last_24_hours"
            }

        # Calculate quality metrics
        quality_scores = [t.data_quality_score for t in telemetry_data if t.data_quality_score is not None]
        map_matched_count = sum(1 for t in telemetry_data if t.map_matched)
        validated_count = sum(1 for t in telemetry_data if t.is_validated)

        quality_distribution = {
            "high": len([q for q in quality_scores if q >= 0.8]),
            "medium": len([q for q in quality_scores if 0.5 <= q < 0.8]),
            "low": len([q for q in quality_scores if q < 0.5])
        }

        return {
            "quality_summary": {
                "total_points": len(telemetry_data),
                "quality_distribution": quality_distribution,
                "map_matching_rate": map_matched_count / len(telemetry_data),
                "validation_rate": validated_count / len(telemetry_data),
                "average_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            },
            "period": "last_24_hours",
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quality summary failed: {str(e)}")


@router.get("/campus-locations")
async def get_campus_locations():
    """Get campus locations with semantic information"""
    try:
        locations = semantic_service.campus_locations

        return {
            "locations": [
                {
                    "location_id": loc.location_id,
                    "name": loc.name,
                    "latitude": loc.latitude,
                    "longitude": loc.longitude,
                    "zone_type": loc.zone_type.value,
                    "is_formal_path": loc.is_formal_path,
                    "safety_score": loc.safety_score
                }
                for loc in locations
            ],
            "total_locations": len(locations),
            "last_updated": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Campus locations retrieval failed: {str(e)}")


@router.get("/processing-stats")
async def get_processing_stats():
    """Get semantic processing statistics"""
    try:
        # This would track processing statistics in a real implementation
        return {
            "processing_stats": {
                "total_batches_processed": 0,  # Would be tracked
                "average_processing_time_ms": 0.0,
                "data_quality_improvement": 0.0,
                "anomaly_detection_rate": 0.0
            },
            "uptime_seconds": (datetime.utcnow() - datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds(),
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing stats retrieval failed: {str(e)}")


async def _process_anomaly_followup(anomaly_count: int, db: Session):
    """Background task for anomaly follow-up processing"""
    try:
        # Could implement notification system, additional analysis, etc.
        print(f"Processed {anomaly_count} anomalies - follow-up completed")

    except Exception as e:
        print(f"Anomaly follow-up failed: {e}")
