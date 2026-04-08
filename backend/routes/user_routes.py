"""
User profile and settings routes for MakFleet
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

router = APIRouter()

class ProfileUpdateRequest(BaseModel):
    name: str
    email: str
    role: Optional[str] = None
    phone: Optional[str] = None
    emailNotifications: Optional[bool] = None
    smsAlerts: Optional[bool] = None

class SettingsUpdateRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    desktopNotifications: Optional[bool] = None
    soundAlerts: Optional[bool] = None
    analytics: Optional[bool] = None
    locationTracking: Optional[bool] = None

@router.post("/api/profile/update")
async def update_profile(request: ProfileUpdateRequest):
    """Update user profile settings"""
    # In a real application, this would update the database
    # For now, we just return success
    return {
        "success": True,
        "message": "Profile updated successfully",
        "data": request.model_dump()
    }

@router.post("/api/settings/update")
async def update_settings(request: SettingsUpdateRequest):
    """Update user application settings"""
    # In a real application, this would update the database
    # For now, we just return success
    return {
        "success": True,
        "message": "Settings saved successfully",
        "data": request.model_dump()
    }

@router.get("/api/profile")
async def get_profile():
    """Get current user profile"""
    # Return default profile
    return {
        "success": True,
        "data": {
            "id": "USR_001",
            "name": "Admin User",
            "email": "admin@makfleet.ac.ug",
            "role": "admin",
            "phone": "+256 700 000 001",
            "status": "active",
            "emailNotifications": True,
            "smsAlerts": False
        }
    }

@router.get("/api/settings")
async def get_settings():
    """Get user application settings"""
    return {
        "success": True,
        "data": {
            "theme": "light",
            "language": "English",
            "desktopNotifications": True,
            "soundAlerts": False,
            "analytics": True,
            "locationTracking": True
        }
    }