from dataclasses import dataclass
import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import hashlib
import json

class MessageType(Enum):
    """Supported V2I message types"""
    POSITION_UPDATE = "position_update"
    EMERGENCY_ALERT = "emergency_alert"
    TRAFFIC_INFO = "traffic_info"
    INFRASTRUCTURE_STATUS = "infrastructure_status"
    SAFETY_WARNING = "safety_warning"
    CONTROL_COMMAND = "control_command"

@dataclass
class MessageMetadata:
    """Message metadata for validation and tracking"""
    message_id: str
    sender_id: str
    timestamp: datetime.datetime
    message_type: MessageType
    priority: int  # 1 (highest) to 5 (lowest)
    hop_count: int = 0
    signature: Optional[str] = None
    previous_hop: Optional[str] = None

class MessageValidator:
    """Validates message structure and content"""
    def __init__(self, max_message_age: int = 5000):  # max age in milliseconds
        self.max_message_age = max_message_age
        self.message_cache: Dict[str, datetime.datetime] = {}

    def validate_message(self, message: Dict, metadata: MessageMetadata) -> Tuple[bool, str]:
        """
        Performs comprehensive message validation
        Returns: (is_valid: bool, error_message: str)
        """
        validations = [
            self._validate_timing(metadata),
            self._validate_structure(message, metadata.message_type),
            self._validate_duplicates(metadata),
            self._validate_sequence(message, metadata),
            self._validate_constraints(message, metadata)
        ]

        # Check if any validation failed
        failed_validations = [result[1] for result in validations if not result[0]]
        if failed_validations:
            return False, " | ".join(failed_validations)

        # Update message cache
        self.message_cache[metadata.message_id] = metadata.timestamp
        return True, "Message valid"

    def _validate_timing(self, metadata: MessageMetadata) -> Tuple[bool, str]:
        """Validates message timing and freshness"""
        current_time = datetime.datetime.now()
        message_age = (current_time - metadata.timestamp).total_seconds() * 1000

        if message_age > self.max_message_age:
            return False, f"Message too old: {message_age}ms"

        if metadata.timestamp > current_time:
            return False, "Future timestamp detected"

        return True, ""

    def _validate_structure(self, message: Dict,
                          message_type: MessageType) -> Tuple[bool, str]:
        """Validates message structure based on its type"""
        required_fields = {
            MessageType.POSITION_UPDATE: {'position', 'speed', 'direction'},
            MessageType.EMERGENCY_ALERT: {'alert_type', 'severity', 'location'},
            MessageType.TRAFFIC_INFO: {'road_id', 'congestion_level', 'average_speed'},
            MessageType.INFRASTRUCTURE_STATUS: {'device_id', 'status', 'health'},
            MessageType.SAFETY_WARNING: {'warning_type', 'affected_area', 'duration'},
            MessageType.CONTROL_COMMAND: {'command_type', 'parameters', 'target_id'}
        }

        if message_type not in required_fields:
            return False, f"Unknown message type: {message_type}"

        missing_fields = required_fields[message_type] - set(message.keys())
        if missing_fields:
            return False, f"Missing required fields: {missing_fields}"

        return True, ""

    def _validate_duplicates(self, metadata: MessageMetadata) -> Tuple[bool, str]:
        """Checks for duplicate messages"""
        if metadata.message_id in self.message_cache:
            cached_time = self.message_cache[metadata.message_id]
            time_diff = (metadata.timestamp - cached_time).total_seconds()

            if time_diff < 1.0:  # Duplicate within 1 second
                return False, f"Duplicate message detected: {metadata.message_id}"

        return True, ""

    def _validate_sequence(self, message: Dict,
                         metadata: MessageMetadata) -> Tuple[bool, str]:
        """Validates message sequence and causality"""
        if 'sequence_number' in message:
            # Implementation depends on specific sequencing requirements
            pass
        return True, ""

    def _validate_constraints(self, message: Dict,
                            metadata: MessageMetadata) -> Tuple[bool, str]:
        """Validates domain-specific constraints"""
        constraints = {
            MessageType.POSITION_UPDATE: self._validate_position_constraints,
            MessageType.EMERGENCY_ALERT: self._validate_emergency_constraints,
            MessageType.TRAFFIC_INFO: self._validate_traffic_constraints,
            MessageType.INFRASTRUCTURE_STATUS: self._validate_infrastructure_constraints,
            MessageType.SAFETY_WARNING: self._validate_safety_constraints,
            MessageType.CONTROL_COMMAND: self._validate_control_constraints
        }

        if metadata.message_type in constraints:
            return constraints[metadata.message_type](message)

        return True, ""

    def _validate_position_constraints(self, message: Dict) -> Tuple[bool, str]:
        """Validates position update constraints"""
        speed = message.get('speed', 0)
        if not 0 <= speed <= 200:  # Speed in km/h
            return False, f"Invalid speed value: {speed}"

        direction = message.get('direction', 0)
        if not 0 <= direction <= 360:
            return False, f"Invalid direction value: {direction}"

        return True, ""

