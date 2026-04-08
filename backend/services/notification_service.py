"""
MakFleet Notification Service
Handles notifications, alerts, and user preferences
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import uuid


class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    SUCCESS = "success"
    SYSTEM = "system"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


@dataclass
class Notification:
    """Notification data structure"""
    id: str
    type: str
    title: str
    message: str
    timestamp: str
    read: bool = False
    channel: str = "in_app"
    priority: int = 1  # 1=low, 2=medium, 3=high, 4=critical
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'timestamp': self.timestamp,
            'read': self.read,
            'channel': self.channel,
            'priority': self.priority,
            'metadata': self.metadata or {}
        }


class NotificationService:
    """Service for managing notifications"""
    
    def __init__(self):
        self.notifications: Dict[str, List[Notification]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.notification_queue: List[Notification] = []
    
    def create_notification(self, user_id: str, notification_type: str, 
                          title: str, message: str, 
                          channel: str = "in_app", 
                          priority: int = 2,
                          metadata: Dict[str, Any] = None) -> Notification:
        """Create and store a notification"""
        notification = Notification(
            id=str(uuid.uuid4()),
            type=notification_type,
            title=title,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
            channel=channel,
            priority=priority,
            metadata=metadata or {}
        )
        
        if user_id not in self.notifications:
            self.notifications[user_id] = []
        
        self.notifications[user_id].append(notification)
        
        # Add to queue for processing
        self.notification_queue.append(notification)
        
        return notification
    
    def get_notifications(self, user_id: str, limit: int = 50, 
                         unread_only: bool = False,
                         notification_type: str = None) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        if user_id not in self.notifications:
            return []
        
        notifications = self.notifications[user_id]
        
        # Filter by unread
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        # Filter by type
        if notification_type:
            notifications = [n for n in notifications if n.type == notification_type]
        
        # Sort by timestamp (newest first)
        notifications.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Limit results
        notifications = notifications[:limit]
        
        return [n.to_dict() for n in notifications]
    
    def mark_as_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a notification as read"""
        if user_id not in self.notifications:
            return False
        
        for notification in self.notifications[user_id]:
            if notification.id == notification_id:
                notification.read = True
                return True
        
        return False
    
    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        if user_id not in self.notifications:
            return 0
        
        count = 0
        for notification in self.notifications[user_id]:
            if not notification.read:
                notification.read = True
                count += 1
        
        return count
    
    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        """Delete a notification"""
        if user_id not in self.notifications:
            return False
        
        original_length = len(self.notifications[user_id])
        self.notifications[user_id] = [
            n for n in self.notifications[user_id] 
            if n.id != notification_id
        ]
        
        return len(self.notifications[user_id]) < original_length
    
    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications"""
        if user_id not in self.notifications:
            return 0
        
        return sum(1 for n in self.notifications[user_id] if not n.read)
    
    def set_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Set notification preferences for a user"""
        self.user_preferences[user_id] = {
            'channels': preferences.get('channels', ['in_app']),
            'types': preferences.get('types', ['info', 'warning', 'danger', 'success']),
            'quiet_hours': preferences.get('quiet_hours', {'start': '22:00', 'end': '07:00'}),
            'email_notifications': preferences.get('email_notifications', False),
            'sms_notifications': preferences.get('sms_notifications', False),
            'push_notifications': preferences.get('push_notifications', True),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        return self.user_preferences[user_id]
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get notification preferences for a user"""
        if user_id not in self.user_preferences:
            # Return default preferences
            return {
                'channels': ['in_app'],
                'types': ['info', 'warning', 'danger', 'success'],
                'quiet_hours': {'start': '22:00', 'end': '07:00'},
                'email_notifications': False,
                'sms_notifications': False,
                'push_notifications': True,
                'updated_at': None
            }
        
        return self.user_preferences[user_id]
    
    def create_system_alert(self, alert_type: str, message: str, 
                          affected_users: List[str] = None,
                          priority: int = 3) -> List[Notification]:
        """Create a system-wide alert"""
        notifications = []
        
        titles = {
            'anomaly_detected': '🔍 AI Anomaly Detected',
            'system_maintenance': '🔧 System Maintenance',
            'data_quality_alert': '📊 Data Quality Alert',
            'security_notice': '🔒 Security Notice',
            'performance_warning': '⚡ Performance Warning'
        }
        
        title = titles.get(alert_type, 'System Alert')
        
        # If no specific users, notify all users
        target_users = affected_users or list(self.notifications.keys())
        
        for user_id in target_users:
            notification = self.create_notification(
                user_id=user_id,
                notification_type='system',
                title=title,
                message=message,
                priority=priority,
                metadata={'alert_type': alert_type}
            )
            notifications.append(notification)
        
        return notifications
    
    def get_notification_stats(self, user_id: str) -> Dict[str, Any]:
        """Get notification statistics for a user"""
        if user_id not in self.notifications:
            return {'total': 0, 'unread': 0, 'by_type': {}}
        
        notifications = self.notifications[user_id]
        unread = sum(1 for n in notifications if not n.read)
        
        by_type = {}
        for notification in notifications:
            ntype = notification.type
            by_type[ntype] = by_type.get(ntype, 0) + 1
        
        return {
            'total': len(notifications),
            'unread': unread,
            'read': len(notifications) - unread,
            'by_type': by_type
        }
    
    def process_queue(self) -> int:
        """Process notification queue (would send emails, push notifications, etc.)"""
        processed = 0
        
        while self.notification_queue:
            notification = self.notification_queue.pop(0)
            # In production, would:
            # - Send email via SMTP/SendGrid
            # - Send SMS via Twilio
            # - Send push notification via Firebase
            # - Log to audit trail
            processed += 1
        
        return processed
    
    def cleanup_old_notifications(self, user_id: str, days_old: int = 30) -> int:
        """Remove notifications older than specified days"""
        if user_id not in self.notifications:
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        original_length = len(self.notifications[user_id])
        
        self.notifications[user_id] = [
            n for n in self.notifications[user_id]
            if datetime.fromisoformat(n.timestamp) > cutoff_date
        ]
        
        return original_length - len(self.notifications[user_id])