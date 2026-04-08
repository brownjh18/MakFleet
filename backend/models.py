"""
MakFleet Prototype - Database Models
Legacy SQLAlchemy models for backward compatibility
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Driver(Base):
    """Legacy driver model with privacy extensions"""
    __tablename__ = "drivers"

    driver_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    license_number = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Privacy extensions
    anonymized_id = Column(String(32), unique=True)  # Privacy: pseudonymized identifier
    license_hash = Column(String(64))  # Privacy: hashed license
    privacy_consent = Column(Boolean, default=False)
    data_retention_days = Column(Integer, default=30)

    # Relationships
    vehicles = relationship("Vehicle", back_populates="driver")


class Vehicle(Base):
    """Legacy vehicle model with privacy extensions"""
    __tablename__ = "vehicles"

    vehicle_id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String(20), unique=True, nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.driver_id"))
    model = Column(String(50))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Privacy extensions
    plate_number_hash = Column(String(64))  # Privacy: hashed plate number
    model_category = Column(String(50))  # Privacy: anonymized model category

    # Relationships
    driver = relationship("Driver", back_populates="vehicles")
    telemetry = relationship("Telemetry", back_populates="vehicle")
    events = relationship("Event", back_populates="vehicle")


class Telemetry(Base):
    """Enhanced telemetry data model with semantic extensions"""
    __tablename__ = "telemetry"

    telemetry_id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.vehicle_id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float, nullable=False)
    acceleration = Column(Float)
    engine_temp = Column(Float)
    fuel_level = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Semantic extensions
    gps_accuracy = Column(Float, default=10.0)  # GPS accuracy in meters
    data_quality_score = Column(Float, default=0.8)  # Semantic: data trustworthiness
    is_validated = Column(Boolean, default=False)
    semantic_context = Column(Text)  # JSON string of semantic context
    map_matched = Column(Boolean, default=False)
    matched_location_id = Column(String(32))
    match_confidence = Column(Float)
    provenance_id = Column(String(64))  # Data provenance tracking

    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry")


class Event(Base):
    """Enhanced event model with explainability"""
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.vehicle_id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    speed = Column(Float)
    acceleration = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    severity = Column(String(20), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Explainability extensions
    confidence_score = Column(Float, default=0.8)  # AI model confidence
    explanation = Column(Text)  # Explainable AI: why this event occurred
    causal_factors = Column(Text)  # JSON string of contributing factors
    ai_detected = Column(Boolean, default=False)  # Whether detected by AI

    # Relationships
    vehicle = relationship("Vehicle", back_populates="events")


class Location(Base):
    """Enhanced location model with semantic attributes"""
    __tablename__ = "locations"

    location_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    zone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Semantic extensions
    zone_type = Column(String(50))  # Academic, Residential, Commercial, etc.
    is_formal_path = Column(Boolean, default=True)  # Distinguishes roads from footpaths
    safety_score = Column(Float, default=0.8)
    capacity = Column(Integer)  # For parking zones
    operating_hours = Column(Text)  # JSON string of operating hours


class Anomaly(Base):
    """AI-detected anomaly storage"""
    __tablename__ = "anomalies"

    anomaly_id = Column(String(64), primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    anomaly_type = Column(String(50), nullable=False)
    severity_score = Column(Float, nullable=False)
    detection_model = Column(String(50))
    confidence = Column(Float)
    explanation = Column(Text)
    causal_factors = Column(Text)  # JSON string
    affected_entities = Column(Text)  # JSON string of affected vehicle/driver IDs
    recommended_action = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class EvaluationResult(Base):
    """Model evaluation results storage"""
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), nullable=False)
    dataset = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Metrics
    accuracy = Column(Float)
    precision = Column(Float)
    recall = Column(Float)
    f1_score = Column(Float)
    auc_roc = Column(Float)
    mse = Column(Float)
    mae = Column(Float)
    rmse = Column(Float)

    # Performance
    inference_time_ms = Column(Float)
    memory_usage_mb = Column(Float)
    model_size_mb = Column(Float)

    # Custom metrics
    spatial_accuracy = Column(Float)
    temporal_consistency = Column(Float)
    anomaly_detection_rate = Column(Float)
    business_value_score = Column(Float)