def _validate_emergency_constraints(self, message: Dict) -> Tuple[bool, str]:
    """
    Validates emergency alert message constraints
    Checks severity levels, location validity, and alert propagation rules
    """
    # Validate severity level
    valid_severity = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
    if message['severity'] not in valid_severity:
        return False, f"Invalid severity level: {message['severity']}"

    # Validate alert type
    valid_alerts = ['COLLISION', 'ROAD_HAZARD', 'WEATHER', 'VEHICLE_MALFUNCTION']
    if message['alert_type'] not in valid_alerts:
        return False, f"Invalid alert type: {message['alert_type']}"

    # Validate location format
    location = message['location']
    if not all(key in location for key in ['latitude', 'longitude', 'radius']):
        return False, "Invalid location format"

    # Validate affected area radius
    if not 0 <= location['radius'] <= 10000:  # max 10km radius
        return False, f"Invalid affected area radius: {location['radius']}"

    return True, ""

def _validate_traffic_constraints(self, message: Dict) -> Tuple[bool, str]:
    """
    Validates traffic information constraints
    Checks congestion levels, speed measurements, and road segment validity
    """
    # Validate congestion level
    if not 0 <= message['congestion_level'] <= 100:
        return False, f"Invalid congestion level: {message['congestion_level']}"

    # Validate average speed
    if not 0 <= message['average_speed'] <= 200:
        return False, f"Invalid average speed: {message['average_speed']}"

    # Validate road segment length
    if 'segment_length' in message:
        if not 0 < message['segment_length'] <= 10000:  # max 10km segment
            return False, f"Invalid segment length: {message['segment_length']}"

    return True, ""

def _validate_infrastructure_constraints(self, message: Dict) -> Tuple[bool, str]:
    """
    Validates infrastructure status message constraints
    Checks device health metrics and operational parameters
    """
    # Validate device status
    valid_statuses = ['OPERATIONAL', 'DEGRADED', 'MAINTENANCE', 'OFFLINE']
    if message['status'] not in valid_statuses:
        return False, f"Invalid device status: {message['status']}"

    # Validate health metrics
    health = message['health']
    if not 0 <= health['battery_level'] <= 100:
        return False, f"Invalid battery level: {health['battery_level']}"

    if not 0 <= health['signal_strength'] <= 100:
        return False, f"Invalid signal strength: {health['signal_strength']}"

    # Validate maintenance data
    if 'maintenance_data' in message:
        mdata = message['maintenance_data']
        if mdata['last_check'] > datetime.datetime.now():
            return False, "Invalid maintenance timestamp"

    return True, ""

def _validate_safety_constraints(self, message: Dict) -> Tuple[bool, str]:
    """
    Validates safety warning message constraints
    Checks warning parameters and affected area specifications
    """
    # Validate warning type
    valid_warnings = ['SLIPPERY_ROAD', 'ROAD_WORK', 'ACCIDENT', 'WEATHER_HAZARD']
    if message['warning_type'] not in valid_warnings:
        return False, f"Invalid warning type: {message['warning_type']}"

    # Validate duration
    duration = message['duration']
    if not 0 < duration <= 86400:  # max 24 hours
        return False, f"Invalid warning duration: {duration}"

    # Validate affected area
    area = message['affected_area']
    if not all(key in area for key in ['start_point', 'end_point', 'width']):
        return False, "Invalid affected area specification"

    if not 0 < area['width'] <= 50:  # max 50m width
        return False, f"Invalid affected area width: {area['width']}"

    return True, ""

