"""
MakFleet Prototype - SQLAlchemy Base
Shared Base class to avoid circular imports
"""
from sqlalchemy.orm import declarative_base

# Create Base class for all models
Base = declarative_base()