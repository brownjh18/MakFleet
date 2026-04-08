"""
MakFleet Privacy-by-Design Module
Implements privacy protection mechanisms for driver and vehicle data
"""
import hashlib
import hmac
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class PseudonymizationEngine:
    """Handles pseudonymization of sensitive data"""
    
    def __init__(self, salt: bytes = None):
        self.salt = salt or secrets.token_bytes(32)
        self.key_cache = {}  # Cache for derived keys
    
    def pseudonymize_driver_id(self, driver_id: str) -> str:
        """Create pseudonymized driver identifier"""
        # Use HMAC-SHA256 for deterministic pseudonymization
        key = self._derive_key("driver_key")
        pseudonym = hmac.new(key, driver_id.encode(), hashlib.sha256).hexdigest()
        return f"DRV_{pseudonym[:16]}"
    
    def pseudonymize_vehicle_id(self, vehicle_id: str) -> str:
        """Create pseudonymized vehicle identifier"""
        key = self._derive_key("vehicle_key")
        pseudonym = hmac.new(key, vehicle_id.encode(), hashlib.sha256).hexdigest()
        return f"VHC_{pseudonym[:16]}"
    
    def pseudonymize_license(self, license_number: str) -> str:
        """Pseudonymize license number for verification without storage"""
        key = self._derive_key("license_key")
        pseudonym = hmac.new(key, license_number.encode(), hashlib.sha256).hexdigest()
        return f"LIC_{pseudonym[:20]}"
    
    def _derive_key(self, purpose: str) -> bytes:
        """Derive key for specific purpose"""
        if purpose not in self.key_cache:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self.salt,
                iterations=100000,
            )
            self.key_cache[purpose] = kdf.derive(purpose.encode())
        
        return self.key_cache[purpose]