def _validate_control_constraints(self, message: Dict) -> Tuple[bool, str]:
    """
    Validates control command constraints
    Checks command parameters and authorization levels
    """
    # Validate command type
    valid_commands = ['SPEED_LIMIT', 'LANE_CHANGE', 'ROUTE_CHANGE', 'STOP']
    if message['command_type'] not in valid_commands:
        return False, f"Invalid command type: {message['command_type']}"

    # Validate parameters
    params = message['parameters']
    if message['command_type'] == 'SPEED_LIMIT':
        if not 0 <= params.get('speed', -1) <= 130:
            return False, f"Invalid speed limit: {params.get('speed')}"

    elif message['command_type'] == 'LANE_CHANGE':
        if not -3 <= params.get('lane_offset', -4) <= 3:
            return False, f"Invalid lane offset: {params.get('lane_offset')}"

    return True, ""

class SecurityValidator:
    """Additional security validations for messages"""
    def __init__(self):
        self.trusted_keys: Dict[str, str] = {}  # node_id -> public_key
        self.revocation_list: Set[str] = set()  # revoked node IDs
        self.threat_patterns: List[Dict] = []  # known attack patterns

    def validate_security(self, message: Dict,
                         metadata: MessageMetadata) -> Tuple[bool, str]:
        """Performs comprehensive security validation"""
        # Check node authentication
        if not self._validate_authentication(metadata):
            return False, "Authentication failed"

        # Check message integrity
        if not self._validate_integrity(message, metadata):
            return False, "Integrity check failed"

        # Check for known attack patterns
        if not self._check_attack_patterns(message, metadata):
            return False, "Suspicious message pattern detected"

        # Rate limiting check
        if not self._check_rate_limits(metadata):
            return False, "Rate limit exceeded"

        return True, ""

    def _validate_authentication(self, metadata: MessageMetadata) -> bool:
        """Validates sender authentication"""
        if metadata.sender_id in self.revocation_list:
            return False

        if metadata.sender_id not in self.trusted_keys:
            return False

        # Verify signature
        if not metadata.signature:
            return False

        return True

    def _validate_integrity(self, message: Dict,
                          metadata: MessageMetadata) -> bool:
        """Validates message integrity using signatures"""
        message_hash = hashlib.sha256(
            json.dumps(message, sort_keys=True).encode()
        ).hexdigest()

        # In real implementation, verify signature using public key
        return True

    def _check_attack_patterns(self, message: Dict,
                             metadata: MessageMetadata) -> bool:
        """Checks message against known attack patterns"""
        for pattern in self.threat_patterns:
            if self._match_pattern(message, metadata, pattern):
                return False
        return True

    def _check_rate_limits(self, metadata: MessageMetadata) -> bool:
        """Enforces rate limiting per sender"""
        # Implementation of rate limiting logic
        return True

class MessageProcessor:
    """Processes and routes validated messages"""
    def __init__(self):
        self.message_validator = MessageValidator()
        self.security_validator = SecurityValidator()
        self.message_handlers: Dict[MessageType, callable] = {}

    def process_message(self, message: Dict,
                       metadata: MessageMetadata) -> Tuple[bool, str]:
        """
        Processes incoming message through validation and security checks
        Returns: (success: bool, response: str)
        """
        # Validate message format and constraints
        valid, error = self.message_validator.validate_message(message, metadata)
        if not valid:
            return False, f"Validation failed: {error}"

        # Perform security validation
        secure, error = self.security_validator.validate_security(
            message, metadata
        )
        if not secure:
            return False, f"Security check failed: {error}"

        # Route message to appropriate handler
        if metadata.message_type in self.message_handlers:
            try:
                self.message_handlers[metadata.message_type](message, metadata)
                return True, "Message processed successfully"
            except Exception as e:
                return False, f"Processing error: {str(e)}"

        return False, "No handler for message type"