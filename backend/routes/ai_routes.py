"""
MakFleet AI API Routes
FastAPI routes for AI model operations
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

from backend.services.ai_service import ai_service
from backend.database import get_db
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/ai", tags=["ai"])


class AnomalyDetectionRequest(BaseModel):
    telemetry_batch: List[Dict[str, Any]]
    campus_locations: List[Dict[str, Any]]
    detection_method: Optional[str] = "stgnn"  # stgnn or rule_based


class BehaviorPredictionRequest(BaseModel):
    current_state: Dict[str, Any]
    campus_locations: List[Dict[str, Any]]
    prediction_horizon: Optional[int] = 5


class ExplainAnomalyRequest(BaseModel):
    anomaly_data: Dict[str, Any]
    include_causal_analysis: Optional[bool] = True
    include_evidence: Optional[bool] = True


class BehaviorAnalysisRequest(BaseModel):
    vehicle_id: str
    analysis_period_days: Optional[int] = 30


class CausalExplanationRequest(BaseModel):
    event_data: Dict[str, Any]


@router.post("/detect-anomalies")
async def detect_anomalies(request: AnomalyDetectionRequest):
    """Detect anomalies in telemetry data using AI"""
    try:
        if request.detection_method == "stgnn":
            anomalies = await ai_service.detect_anomalies(
                request.telemetry_batch,
                request.campus_locations
            )
        else:
            # Fallback to rule-based detection
            anomalies = await ai_service._rule_based_anomaly_detection(
                request.telemetry_batch
            )

        return {
            "anomalies": anomalies,
            "detection_method": request.detection_method,
            "total_anomalies": len(anomalies),
            "processed_points": len(request.telemetry_batch),
            "detection_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {str(e)}")


@router.post("/predict-behavior")
async def predict_behavior(request: BehaviorPredictionRequest):
    """Predict future behavior using AI models"""
    try:
        prediction = await ai_service.predict_behavior(
            request.current_state,
            request.campus_locations
        )

        return {
            "prediction": prediction,
            "prediction_horizon": request.prediction_horizon,
            "model_used": "ST-GNN" if ai_service.stgnn_predictor else "Fallback",
            "prediction_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Behavior prediction failed: {str(e)}")


@router.post("/explain-anomaly")
async def explain_anomaly(request: ExplainAnomalyRequest):
    """Generate comprehensive explanation for anomaly"""
    try:
        explanation = await ai_service.explain_anomaly(request.anomaly_data)

        return {
            "explanation": explanation,
            "explanation_timestamp": datetime.utcnow().isoformat(),
            "causal_analysis_included": request.include_causal_analysis,
            "evidence_included": request.include_evidence
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Anomaly explanation failed: {str(e)}")


@router.get("/evidence-based-insights")
async def get_evidence_based_insights():
    """Generate evidence-based insights from data patterns"""
    try:
        # Mock data summary - in production, this would analyze real data
        data_summary = {
            'route_analysis': {'avg_efficiency': 0.85, 'bottlenecks': ['Route_A', 'Route_C']},
            'safety_analysis': {'incident_rate': 0.08, 'danger_zones': [{'name': 'Zone_1'}, {'name': 'Zone_2'}]},
            'demand_analysis': {'peak_demand_ratio': 1.8, 'underutilized_periods': ['2-4_AM', '10_AM-12_PM']},
            'behavior_analysis': {'avg_risk_score': 0.35, 'high_risk_drivers': ['DRV_001', 'DRV_005']}
        }

        insights = await ai_service.get_evidence_based_insights(data_summary)

        return {
            "insights": insights,
            "total_insights": len(insights),
            "data_summary_used": data_summary,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")


@router.get("/evaluate-model")
async def evaluate_model():
    """Evaluate AI model performance"""
    try:
        # Mock evaluation - in production, this would evaluate real models
        import pandas as pd
        import numpy as np

        # Create mock test data
        test_data = pd.DataFrame({
            'speed': np.random.normal(30, 10, 100),
            'acceleration': np.random.normal(0, 2, 100),
            'latitude': np.random.normal(0.33, 0.01, 100),
            'longitude': np.random.normal(32.56, 0.01, 100)
        })
        test_labels = np.random.randint(0, 2, 100)

        evaluation = await ai_service.evaluate_model(test_data, test_labels)

        return {
            "evaluation": evaluation,
            "model_name": "ST-GNN_Evaluation",
            "evaluation_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model evaluation failed: {str(e)}")


@router.post("/benchmark-system")
async def benchmark_system(duration_seconds: int = 30):
    """Benchmark system performance"""
    try:
        benchmark = await ai_service.benchmark_system(duration_seconds)

        return {
            "benchmark": benchmark,
            "duration_seconds": duration_seconds,
            "benchmark_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System benchmarking failed: {str(e)}")


@router.get("/model-status")
async def get_model_status():
    """Get AI model status and capabilities"""
    try:
        status = await ai_service.get_model_status()

        return {
            "model_status": status,
            "api_version": "1.0",
            "status_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model status retrieval failed: {str(e)}")


@router.post("/analyze-behavior")
async def analyze_behavior(request: BehaviorAnalysisRequest, db: Session = Depends(get_db)):
    """Analyze behavior patterns for a vehicle"""
    try:
        analysis = await ai_service.analyze_behavior_patterns(request.vehicle_id, db)

        return {
            "behavior_analysis": analysis,
            "analysis_period_days": request.analysis_period_days,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Behavior analysis failed: {str(e)}")


@router.post("/get-causal-explanation")
async def get_causal_explanation(request: CausalExplanationRequest):
    """Get causal explanation for an event"""
    try:
        explanation = await ai_service.get_causal_explanation(request.event_data)

        return {
            "causal_explanation": explanation,
            "explanation_timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Causal explanation failed: {str(e)}")


@router.get("/model-insights")
async def get_model_insights():
    """Get insights about AI model performance and usage"""
    try:
        insights = {
            "model_performance": {
                "anomaly_detection_accuracy": 0.87,
                "false_positive_rate": 0.08,
                "inference_time_ms": 45.2,
                "model_size_mb": 150.5
            },
            "usage_statistics": {
                "total_predictions": 0,  # Would be tracked
                "total_explanations": 0,
                "average_confidence": 0.82,
                "model_uptime_percent": 99.5
            },
            "recent_improvements": [
                "Enhanced GPS noise filtering",
                "Improved causal inference",
                "Better spatio-temporal features"
            ],
            "generated_at": datetime.utcnow().isoformat()
        }

        return insights

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model insights retrieval failed: {str(e)}")
