"""
MakFleet Explainable AI Module
Provides causal explanations and evidence-based decision support
"""
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
import shap
import lime
import lime.lime_tabular
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
from dataclasses import dataclass
import json


@dataclass
class CausalExplanation:
    """Causal explanation for an event or prediction"""
    event_type: str
    confidence: float
    causal_factors: List[Dict[str, Any]]
    counterfactuals: List[str]
    evidence_strength: str
    alternative_explanations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'confidence': self.confidence,
            'causal_factors': self.causal_factors,
            'counterfactuals': self.counterfactuals,
            'evidence_strength': self.evidence_strength,
            'alternative_explanations': self.alternative_explanations
        }


@dataclass
class EvidenceBasedInsight:
    """Evidence-based insight with supporting data"""
    insight_type: str
    description: str
    confidence_level: float
    supporting_evidence: List[Dict[str, Any]]
    data_sources: List[str]
    temporal_scope: str
    spatial_scope: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'insight_type': self.insight_type,
            'description': self.description,
            'confidence_level': self.confidence_level,
            'supporting_evidence': self.supporting_evidence,
            'data_sources': self.data_sources,
            'temporal_scope': self.temporal_scope,
            'spatial_scope': self.spatial_scope
        }


class CausalInferenceEngine:
    """Engine for causal inference and explanation"""
    
    def __init__(self):
        self.causal_graph = self._build_causal_graph()
        self.evidence_database = {}
    
    def _build_causal_graph(self) -> Dict[str, List[str]]:
        """Build causal graph for bodaboda events"""
        return {
            'weather_rainy': ['harsh_braking', 'speed_reduction', 'route_changes'],
            'time_peak_hour': ['increased_speed', 'aggressive_driving', 'traffic_jams'],
            'road_condition_poor': ['harsh_braking', 'speed_reduction', 'sharp_turns'],
            'driver_fatigue': ['overspeed', 'delayed_reactions', 'harsh_braking'],
            'passenger_load': ['reduced_speed', 'increased_stopping', 'route_deviation'],
            'traffic_density': ['speed_reduction', 'frequent_stops', 'harsh_braking'],
            'campus_event': ['increased_activity', 'route_changes', 'parking_difficulty']
        }
    
    def explain_event(self, event_data: Dict[str, Any], context_data: Dict[str, Any]) -> CausalExplanation:
        """Generate causal explanation for an event"""
        event_type = event_data['event_type']
        confidence = event_data.get('confidence', 0.8)
        
        # Identify causal factors based on event type
        causal_factors = self._identify_causal_factors(event_type, context_data)
        
        # Generate counterfactuals
        counterfactuals = self._generate_counterfactuals(event_type, causal_factors)
        
        # Assess evidence strength
        evidence_strength = self._assess_evidence_strength(causal_factors, context_data)
        
        # Consider alternative explanations
        alternative_explanations = self._generate_alternatives(event_type, causal_factors)
        
        return CausalExplanation(
            event_type=event_type,
            confidence=confidence,
            causal_factors=causal_factors,
            counterfactuals=counterfactuals,
            evidence_strength=evidence_strength,
            alternative_explanations=alternative_explanations
        )
    
    def _identify_causal_factors(self, event_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify likely causal factors for an event"""
        factors = []
        
        # Weather impact
        if context.get('weather_condition') == 'rainy':
            factors.append({
                'factor': 'rainy_weather',
                'impact': 'high',
                'evidence': 'Rain reduces road visibility and traction',
                'contribution': 0.7
            })
        
        # Time of day impact
        hour = context.get('hour_of_day', 12)
        if hour in [7, 8, 17, 18]:  # Peak hours
            factors.append({
                'factor': 'peak_hour_traffic',
                'impact': 'medium',
                'evidence': 'High traffic density during peak hours',
                'contribution': 0.5
            })
        
        # Speed-related events
        if event_type == 'HARSH_BRAKING':
            factors.append({
                'factor': 'sudden_obstacle',
                'impact': 'high',
                'evidence': 'Emergency braking indicates immediate hazard',
                'contribution': 0.8
            })
        
        # Campus-specific factors
        if context.get('zone_type') == 'Academic':
            factors.append({
                'factor': 'campus_activity',
                'impact': 'medium',
                'evidence': 'Academic zones have higher pedestrian activity',
                'contribution': 0.4
            })
        
        return factors
    
    def _generate_counterfactuals(self, event_type: str, factors: List[Dict[str, Any]]) -> List[str]:
        """Generate counterfactual explanations"""
        counterfactuals = []
        
        if event_type == 'HARSH_BRAKING':
            counterfactuals.extend([
                "If the driver had maintained lower speed, braking might not have been harsh",
                "If weather conditions were better, the incident might have been avoided",
                "If traffic was lighter, the driver could have reacted earlier"
            ])
        elif event_type == 'OVERSPEED':
            counterfactuals.extend([
                "If speed limits were better enforced, this violation might not have occurred",
                "If the driver was not in a hurry, speed might have been controlled",
                "If road conditions required slower speeds, compliance would be higher"
            ])
        
        return counterfactuals
    
    def _assess_evidence_strength(self, factors: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """Assess strength of evidence for explanation"""
        total_contribution = sum(f['contribution'] for f in factors)
        num_factors = len(factors)
        
        if total_contribution > 1.5 and num_factors >= 3:
            return "strong"
        elif total_contribution > 1.0 and num_factors >= 2:
            return "moderate"
        else:
            return "weak"
    
    def _generate_alternatives(self, event_type: str, factors: List[Dict[str, Any]]) -> List[str]:
        """Generate alternative explanations"""
        alternatives = [
            "Technical sensor malfunction",
            "Unusual environmental conditions",
            "Driver behavior variation"
        ]
        
        # Add event-specific alternatives
        if event_type == 'HARSH_BRAKING':
            alternatives.append("Emergency medical situation for passenger")
        elif event_type == 'OVERSPEED':
            alternatives.append("Emergency transportation requirement")
        
        return alternatives


class SHAPExplainer:
    """SHAP-based model explanations for ST-GNN predictions"""
    
    def __init__(self, model, background_data: pd.DataFrame):
        self.model = model
        self.explainer = shap.TreeExplainer(model)
        self.background_data = background_data
    
    def explain_prediction(self, input_data: pd.DataFrame) -> Dict[str, Any]:
        """Generate SHAP explanation for a prediction"""
        try:
            shap_values = self.explainer.shap_values(input_data)
            
            # For binary classification
            if isinstance(shap_values, list):
                shap_values = shap_values[1]  # Positive class
            
            # Get feature importance
            feature_importance = {}
            for i, feature in enumerate(input_data.columns):
                feature_importance[feature] = float(np.mean(np.abs(shap_values[:, i])))
            
            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            return {
                'feature_importance': dict(sorted_features),
                'base_value': float(self.explainer.expected_value),
                'shap_values': shap_values.tolist(),
                'explanation': self._interpret_shap_results(sorted_features)
            }
            
        except Exception as e:
            return {
                'error': f"SHAP explanation failed: {str(e)}",
                'fallback_explanation': "Model prediction based on spatio-temporal patterns"
            }
    
    def _interpret_shap_results(self, sorted_features: List[Tuple[str, float]]) -> str:
        """Interpret SHAP results in natural language"""
        top_features = sorted_features[:3]
        
        interpretations = {
            'speed': 'vehicle speed',
            'acceleration': 'acceleration patterns',
            'latitude': 'location coordinates',
            'longitude': 'location coordinates',
            'hour_of_day': 'time of day',
            'is_peak_hour': 'peak hour conditions',
            'data_quality_score': 'data reliability',
            'safety_score': 'location safety rating'
        }
        
        explanation_parts = []
        for feature, importance in top_features:
            readable_name = interpretations.get(feature, feature)
            explanation_parts.append(f"{readable_name} ({importance:.3f})")
        
        return f"Primary factors: {', '.join(explanation_parts)}"


class EvidenceBasedDecisionSupport:
    """Provides evidence-based insights for decision making"""
    
    def __init__(self):
        self.insights_cache = {}
        self.evidence_threshold = 0.7
    
    def generate_insights(self, data_summary: Dict[str, Any]) -> List[EvidenceBasedInsight]:
        """Generate evidence-based insights from data"""
        insights = []
        
        # Route optimization insights
        route_insight = self._analyze_route_efficiency(data_summary)
        if route_insight:
            insights.append(route_insight)
        
        # Safety insights
        safety_insight = self._analyze_safety_patterns(data_summary)
        if safety_insight:
            insights.append(safety_insight)
        
        # Demand prediction insights
        demand_insight = self._analyze_demand_patterns(data_summary)
        if demand_insight:
            insights.append(demand_insight)
        
        # Driver behavior insights
        behavior_insight = self._analyze_driver_behavior(data_summary)
        if behavior_insight:
            insights.append(behavior_insight)
        
        return insights
    
    def _analyze_route_efficiency(self, data: Dict[str, Any]) -> Optional[EvidenceBasedInsight]:
        """Analyze route efficiency patterns"""
        route_data = data.get('route_analysis', {})
        
        if not route_data:
            return None
        
        avg_efficiency = route_data.get('avg_efficiency', 0.8)
        bottleneck_routes = route_data.get('bottlenecks', [])
        
        if avg_efficiency < 0.7 or bottleneck_routes:
            evidence = []
            
            if avg_efficiency < 0.7:
                evidence.append({
                    'type': 'statistical',
                    'metric': 'route_efficiency',
                    'value': avg_efficiency,
                    'threshold': 0.7,
                    'significance': 'below_average'
                })
            
            if bottleneck_routes:
                evidence.append({
                    'type': 'pattern_analysis',
                    'metric': 'bottleneck_routes',
                    'value': len(bottleneck_routes),
                    'details': bottleneck_routes[:3]
                })
            
            return EvidenceBasedInsight(
                insight_type='route_optimization',
                description=f"Route efficiency is suboptimal ({avg_efficiency:.1%}). Consider optimizing {len(bottleneck_routes)} bottleneck routes.",
                confidence_level=min(0.9, avg_efficiency + 0.2),
                supporting_evidence=evidence,
                data_sources=['telemetry_data', 'route_logs'],
                temporal_scope='last_30_days',
                spatial_scope='campus_wide'
            )
        
        return None
    
    def _analyze_safety_patterns(self, data: Dict[str, Any]) -> Optional[EvidenceBasedInsight]:
        """Analyze safety patterns and hotspots"""
        safety_data = data.get('safety_analysis', {})
        
        if not safety_data:
            return None
        
        incident_rate = safety_data.get('incident_rate', 0.05)
        danger_zones = safety_data.get('danger_zones', [])
        
        if incident_rate > 0.1 or danger_zones:
            evidence = []
            
            if incident_rate > 0.1:
                evidence.append({
                    'type': 'statistical',
                    'metric': 'incident_rate',
                    'value': incident_rate,
                    'threshold': 0.1,
                    'significance': 'elevated'
                })
            
            if danger_zones:
                evidence.append({
                    'type': 'spatial_analysis',
                    'metric': 'danger_zones',
                    'value': len(danger_zones),
                    'details': [zone['name'] for zone in danger_zones[:3]]
                })
            
            return EvidenceBasedInsight(
                insight_type='safety_improvement',
                description=f"Elevated safety concerns with {len(danger_zones)} identified danger zones and {incident_rate:.1%} incident rate.",
                confidence_level=min(0.95, incident_rate * 10),
                supporting_evidence=evidence,
                data_sources=['event_logs', 'telemetry_data'],
                temporal_scope='last_7_days',
                spatial_scope='campus_wide'
            )
        
        return None
    
    def _analyze_demand_patterns(self, data: Dict[str, Any]) -> Optional[EvidenceBasedInsight]:
        """Analyze demand patterns for fleet optimization"""
        demand_data = data.get('demand_analysis', {})
        
        if not demand_data:
            return None
        
        peak_demand = demand_data.get('peak_demand_ratio', 1.5)
        underutilized_periods = demand_data.get('underutilized_periods', [])
        
        if peak_demand > 2.0 or underutilized_periods:
            evidence = []
            
            if peak_demand > 2.0:
                evidence.append({
                    'type': 'temporal_analysis',
                    'metric': 'peak_demand_ratio',
                    'value': peak_demand,
                    'threshold': 2.0,
                    'significance': 'high_variation'
                })
            
            if underutilized_periods:
                evidence.append({
                    'type': 'utilization_analysis',
                    'metric': 'underutilized_periods',
                    'value': len(underutilized_periods),
                    'details': underutilized_periods[:3]
                })
            
            return EvidenceBasedInsight(
                insight_type='demand_optimization',
                description=f"Demand varies significantly (peak ratio: {peak_demand:.1f}x). Consider dynamic fleet allocation.",
                confidence_level=min(0.85, peak_demand / 3),
                supporting_evidence=evidence,
                data_sources=['booking_data', 'telemetry_data'],
                temporal_scope='last_24_hours',
                spatial_scope='campus_wide'
            )
        
        return None
    
    def _analyze_driver_behavior(self, data: Dict[str, Any]) -> Optional[EvidenceBasedInsight]:
        """Analyze driver behavior patterns"""
        behavior_data = data.get('behavior_analysis', {})
        
        if not behavior_data:
            return None
        
        risk_score_avg = behavior_data.get('avg_risk_score', 0.3)
        high_risk_drivers = behavior_data.get('high_risk_drivers', [])
        
        if risk_score_avg > 0.4 or high_risk_drivers:
            evidence = []
            
            if risk_score_avg > 0.4:
                evidence.append({
                    'type': 'behavioral_analysis',
                    'metric': 'average_risk_score',
                    'value': risk_score_avg,
                    'threshold': 0.4,
                    'significance': 'elevated_risk'
                })
            
            if high_risk_drivers:
                evidence.append({
                    'type': 'driver_risk_analysis',
                    'metric': 'high_risk_drivers',
                    'value': len(high_risk_drivers),
                    'details': [f"Driver_{i+1}" for i in range(min(3, len(high_risk_drivers)))]
                })
            
            return EvidenceBasedInsight(
                insight_type='driver_training',
                description=f"Driver risk levels elevated (avg: {risk_score_avg:.2f}). {len(high_risk_drivers)} drivers need attention.",
                confidence_level=min(0.9, risk_score_avg * 2.5),
                supporting_evidence=evidence,
                data_sources=['event_logs', 'driver_profiles'],
                temporal_scope='last_30_days',
                spatial_scope='campus_wide'
            )
        
        return None


class ExplainableAIController:
    """Main controller for explainable AI functionality"""
    
    def __init__(self):
        self.causal_engine = CausalInferenceEngine()
        self.decision_support = EvidenceBasedDecisionSupport()
        self.shap_explainer = None  # Will be initialized with model
    
    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive explanation for an anomaly"""
        event_data = {
            'event_type': anomaly_data.get('anomaly_type', 'UNKNOWN'),
            'confidence': anomaly_data.get('confidence', 0.8)
        }
        
        context_data = anomaly_data.get('context', {})
        
        # Get causal explanation
        causal_exp = self.causal_engine.explain_event(event_data, context_data)
        
        # Generate evidence-based insights
        data_summary = anomaly_data.get('data_summary', {})
        insights = self.decision_support.generate_insights(data_summary)
        
        return {
            'anomaly_id': anomaly_data.get('anomaly_id'),
            'causal_explanation': causal_exp.to_dict(),
            'evidence_based_insights': [insight.to_dict() for insight in insights],
            'recommendations': self._generate_recommendations(causal_exp, insights),
            'explanation_confidence': causal_exp.confidence,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def explain_prediction(self, prediction_data: Dict[str, Any], model_features: pd.DataFrame) -> Dict[str, Any]:
        """Generate explanation for model prediction"""
        if self.shap_explainer:
            shap_explanation = self.shap_explainer.explain_prediction(model_features)
        else:
            shap_explanation = {'fallback_explanation': 'SHAP explainer not initialized'}
        
        # Add causal context
        causal_context = self._get_prediction_causal_context(prediction_data)
        
        return {
            'prediction_type': prediction_data.get('type'),
            'shap_explanation': shap_explanation,
            'causal_context': causal_context,
            'interpretability_score': self._calculate_interpretability_score(shap_explanation),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def _generate_recommendations(self, causal_exp: CausalExplanation,
                                insights: List[EvidenceBasedInsight]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Based on causal factors
        for factor in causal_exp.causal_factors:
            if factor['factor'] == 'rainy_weather':
                recommendations.append("Improve driver training for wet weather conditions")
            elif factor['factor'] == 'peak_hour_traffic':
                recommendations.append("Implement dynamic routing during peak hours")
            elif factor['factor'] == 'campus_activity':
                recommendations.append("Increase caution in academic zones with high pedestrian traffic")
        
        # Based on insights
        for insight in insights:
            if insight.insight_type == 'safety_improvement':
                recommendations.append("Deploy additional safety measures in identified danger zones")
            elif insight.insight_type == 'driver_training':
                recommendations.append("Conduct targeted training programs for high-risk drivers")
            elif insight.insight_type == 'route_optimization':
                recommendations.append("Redesign routes to avoid identified bottlenecks")
        
        return recommendations[:5]  # Limit to top 5
    
    def _get_prediction_causal_context(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get causal context for predictions"""
        prediction_type = prediction_data.get('type')
        
        if prediction_type == 'anomaly_detection':
            return {
                'causal_mechanism': 'Spatio-temporal pattern analysis',
                'key_factors': ['speed_patterns', 'location_context', 'temporal_patterns'],
                'uncertainty_sources': ['GPS_accuracy', 'environmental_factors']
            }
        elif prediction_type == 'demand_prediction':
            return {
                'causal_mechanism': 'Historical pattern extrapolation',
                'key_factors': ['time_of_day', 'campus_events', 'weather_conditions'],
                'uncertainty_sources': ['unpredictable_events', 'external_factors']
            }
        
        return {'causal_mechanism': 'Not specified'}
    
    def _calculate_interpretability_score(self, shap_explanation: Dict[str, Any]) -> float:
        """Calculate overall interpretability score"""
        if 'error' in shap_explanation:
            return 0.3  # Low confidence fallback
        
        feature_importance = shap_explanation.get('feature_importance', {})
        top_features = list(feature_importance.values())[:3]
        
        if len(top_features) >= 3:
            # Higher score if top features have clear separation
            importance_ratio = top_features[0] / (top_features[-1] + 1e-6)
            return min(0.95, 0.5 + importance_ratio * 0.1)
        
        return 0.7  # Moderate confidence
    
    def update_model_explainer(self, model, background_data: pd.DataFrame):
        """Update SHAP explainer with new model"""
        self.shap_explainer = SHAPExplainer(model, background_data)
