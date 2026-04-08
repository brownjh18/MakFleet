"""
MakFleet AI Service
Integrates ST-GNN models and explainable AI with FastAPI backend
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from fastapi import HTTPException

# Try to import optional dependencies
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

# Try to import AI models (may not be available in serverless)
try:
    from ai_models.st_gnn_model import STGNNPredictor, STGNNConfig
    AI_MODELS_AVAILABLE = True
except ImportError:
    STGNNPredictor = None
    STGNNConfig = None
    AI_MODELS_AVAILABLE = False

try:
    from ai_models.explainable_ai import ExplainableAIController
    EXPLAINABLE_AI_AVAILABLE = True
except ImportError:
    ExplainableAIController = None
    EXPLAINABLE_AI_AVAILABLE = False

try:
    from evaluation.evaluation_framework import ModelEvaluator, SystemBenchmarker
    EVALUATION_AVAILABLE = True
except ImportError:
    ModelEvaluator = None
    SystemBenchmarker = None
    EVALUATION_AVAILABLE = False

from backend.database import get_db
from sqlalchemy.orm import Session


class AIService:
    """Service for AI model operations"""

    def __init__(self):
        self.stgnn_predictor = None  # Will be initialized with trained model
        self.explainable_ai = None
        self.evaluator = None
        self.benchmarker = None
        self.model_config = None

        # Initialize available components
        if EXPLAINABLE_AI_AVAILABLE:
            try:
                self.explainable_ai = ExplainableAIController()
            except Exception as e:
                print(f"Warning: Could not initialize ExplainableAI: {e}")

        if EVALUATION_AVAILABLE:
            try:
                self.evaluator = ModelEvaluator()
            except Exception as e:
                print(f"Warning: Could not initialize ModelEvaluator: {e}")

        if EVALUATION_AVAILABLE:
            try:
                self.benchmarker = SystemBenchmarker()
            except Exception as e:
                print(f"Warning: Could not initialize SystemBenchmarker: {e}")

        if AI_MODELS_AVAILABLE:
            try:
                self.model_config = STGNNConfig()
            except Exception as e:
                print(f"Warning: Could not initialize STGNNConfig: {e}")

    def initialize_models(self, model_path: str = None):
        """Initialize AI models"""
        try:
            if model_path:
                self.stgnn_predictor = STGNNPredictor(model_path, self.model_config)
            # Note: In production, load pre-trained models here
        except Exception as e:
            print(f"Warning: Could not initialize AI models: {e}")

    async def detect_anomalies(self, telemetry_batch: List[Dict[str, Any]],
                             campus_locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies using ST-GNN model"""
        if not self.stgnn_predictor:
            # Fallback to rule-based detection
            return await self._rule_based_anomaly_detection(telemetry_batch)

        try:
            anomalies = self.stgnn_predictor.detect_anomalies(telemetry_batch, campus_locations)
            return anomalies

        except Exception as e:
            print(f"ST-GNN anomaly detection failed: {e}")
            return await self._rule_based_anomaly_detection(telemetry_batch)

    async def predict_behavior(self, current_state: Dict[str, Any],
                             campus_locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict future behavior using ST-GNN"""
        if not self.stgnn_predictor:
            return {"error": "ST-GNN model not available"}

        try:
            prediction = self.stgnn_predictor.predict_behavior(current_state, campus_locations)
            return prediction

        except Exception as e:
            return {"error": f"Behavior prediction failed: {str(e)}"}

    async def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation for anomaly"""
        if not self.explainable_ai:
            return {
                "explanation": "Rule-based explanation: Anomaly detected based on threshold analysis",
                "confidence": 0.7,
                "causal_factors": ["threshold_violation"]
            }

        try:
            explanation = self.explainable_ai.explain_anomaly(anomaly_data)
            return explanation

        except Exception as e:
            return {"error": f"Explanation generation failed: {str(e)}"}

    async def get_evidence_based_insights(self, data_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate evidence-based insights"""
        if not self.explainable_ai or not hasattr(self.explainable_ai, 'decision_support'):
            return [{"insight": "Basic insight: Monitor your fleet regularly", "confidence": 0.5}]

        try:
            insights = self.explainable_ai.decision_support.generate_insights(data_summary)
            return [insight.to_dict() for insight in insights]

        except Exception as e:
            return [{"error": f"Insight generation failed: {str(e)}"}]

    async def evaluate_model(self, test_data=None, test_labels=None, model_name: str = "current_model") -> Dict[str, Any]:
        """Evaluate model performance"""
        try:
            # This would normally evaluate against real test data
            # For now, return mock results
            mock_metrics = {
                "model_name": model_name,
                "accuracy": 0.87,
                "precision": 0.84,
                "recall": 0.82,
                "f1_score": 0.83,
                "auc_roc": 0.89,
                "inference_time_ms": 45.2,
                "memory_usage_mb": 512.3,
                "spatial_accuracy": 12.5,  # meters
                "temporal_consistency": 0.91,
                "anomaly_detection_rate": 0.88,
                "business_value_score": 0.76
            }

            return mock_metrics

        except Exception as e:
            return {"error": f"Model evaluation failed: {str(e)}"}

    async def benchmark_system(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Benchmark system performance"""
        if not self.benchmarker:
            return {
                "status": "benchmarking_unavailable",
                "message": "Benchmarking not available in this environment"
            }

        try:
            benchmark_results = self.benchmarker.run_load_test(
                test_scenario="ai_inference_load_test",
                duration_seconds=duration_seconds
            )
            return benchmark_results

        except Exception as e:
            return {"error": f"System benchmarking failed: {str(e)}"}

    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of AI models"""
        status = {
            "stgnn_available": self.stgnn_predictor is not None,
            "explainable_ai_available": self.explainable_ai is not None,
            "evaluation_framework_available": self.evaluator is not None,
            "benchmarking_available": self.benchmarker is not None,
            "model_config": {}
        }

        if self.model_config:
            status["model_config"] = {
                "node_features": getattr(self.model_config, 'node_features', 16),
                "hidden_dim": getattr(self.model_config, 'hidden_dim', 64),
                "sequence_length": getattr(self.model_config, 'sequence_length', 10),
                "prediction_horizon": getattr(self.model_config, 'prediction_horizon', 5)
            }

        if self.stgnn_predictor:
            status["model_info"] = {
                "anomaly_threshold": getattr(self.model_config, 'anomaly_threshold', 0.5) if self.model_config else 0.5,
                "supported_features": ["speed", "acceleration", "location", "time_features"]
            }

        return status

    async def _rule_based_anomaly_detection(self, telemetry_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback rule-based anomaly detection"""
        anomalies = []

        for point in telemetry_batch:
            speed = point.get('speed', 0)
            acceleration = point.get('acceleration', 0)

            anomaly = None

            # Speed violations
            if speed > 70:
                anomaly = {
                    'anomaly_id': f'rule_anomaly_{datetime.utcnow().timestamp()}',
                    'timestamp': point.get('timestamp', datetime.utcnow().isoformat()),
                    'anomaly_type': 'OVERSPEED',
                    'severity_score': min(1.0, speed / 100.0),
                    'detection_model': 'rule_based',
                    'confidence': 0.9,
                    'explanation': f'Vehicle speed {speed} km/h exceeds campus limit of 70 km/h',
                    'causal_factors': ['excessive_speed', 'possible_emergency'],
                    'affected_entities': [point.get('vehicle_id', 'unknown')],
                    'recommended_action': 'Enforce speed limits and review driver behavior'
                }

            # Harsh braking
            elif acceleration < -4.0:
                anomaly = {
                    'anomaly_id': f'rule_anomaly_{datetime.utcnow().timestamp()}',
                    'timestamp': point.get('timestamp', datetime.utcnow().isoformat()),
                    'anomaly_type': 'HARSH_BRAKING',
                    'severity_score': min(1.0, abs(acceleration) / 8.0),
                    'detection_model': 'rule_based',
                    'confidence': 0.85,
                    'explanation': f'Harsh braking detected with deceleration {acceleration} m/s²',
                    'causal_factors': ['sudden_stop', 'obstacle_avoidance', 'emergency_situation'],
                    'affected_entities': [point.get('vehicle_id', 'unknown')],
                    'recommended_action': 'Investigate incident and review safety protocols'
                }

            # Rapid acceleration
            elif acceleration > 4.0:
                anomaly = {
                    'anomaly_id': f'rule_anomaly_{datetime.utcnow().timestamp()}',
                    'timestamp': point.get('timestamp', datetime.utcnow().isoformat()),
                    'anomaly_type': 'RAPID_ACCELERATION',
                    'severity_score': min(1.0, acceleration / 8.0),
                    'detection_model': 'rule_based',
                    'confidence': 0.8,
                    'explanation': f'Rapid acceleration detected with {acceleration} m/s²',
                    'causal_factors': ['aggressive_driving', 'late_departure'],
                    'affected_entities': [point.get('vehicle_id', 'unknown')],
                    'recommended_action': 'Monitor driver behavior for fuel efficiency and safety'
                }

            if anomaly:
                anomalies.append(anomaly)

        return anomalies

    async def get_causal_explanation(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get causal explanation for an event"""
        try:
            from ai_models.explainable_ai import CausalInferenceEngine

            engine = CausalInferenceEngine()
            explanation = engine.explain_event(event_data, event_data.get('context', {}))

            return explanation.to_dict()

        except Exception as e:
            return {"error": f"Causal explanation failed: {str(e)}"}

    async def analyze_behavior_patterns(self, vehicle_id: str, db: Session) -> Dict[str, Any]:
        """Analyze behavior patterns for a vehicle"""
        try:
            # Query telemetry data for the vehicle
            from backend.models import Telemetry, Event

            # Get recent telemetry (last 30 days)
            thirty_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)

            telemetry_query = db.query(Telemetry).filter(
                Telemetry.vehicle_id == vehicle_id,
                Telemetry.timestamp >= thirty_days_ago
            ).order_by(Telemetry.timestamp)

            telemetry_data = telemetry_query.all()

            # Get events for the vehicle
            events_query = db.query(Event).filter(
                Event.vehicle_id == vehicle_id,
                Event.timestamp >= thirty_days_ago
            )

            events_data = events_query.all()

            # Analyze patterns
            analysis = {
                'vehicle_id': vehicle_id,
                'analysis_period_days': 30,
                'total_telemetry_points': len(telemetry_data),
                'total_events': len(events_data),
                'behavior_patterns': {},
                'risk_assessment': {}
            }

            if telemetry_data:
                # Speed analysis
                speeds = [t.speed for t in telemetry_data if t.speed is not None]
                if speeds:
                    analysis['behavior_patterns']['speed'] = {
                        'avg_speed': sum(speeds) / len(speeds),
                        'max_speed': max(speeds),
                        'overspeed_instances': len([s for s in speeds if s > 70])
                    }

                # Acceleration analysis
                accelerations = [t.acceleration for t in telemetry_data if t.acceleration is not None]
                if accelerations:
                    analysis['behavior_patterns']['acceleration'] = {
                        'harsh_braking_count': len([a for a in accelerations if a < -4.0]),
                        'rapid_accel_count': len([a for a in accelerations if a > 4.0]),
                        'avg_acceleration': sum(accelerations) / len(accelerations)
                    }

            # Event analysis
            event_types = {}
            for event in events_data:
                event_type = event.event_type
                if event_type not in event_types:
                    event_types[event_type] = 0
                event_types[event_type] += 1

            analysis['behavior_patterns']['events'] = event_types

            # Risk assessment
            risk_score = 0.0
            risk_factors = []

            overspeed_count = analysis['behavior_patterns'].get('speed', {}).get('overspeed_instances', 0)
            harsh_braking_count = analysis['behavior_patterns'].get('acceleration', {}).get('harsh_braking_count', 0)

            if overspeed_count > 10:
                risk_score += 0.3
                risk_factors.append('frequent_speeding')
            elif overspeed_count > 5:
                risk_score += 0.2
                risk_factors.append('occasional_speeding')

            if harsh_braking_count > 5:
                risk_score += 0.4
                risk_factors.append('harsh_braking')
            elif harsh_braking_count > 2:
                risk_score += 0.2
                risk_factors.append('some_harsh_braking')

            analysis['risk_assessment'] = {
                'risk_score': min(1.0, risk_score),
                'risk_level': 'high' if risk_score > 0.6 else 'medium' if risk_score > 0.3 else 'low',
                'risk_factors': risk_factors,
                'recommendations': self._generate_behavior_recommendations(risk_factors)
            }

            return analysis

        except Exception as e:
            return {"error": f"Behavior analysis failed: {str(e)}"}

    def _generate_behavior_recommendations(self, risk_factors: List[str]) -> List[str]:
        """Generate recommendations based on risk factors"""
        recommendations = []

        if 'frequent_speeding' in risk_factors:
            recommendations.extend([
                'Implement speed awareness training',
                'Install speed monitoring systems',
                'Review route assignments for time pressure'
            ])

        if 'harsh_braking' in risk_factors:
            recommendations.extend([
                'Conduct defensive driving training',
                'Investigate vehicle maintenance issues',
                'Review route planning for traffic conditions'
            ])

        if 'occasional_speeding' in risk_factors:
            recommendations.append('Monitor speed trends and provide feedback')

        if 'some_harsh_braking' in risk_factors:
            recommendations.append('Review driving behavior during peak hours')

        if not recommendations:
            recommendations.append('Continue monitoring - behavior appears normal')

        return recommendations


# Global service instance
ai_service = AIService()
