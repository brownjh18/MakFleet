# Models Package
from .spatio_temporal_models import *
from . import spatio_temporal_models

# Import SQLAlchemy models from the main models.py file
try:
    # Import the models from the parent directory's models.py
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    from backend.models import (
        Driver, Vehicle, Telemetry, Event, Location,
        Anomaly, EvaluationResult
    )
except ImportError:
    # Create dummy classes if models not available
    class Driver: pass
    class Vehicle: pass
    class Telemetry: pass
    class Event: pass
    class Location: pass
    class Anomaly: pass
    class EvaluationResult: pass

__all__ = [
    # Spatio-temporal models
    'GPSPoint', 'SpatioTemporalPoint', 'Trajectory', 'CampusLocation',
    'ZoneType', 'DataQuality', 'EventType', 'DriverBehavior',
    'Anomaly', 'SemanticEvent', 'PrivacyConfig', 'EvaluationMetrics',

    # SQLAlchemy models
    'Driver', 'Vehicle', 'Telemetry', 'Event', 'Location', 'Anomaly', 'EvaluationResult'
]