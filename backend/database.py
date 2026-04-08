"""
MakFleet Prototype - Database Configuration
Uses SQLite for demonstration (no PostgreSQL required)
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Use SQLite for demonstration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///makfleet.db"
)

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import Base from base module
from .base import Base


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    # Import models to ensure they are registered
    from . import models
    Base.metadata.create_all(bind=engine)
    print("Database tables created")


def clear_telemetry_and_events():
    """Clear all telemetry and events data - call this on server startup
    to ensure vehicles/events don't appear until simulator is running"""
    from .models import Telemetry, Event
    db = SessionLocal()
    try:
        # Delete all telemetry and events (keep drivers, vehicles, locations)
        db.query(Telemetry).delete(synchronize_session=False)
        db.query(Event).delete(synchronize_session=False)
        db.commit()
        print("Cleared old telemetry and event data")
    except Exception as e:
        print(f"Error clearing data: {e}")
        db.rollback()
    finally:
        db.close()