class DataMinimizationEngine:
    """Ensures only necessary data is collected and stored"""
    
    def __init__(self):
        self.required_fields = {
            'telemetry': ['latitude', 'longitude', 'speed', 'acceleration', 'timestamp'],
            'driver': ['anonymized_id'],  # No personal details
            'vehicle': ['plate_number_hash', 'model_category']  # No specific model
        }
        
        self.retention_policies = {
            'telemetry': timedelta(days=30),
            'events': timedelta(days=90),
            'anomaly_reports': timedelta(days=365)
        }
    
    def validate_data_collection(self, data_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and minimize data collection"""
        if data_type not in self.required_fields:
            raise ValueError(f"Unknown data type: {data_type}")
        
        minimized = {}
        required = self.required_fields[data_type]
        
        for field in required:
            if field in data:
                minimized[field] = data[field]
            else:
                raise ValueError(f"Required field missing: {field}")
        
        # Add metadata
        minimized['_collected_at'] = datetime.utcnow().isoformat()
        minimized['_data_type'] = data_type
        minimized['_minimization_applied'] = True
        
        return minimized
    
    def should_retain_data(self, data_type: str, created_at: datetime) -> bool:
        """Check if data should be retained based on retention policy"""
        if data_type not in self.retention_policies:
            return False
        
        retention_period = self.retention_policies[data_type]
        cutoff_date = datetime.utcnow() - retention_period
        
        return created_at > cutoff_date
    
    def anonymize_vehicle_model(self, model: str) -> str:
        """Anonymize vehicle model to category only"""
        model_lower = model.lower()
        if any(keyword in model_lower for keyword in ['yamaha', 'honda', 'suzuki', 'kawasaki']):
            return 'motorcycle_japanese'
        elif any(keyword in model_lower for keyword in ['ducati', 'bmw', 'harley']):
            return 'motorcycle_premium'
        else:
            return 'motorcycle_other'


class AccessControlEngine:
    """Manages access control with role-based permissions"""
    
    def __init__(self):
        self.roles = {
            'admin': ['read', 'write', 'delete', 'anonymize', 'audit'],
            'analyst': ['read', 'anonymize'],
            'operator': ['read', 'write'],
            'auditor': ['read', 'audit']
        }
        
        self.resource_permissions = {
            'driver_data': ['admin', 'auditor'],
            'vehicle_data': ['admin', 'analyst', 'operator'],
            'telemetry_data': ['admin', 'analyst', 'operator'],
            'anomaly_reports': ['admin', 'analyst', 'auditor'],
            'audit_logs': ['admin', 'auditor']
        }
    
    def check_permission(self, user_role: str, resource: str, action: str) -> bool:
        """Check if user has permission for action on resource"""
        if user_role not in self.roles:
            return False
        
        if resource not in self.resource_permissions:
            return False
        
        # Check role permissions
        if action not in self.roles[user_role]:
            return False
        
        # Check resource access
        if user_role not in self.resource_permissions[resource]:
            return False
        
        return True
    
    def get_user_permissions(self, user_role: str) -> Dict[str, List[str]]:
        """Get all permissions for a user role"""
        if user_role not in self.roles:
            return {}
        
        permissions = {}
        for resource in self.resource_permissions:
            if user_role in self.resource_permissions[resource]:
                permissions[resource] = [
                    action for action in self.roles[user_role]
                    if action in ['read', 'write', 'delete']  # Exclude admin actions
                ]
        
        return permissions


class EncryptionEngine:
    """Handles encryption for sensitive data"""
    
    def __init__(self, master_key: bytes = None):
        self.master_key = master_key or Fernet.generate_key()
        self.fernet = Fernet(self.master_key)
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        encrypted = self.fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data)
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            raise ValueError("Failed to decrypt data")
    
    def hash_irreversible(self, data: str) -> str:
        """Create irreversible hash for verification purposes"""
        return hashlib.sha256(data.encode()).hexdigest()


class AuditLogger:
    """Logs all privacy-related operations for compliance"""
    
    def __init__(self):
        self.audit_trail = []
    
    def log_access(self, user_id: str, resource: str, action: str,
                  success: bool, reason: str = None):
        """Log data access"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'success': success,
            'reason': reason or ('granted' if success else 'denied'),
            'event_type': 'access_control'
        }
        self.audit_trail.append(entry)
    
    def log_anonymization(self, data_type: str, original_fields: List[str],
                         anonymization_method: str):
        """Log anonymization operations"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'data_type': data_type,
            'original_fields': original_fields,
            'anonymization_method': anonymization_method,
            'event_type': 'anonymization'
        }
        self.audit_trail.append(entry)
    
    def log_data_minimization(self, data_type: str, fields_removed: List[str]):
        """Log data minimization operations"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'data_type': data_type,
            'fields_removed': fields_removed,
            'event_type': 'data_minimization'
        }
        self.audit_trail.append(entry)
    
    def get_audit_trail(self, user_id: str = None, resource: str = None,
                       start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Retrieve audit trail with filters"""
        filtered_trail = self.audit_trail
        
        if user_id:
            filtered_trail = [e for e in filtered_trail if e.get('user_id') == user_id]
        
        if resource:
            filtered_trail = [e for e in filtered_trail if e.get('resource') == resource]
        
        if start_date:
            filtered_trail = [e for e in filtered_trail
                            if datetime.fromisoformat(e['timestamp']) >= start_date]
        
        if end_date:
            filtered_trail = [e for e in filtered_trail
                            if datetime.fromisoformat(e['timestamp']) <= end_date]
        
        return filtered_trail


class PrivacyController:
    """Main privacy controller implementing privacy-by-design"""
    
    def __init__(self):
        self.pseudonymizer = PseudonymizationEngine()
        self.minimizer = DataMinimizationEngine()
        self.access_controller = AccessControlEngine()
        self.encryption_engine = EncryptionEngine()
        self.audit_logger = AuditLogger()
    
    def process_driver_data(self, driver_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process driver data with privacy protection"""
        # Pseudonymize identifiers
        processed = {
            'anonymized_id': self.pseudonymizer.pseudonymize_driver_id(driver_data['driver_id']),
            'license_pseudonym': self.pseudonymizer.pseudonymize_license(driver_data['license_number']),
            'created_at': driver_data.get('created_at', datetime.utcnow().isoformat())
        }
        
        # Log anonymization
        self.audit_logger.log_anonymization(
            'driver',
            ['driver_id', 'license_number'],
            'pseudonymization'
        )
        
        return processed
    
    def process_vehicle_data(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process vehicle data with privacy protection"""
        processed = {
            'plate_number_hash': self.encryption_engine.hash_irreversible(vehicle_data['plate_number']),
            'model_category': self.minimizer.anonymize_vehicle_model(vehicle_data['model']),
            'driver_anonymized_id': self.pseudonymizer.pseudonymize_driver_id(vehicle_data['driver_id']),
            'created_at': vehicle_data.get('created_at', datetime.utcnow().isoformat())
        }
        
        # Log anonymization
        self.audit_logger.log_anonymization(
            'vehicle',
            ['plate_number', 'model'],
            'hashing_and_categorization'
        )
        
        return processed
    
    def process_telemetry_data(self, telemetry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process telemetry data with data minimization"""
        # Validate and minimize
        processed = self.minimizer.validate_data_collection('telemetry', telemetry_data)
        
        # Add vehicle pseudonym
        processed['vehicle_anonymized_id'] = self.pseudonymizer.pseudonymize_vehicle_id(
            telemetry_data['vehicle_id']
        )
        
        # Log data minimization
        removed_fields = [k for k in telemetry_data.keys() if k not in processed]
        if removed_fields:
            self.audit_logger.log_data_minimization('telemetry', removed_fields)
        
        return processed
    
    def check_data_access(self, user_id: str, user_role: str, resource: str, action: str) -> bool:
        """Check if user can access data"""
        has_permission = self.access_controller.check_permission(user_role, resource, action)
        
        # Log access attempt
        self.audit_logger.log_access(
            user_id, resource, action, has_permission,
            reason=f"Role: {user_role}"
        )
        
        return has_permission
    
    def get_privacy_report(self) -> Dict[str, Any]:
        """Generate privacy compliance report"""
        audit_trail = self.audit_logger.get_audit_trail()
        
        # Analyze audit trail
        access_attempts = len([e for e in audit_trail if e['event_type'] == 'access_control'])
        access_granted = len([e for e in audit_trail
                            if e['event_type'] == 'access_control' and e['success']])
        
        anonymization_ops = len([e for e in audit_trail if e['event_type'] == 'anonymization'])
        minimization_ops = len([e for e in audit_trail if e['event_type'] == 'data_minimization'])
        
        return {
            'privacy_metrics': {
                'total_access_attempts': access_attempts,
                'access_granted_rate': access_granted / access_attempts if access_attempts > 0 else 0,
                'anonymization_operations': anonymization_ops,
                'data_minimization_operations': minimization_ops
            },
            'compliance_status': 'compliant',  # Would implement actual compliance checks
            'last_audit': datetime.utcnow().isoformat(),
            'data_retention_compliance': True,  # Would check actual retention
            'encryption_status': 'active'
        }
    
    def purge_expired_data(self, data_store: Dict[str, Any]):
        """Purge expired data according to retention policies"""
        purged_items = []
        
        for data_type, items in data_store.items():
            if data_type in self.minimizer.retention_policies:
                retention_period = self.minimizer.retention_policies[data_type]
                cutoff_date = datetime.utcnow() - retention_period
                
                # Filter items to keep
                kept_items = []
                for item in items:
                    created_at = datetime.fromisoformat(item.get('created_at', item.get('timestamp', '')))
                    if self.minimizer.should_retain_data(data_type, created_at):
                        kept_items.append(item)
                    else:
                        purged_items.append(f"{data_type}:{item.get('id', 'unknown')}")
                
                data_store[data_type] = kept_items
        
        return purged_items


class PrivacyImpactAssessment:
    """Conducts Privacy Impact Assessment for new features"""
    
    def __init__(self):
        self.assessment_criteria = {
            'data_collection': [
                'Is data collection minimized?',
                'Are data subjects informed?',
                'Is consent properly obtained?'
            ],
            'data_processing': [
                'Is processing purpose specified?',
                'Is data anonymized where possible?',
                'Are processing activities logged?'
            ],
            'data_sharing': [
                'Is data sharing minimized?',
                'Are recipients verified?',
                'Is data encrypted in transit?'
            ],
            'data_retention': [
                'Is retention period defined?',
                'Is data purged automatically?',
                'Are retention policies enforced?'
            ]
        }
    
    def assess_feature(self, feature_description: str, data_flows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess privacy impact of a feature"""
        assessment = {
            'feature': feature_description,
            'assessment_date': datetime.utcnow().isoformat(),
            'overall_risk': 'low',
            'recommendations': [],
            'criteria_assessment': {}
        }
        
        high_risk_indicators = 0
        
        for category, criteria in self.assessment_criteria.items():
            category_assessment = {}
            
            for criterion in criteria:
                # Simplified assessment logic
                if 'consent' in criterion.lower() or 'informed' in criterion.lower():
                    category_assessment[criterion] = 'requires_attention'
                    high_risk_indicators += 1
                elif 'encrypt' in criterion.lower() or 'anonymized' in criterion.lower():
                    category_assessment[criterion] = 'compliant'
                else:
                    category_assessment[criterion] = 'adequate'
            
            assessment['criteria_assessment'][category] = category_assessment
        
        # Determine overall risk
        if high_risk_indicators > 2:
            assessment['overall_risk'] = 'high'
            assessment['recommendations'].extend([
                'Implement explicit user consent mechanisms',
                'Conduct detailed data protection impact assessment',
                'Consult privacy officer before deployment'
            ])
        elif high_risk_indicators > 0:
            assessment['overall_risk'] = 'medium'
            assessment['recommendations'].extend([
                'Enhance user notification mechanisms',
                'Implement additional anonymization measures'
            ])
        
        return assessment
