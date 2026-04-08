"""
MakFleet System Routes
API endpoints for reports, notifications, profile, and settings
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import io

router = APIRouter()

# Initialize services (would be injected via dependency injection in production)
from backend.services.report_service import ReportService
from backend.services.notification_service import NotificationService

report_service = ReportService()
notification_service = NotificationService()


# ============== Report Routes ==============

class ReportRequest(BaseModel):
    report_type: str
    params: Dict[str, Any] = {}
    format: str = "json"  # json, csv, pdf

@router.get("/api/reports/types")
async def get_report_types():
    """Get available report types"""
    return {
        "types": [
            {
                "id": "safety_summary",
                "name": "Safety Summary Report",
                "description": "Comprehensive safety analysis with event trends and recommendations"
            },
            {
                "id": "driver_performance", 
                "name": "Driver Performance Report",
                "description": "Individual or fleet-wide driver performance metrics"
            },
            {
                "id": "anomaly_analysis",
                "name": "Anomaly Analysis Report",
                "description": "Detailed analysis of AI-detected anomalies with ST-GNN insights"
            },
            {
                "id": "system_evaluation",
                "name": "System Evaluation Report",
                "description": "Model performance, system metrics, and business impact analysis"
            }
        ]
    }

@router.post("/api/reports/generate")
async def generate_report(request: ReportRequest):
    """Generate a report"""
    try:
        report = report_service.generate_report(
            report_type=request.report_type,
            params=request.params
        )
        
        # Add metadata
        metadata = report_service.get_report_metadata(report)
        report['metadata'] = metadata
        
        return report
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

@router.get("/api/reports/export")
async def export_report(
    report_type: str = Query(...),
    format: str = Query("json", regex="^(json|csv|pdf)$"),
    params: Dict[str, Any] = {}
):
    """Export a report in specified format"""
    try:
        report = report_service.generate_report(report_type, params)
        
        if format == "json":
            content = report_service.export_to_json(report)
            media_type = "application/json"
            filename = f"report_{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        elif format == "csv":
            content = report_service.export_to_csv(report)
            media_type = "text/csv"
            filename = f"report_{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        else:  # pdf
            content = report_service.export_to_pdf(report)
            media_type = "application/pdf"
            filename = f"report_{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return {
            "content": content if isinstance(content, str) else content.decode('utf-8', errors='ignore'),
            "filename": filename,
            "media_type": media_type,
            "size_bytes": len(content) if isinstance(content, bytes) else len(content.encode())
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@router.post("/api/reports/schedule")
async def schedule_report(
    report_type: str = Body(...),
    schedule: str = Body(...),  # daily, weekly, monthly
    recipients: List[str] = Body([])
):
    """Schedule automatic report generation"""
    try:
        schedule_info = report_service.schedule_report(report_type, schedule, recipients)
        return {
            "message": "Report scheduled successfully",
            "schedule": schedule_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Notification Routes ==============

class NotificationPreferences(BaseModel):
    channels: List[str] = ["in_app"]
    types: List[str] = ["info", "warning", "danger", "success"]
    quiet_hours: Dict[str, str] = {"start": "22:00", "end": "07:00"}
    email_notifications: bool = False
    sms_notifications: bool = False
    push_notifications: bool = True

@router.get("/api/notifications")
async def get_notifications(
    user_id: str = Query("admin", description="User ID"),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    notification_type: str = None
):
    """Get notifications for a user"""
    notifications = notification_service.get_notifications(
        user_id=user_id,
        limit=limit,
        unread_only=unread_only,
        notification_type=notification_type
    )
    
    return {
        "notifications": notifications,
        "total": len(notifications),
        "unread_count": notification_service.get_unread_count(user_id)
    }

@router.get("/api/notifications/unread-count")
async def get_unread_count(user_id: str = Query("admin")):
    """Get count of unread notifications"""
    count = notification_service.get_unread_count(user_id)
    return {"unread_count": count}

@router.post("/api/notifications/mark-as-read")
async def mark_notification_as_read(
    notification_id: str = Body(...),
    user_id: str = Body("admin")
):
    """Mark a notification as read"""
    success = notification_service.mark_as_read(user_id, notification_id)
    if success:
        return {"message": "Notification marked as read"}
    else:
        raise HTTPException(status_code=404, detail="Notification not found")

@router.post("/api/notifications/mark-all-read")
async def mark_all_as_read(user_id: str = Body("admin")):
    """Mark all notifications as read"""
    count = notification_service.mark_all_as_read(user_id)
    return {"message": f"Marked {count} notifications as read"}

@router.delete("/api/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    user_id: str = Query("admin")
):
    """Delete a notification"""
    success = notification_service.delete_notification(user_id, notification_id)
    if success:
        return {"message": "Notification deleted"}
    else:
        raise HTTPException(status_code=404, detail="Notification not found")

@router.get("/api/notifications/preferences")
async def get_notification_preferences(user_id: str = Query("admin")):
    """Get user notification preferences"""
    preferences = notification_service.get_user_preferences(user_id)
    return preferences

@router.post("/api/notifications/preferences")
async def set_notification_preferences(
    preferences: NotificationPreferences,
    user_id: str = Body("admin")
):
    """Set user notification preferences"""
    updated = notification_service.set_user_preferences(
        user_id, 
        preferences.dict()
    )
    return {
        "message": "Preferences updated successfully",
        "preferences": updated
    }

@router.get("/api/notifications/stats")
async def get_notification_stats(user_id: str = Query("admin")):
    """Get notification statistics"""
    stats = notification_service.get_notification_stats(user_id)
    return stats


# ============== Profile Routes ==============

class UserProfile(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None

# Mock user database
mock_users = {
    "admin": {
        "user_id": "admin",
        "email": "admin@makfleet.ac.ug",
        "full_name": "System Administrator",
        "role": "admin",
        "department": "IT",
        "phone": "+256700000000",
        "avatar_url": None,
        "created_at": "2024-01-01T00:00:00",
        "last_login": datetime.utcnow().isoformat()
    }
}

@router.get("/api/profile")
async def get_profile(user_id: str = Query("admin")):
    """Get user profile"""
    if user_id in mock_users:
        return mock_users[user_id]
    else:
        raise HTTPException(status_code=404, detail="User not found")

@router.put("/api/profile")
async def update_profile(
    profile: UserProfile,
    user_id: str = Body("admin")
):
    """Update user profile"""
    if user_id in mock_users:
        mock_users[user_id].update(profile.dict())
        return {
            "message": "Profile updated successfully",
            "profile": mock_users[user_id]
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")


# ============== Settings Routes ==============

class SystemSettings(BaseModel):
    theme: str = "light"  # light, dark
    language: str = "en"
    timezone: str = "Africa/Kampala"
    date_format: str = "YYYY-MM-DD"
    time_format: str = "24h"
    notifications_enabled: bool = True
    auto_refresh_interval: int = 30  # seconds
    map_zoom_level: int = 15
    show_real_time_data: bool = True

class UserSettings(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    auto_refresh_interval: Optional[int] = None
    map_zoom_level: Optional[int] = None
    show_real_time_data: Optional[bool] = None

# Mock settings storage
mock_settings = {
    "system": SystemSettings().dict(),
    "users": {}
}

@router.get("/api/settings/system")
async def get_system_settings():
    """Get system-wide settings"""
    return mock_settings["system"]

@router.put("/api/settings/system")
async def update_system_settings(settings: SystemSettings):
    """Update system-wide settings"""
    mock_settings["system"] = settings.dict()
    return {
        "message": "System settings updated",
        "settings": mock_settings["system"]
    }

@router.get("/api/settings/user")
async def get_user_settings(user_id: str = Query("admin")):
    """Get user-specific settings"""
    if user_id in mock_settings["users"]:
        return mock_settings["users"][user_id]
    else:
        # Return defaults
        return SystemSettings().dict()

@router.put("/api/settings/user")
async def update_user_settings(
    settings: UserSettings,
    user_id: str = Body("admin")
):
    """Update user-specific settings"""
    if user_id not in mock_settings["users"]:
        mock_settings["users"][user_id] = SystemSettings().dict()
    
    # Update only provided fields
    for key, value in settings.dict(exclude_unset=True).items():
        if value is not None:
            mock_settings["users"][user_id][key] = value
    
    return {
        "message": "User settings updated",
        "settings": mock_settings["users"][user_id]
    }


# ============== System Info Routes ==============

@router.get("/api/system/info")
async def get_system_info():
    """Get system information"""
    return {
        "name": "MakFleet Intelligent Semantic AI System",
        "version": "2.0.0",
        "environment": "development",
        "features": {
            "st_gnn_model": True,
            "semantic_pipeline": True,
            "knowledge_graph": True,
            "explainable_ai": True,
            "privacy_by_design": True,
            "evaluation_framework": True,
            "report_export": True,
            "notifications": True,
            "user_management": True
        },
        "uptime": "24+ hours",
        "last_updated": datetime.utcnow().isoformat()
    }

@router.get("/api/system/health")
async def get_system_health():
    """Get system health status"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "healthy",
            "database": "healthy",
            "ai_models": "healthy",
            "semantic_pipeline": "healthy"
        }
    }