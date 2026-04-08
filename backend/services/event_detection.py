"""
MakFleet Prototype - Event Detection Service
Detects events from raw telemetry data based on defined rules
"""

from datetime import datetime
from typing import Optional, Tuple


class EventDetectionService:
    """
    Service for detecting driving events from telemetry data
    """

    # Thresholds for event detection
    HARSH_BRAKING_THRESHOLD = -4.0  # m/s²
    RAPID_ACCELERATION_THRESHOLD = 4.0  # m/s²
    OVERSPEED_THRESHOLD = 70.0  # km/h
    IDLING_THRESHOLD = 0.0  # km/h (stationary)
    IDLING_DURATION_MINUTES = 5  # minutes

    @staticmethod
    def detect_event(speed: float, acceleration: float, 
                     prev_speed: Optional[float] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect event type from telemetry data
        
        Args:
            speed: Current speed in km/h
            acceleration: Current acceleration in m/s²
            prev_speed: Previous speed (optional, for additional checks)
            
        Returns:
            Tuple of (event_type, severity) or (None, None) if no event
        """
        # Harsh braking detection
        if acceleration < EventDetectionService.HARSH_BRAKING_THRESHOLD:
            severity = "high" if acceleration < -6.0 else "medium"
            return "HARSH_BRAKING", severity

        # Rapid acceleration detection
        if acceleration > EventDetectionService.RAPID_ACCELERATION_THRESHOLD:
            severity = "high" if acceleration > 6.0 else "medium"
            return "RAPID_ACCELERATION", severity

        # Overspeed detection
        if speed > EventDetectionService.OVERSPEED_THRESHOLD:
            severity = "high" if speed > 90.0 else "medium"
            return "OVERSPEED", severity

        # Idling detection (stationary with engine running)
        if speed == 0 and acceleration == 0:
            return "IDLING", "low"

        return None, None

    @staticmethod
    def calculate_risk_score(events_df) -> dict:
        """
        Calculate driver risk score based on events
        
        Risk Score Formula:
        Risk = (Harsh Braking × 3) + (Overspeed × 2) + (Rapid Acceleration × 1)
        
        Args:
            events_df: DataFrame containing event data
            
        Returns:
            Dictionary with risk scores per driver
        """
        risk_scores = {}
        
        # Weight factors for each event type
        weights = {
            "HARSH_BRAKING": 3,
            "OVERSPEED": 2,
            "RAPID_ACCELERATION": 1,
            "IDLING": 0.5
        }
        
        # Calculate risk score per vehicle/driver
        for event_type, weight in weights.items():
            count = len(events_df[events_df['event_type'] == event_type]) if len(events_df) > 0 else 0
            risk_scores[event_type] = count * weight
        
        # Calculate total risk score
        total_risk = sum(risk_scores.values())
        risk_scores['total'] = total_risk
        
        return risk_scores

    @staticmethod
    def get_event_summary(events) -> dict:
        """
        Get summary statistics for events
        
        Args:
            events: List of Event objects
            
        Returns:
            Dictionary with event counts by type
        """
        summary = {
            "HARSH_BRAKING": 0,
            "RAPID_ACCELERATION": 0,
            "OVERSPEED": 0,
            "IDLING": 0,
            "total": 0
        }
        
        for event in events:
            if event.event_type in summary:
                summary[event.event_type] += 1
                summary["total"] += 1
        
        return summary
