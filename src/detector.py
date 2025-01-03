import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import datetime
from collections import defaultdict
from torch.nn import TransformerEncoder, TransformerEncoderLayer

@dataclass
class DetectionResult:
    """Represents the result of intrusion detection analysis"""
    timestamp: datetime.datetime
    threat_detected: bool
    confidence: float
    threat_type: Optional[str]
    affected_nodes: List[str]
    evidence: Dict
    recommendation: str

class V2ITransformerEncoder(nn.Module):
    """Custom transformer encoder for V2I network analysis"""
    def __init__(self,
                 feature_dim: int,
                 n_heads: int = 8,
                 n_layers: int = 6,
                 dropout: float = 0.1):
        super().__init__()

        # Transformer architecture
        encoder_layer = TransformerEncoderLayer(
            d_model=feature_dim,
            nhead=n_heads,
            dim_feedforward=4*feature_dim,
            dropout=dropout,
            batch_first=True
        )

        self.transformer = TransformerEncoder(
            encoder_layer=encoder_layer,
            num_layers=n_layers
        )

        # Additional layers for threat detection
        self.threat_classifier = nn.Sequential(
            nn.Linear(feature_dim, feature_dim//2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(feature_dim//2, feature_dim//4),
            nn.ReLU(),
            nn.Linear(feature_dim//4, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Forward pass through the transformer
        Args:
            x: Input tensor of shape (batch_size, seq_len, feature_dim)
            mask: Attention mask
        Returns:
            Tensor of threat probabilities
        """
        # Pass through transformer
        transformed = self.transformer(x, mask=mask)

        # Global average pooling
        pooled = torch.mean(transformed, dim=1)

        # Threat classification
        threat_prob = self.threat_classifier(pooled)

        return threat_prob

class IntrusionDetector:
    """Main intrusion detection system class"""
    def __init__(self,
                 feature_dim: int = 64,
                 sequence_length: int = 50,
                 detection_threshold: float = 0.75):
        self.feature_dim = feature_dim
        self.sequence_length = sequence_length
        self.detection_threshold = detection_threshold

        # Initialize transformer model
        self.model = V2ITransformerEncoder(feature_dim=feature_dim)

        # Message sequence buffers per node
        self.message_buffers: Dict[str, List[Dict]] = defaultdict(list)

        # Feature extractors for different message types
        self.feature_extractors = {
            'position_update': self._extract_position_features,
            'emergency_alert': self._extract_emergency_features,
            'traffic_info': self._extract_traffic_features,
            'infrastructure_status': self._extract_infrastructure_features,
            'safety_warning': self._extract_safety_features,
            'control_command': self._extract_control_features
        }

    def process_message(self, message: Dict,
                       metadata: MessageMetadata) -> DetectionResult:
        """
        Processes a new message for intrusion detection
        Returns detection result with threat assessment
        """
        # Update message buffer for the sender
        self.message_buffers[metadata.sender_id].append({
            'message': message,
            'metadata': metadata,
            'timestamp': datetime.datetime.now()
        })

        # Maintain buffer size
        if len(self.message_buffers[metadata.sender_id]) > self.sequence_length:
            self.message_buffers[metadata.sender_id].pop(0)

        # Extract features
        features = self._extract_features(
            self.message_buffers[metadata.sender_id]
        )

        # Perform detection
        threat_prob = self._detect_threats(features)

        # Analyze results
        return self._analyze_detection(
            threat_prob,
            message,
            metadata
        )

    def _extract_features(self, message_sequence: List[Dict]) -> torch.Tensor:
        """Extracts features from message sequence"""
        features = []

        for message_data in message_sequence:
            message = message_data['message']
            metadata = message_data['metadata']

            # Get appropriate feature extractor
            extractor = self.feature_extractors.get(
                metadata.message_type,
                self._extract_default_features
            )

            # Extract features
            message_features = extractor(message, metadata)
            features.append(message_features)

        # Pad sequence if necessary
        while len(features) < self.sequence_length:
            features.append(torch.zeros(self.feature_dim))

        return torch.stack(features)

    def _detect_threats(self, features: torch.Tensor) -> float:
        """Performs threat detection using transformer model"""
        # Prepare input
        features = features.unsqueeze(0)  # Add batch dimension

        # Model inference
        with torch.no_grad():
            threat_prob = self.model(features).item()

        return threat_prob

    def _analyze_detection(self,
                          threat_prob: float,
                          message: Dict,
                          metadata: MessageMetadata) -> DetectionResult:
        """Analyzes detection results and generates detailed report"""
        is_threat = threat_prob >= self.detection_threshold

        # Determine threat type if detected
        threat_type = None
        if is_threat:
            threat_type = self._classify_threat_type(
                message,
                metadata,
                threat_prob
            )

        # Generate evidence
        evidence = self._collect_evidence(
            message,
            metadata,
            threat_prob
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            is_threat,
            threat_type,
            evidence
        )

        return DetectionResult(
            timestamp=datetime.datetime.now(),
            threat_detected=is_threat,
            confidence=threat_prob,
            threat_type=threat_type,
            affected_nodes=[metadata.sender_id],
            evidence=evidence,
            recommendation=recommendation
        )

    def _classify_threat_type(self,
                            message: Dict,
                            metadata: MessageMetadata,
                            threat_prob: float) -> str:
        """Classifies the type of detected threat"""
        # Implementation of threat classification logic
        pass

    def _collect_evidence(self,
                         message: Dict,
                         metadata: MessageMetadata,
                         threat_prob: float) -> Dict:
        """Collects evidence supporting the detection result"""
        # Implementation of evidence collection logic
        pass

    def _generate_recommendation(self,
                               is_threat: bool,
                               threat_type: Optional[str],
                               evidence: Dict) -> str:
        """Generates recommendation based on detection results"""
        # Implementation of recommendation generation logic
        pass

    def _extract_position_features(self, message: Dict,
                                metadata: MessageMetadata) -> torch.Tensor:
        """
        Extracts features from position update messages
        Focuses on movement patterns and physical constraints
        """
        features = []

        # Spatial features
        position = message['position']
        features.extend([
            position['latitude'],
            position['longitude'],
            position['altitude'] if 'altitude' in position else 0,
            message['speed'],
            message['direction']
        ])

        # Acceleration and jerk (rate of acceleration change)
        features.extend([
            message.get('acceleration', 0),
            message.get('jerk', 0)
        ])

        # Physical feasibility metrics
        features.extend([
            self._calculate_speed_feasibility(message),
            self._calculate_acceleration_feasibility(message),
            self._calculate_turn_feasibility(message)
        ])

        # Historical consistency
        features.extend([
            self._calculate_position_consistency(message, metadata),
            self._calculate_speed_consistency(message, metadata)
        ])

        return self._normalize_features(torch.tensor(features))

    def _extract_emergency_features(self, message: Dict,
                                  metadata: MessageMetadata) -> torch.Tensor:
        """
        Extracts features from emergency alert messages
        Focuses on alert patterns and contextual consistency
        """
        features = []

        # Alert characteristics
        severity_encoding = {
            'CRITICAL': 1.0,
            'HIGH': 0.75,
            'MEDIUM': 0.5,
            'LOW': 0.25
        }

        features.extend([
            severity_encoding.get(message['severity'], 0),
            self._encode_alert_type(message['alert_type']),
            message['location']['radius'] / 10000  # Normalize radius
        ])

        # Contextual features
        features.extend([
            self._calculate_alert_frequency(metadata.sender_id),
            self._calculate_alert_correlation(message),
            self._calculate_geographical_correlation(message)
        ])

        return self._normalize_features(torch.tensor(features))

    def _extract_traffic_features(self, message: Dict,
                                metadata: MessageMetadata) -> torch.Tensor:
        """
        Extracts features from traffic information messages
        Focuses on traffic patterns and flow consistency
        """
        features = []

        # Traffic metrics
        features.extend([
            message['congestion_level'] / 100,  # Normalize to [0,1]
            message['average_speed'] / 200,     # Normalize speed
            message.get('density', 0) / 100     # Vehicles per km
        ])

        # Flow consistency
        features.extend([
            self._calculate_flow_consistency(message),
            self._calculate_speed_flow_relationship(message),
            self._calculate_temporal_correlation(message)
        ])

        return self._normalize_features(torch.tensor(features))

    def _classify_threat_type(self, message: Dict,
                            metadata: MessageMetadata,
                            threat_prob: float) -> str:
        """
        Classifies the detected threat based on message characteristics
        and detection patterns
        """
        # Get recent messages for context
        recent_messages = self.message_buffers[metadata.sender_id][-10:]

        # Calculate threat characteristics
        characteristics = {
            'position_spoofing': self._check_position_spoofing(recent_messages),
            'message_flooding': self._check_message_flooding(metadata.sender_id),
            'data_injection': self._check_data_injection(message, recent_messages),
            'replay_attack': self._check_replay_attack(message, recent_messages),
            'impersonation': self._check_impersonation(metadata)
        }

        # Find most likely threat type
        threat_type = max(characteristics.items(), key=lambda x: x[1])[0]

        return threat_type

    def _collect_evidence(self, message: Dict,
                        metadata: MessageMetadata,
                        threat_prob: float) -> Dict:
        """
        Collects and organizes evidence supporting the detection result
        """
        evidence = {
            'threat_probability': threat_prob,
            'timestamp': datetime.datetime.now().isoformat(),
            'message_analysis': {
                'content_anomalies': self._analyze_content_anomalies(message),
                'timing_anomalies': self._analyze_timing_anomalies(metadata),
                'behavioral_anomalies': self._analyze_behavioral_anomalies(
                    metadata.sender_id
                )
            },
            'context_analysis': {
                'historical_patterns': self._analyze_historical_patterns(
                    metadata.sender_id
                ),
                'spatial_correlation': self._analyze_spatial_correlation(message),
                'network_impact': self._analyze_network_impact(message, metadata)
            },
            'risk_assessment': {
                'severity': self._assess_severity(message, threat_prob),
                'potential_impact': self._assess_impact(message),
                'confidence_factors': self._assess_confidence(threat_prob)
            }
        }

        return evidence

    def _generate_recommendation(self, is_threat: bool,
                              threat_type: Optional[str],
                              evidence: Dict) -> str:
        """
        Generates detailed recommendations based on detection results
        """
        if not is_threat:
            return "No immediate action required. Continue normal monitoring."

        # Base recommendations on threat type
        recommendations = {
            'position_spoofing': [
                "Initiate position verification protocol",
                "Flag vehicle for enhanced monitoring",
                "Request additional position confirmations"
            ],
            'message_flooding': [
                "Implement rate limiting for affected node",
                "Temporarily increase message filtering threshold",
                "Monitor network bandwidth consumption"
            ],
            'data_injection': [
                "Isolate affected message streams",
                "Increase validation strictness",
                "Deploy additional data sanity checks"
            ],
            'replay_attack': [
                "Refresh session keys",
                "Enhance timestamp validation",
                "Monitor message sequence numbers"
            ],
            'impersonation': [
                "Initiate node re-authentication",
                "Revoke suspected compromised credentials",
                "Deploy additional identity verification measures"
            ]
        }

        # Get base recommendations for the threat type
        base_recs = recommendations.get(threat_type,
                                      ["Initiate general security measures"])

        # Enhance with severity-specific additions
        severity = evidence['risk_assessment']['severity']
        if severity > 0.8:
            base_recs.append("URGENT: Consider immediate node isolation")
        elif severity > 0.6:
            base_recs.append("Increase monitoring frequency")

        return " | ".join(base_recs)

    def _check_position_spoofing(self,
                              recent_messages: List[Dict]) -> float:
        """Calculates likelihood of position spoofing"""
        if len(recent_messages) < 2:
            return 0.0

        anomaly_score = 0.0
        for i in range(1, len(recent_messages)):
            prev_msg = recent_messages[i-1]['message']
            curr_msg = recent_messages[i]['message']

            # Check for physically impossible movements
            time_diff = (curr_msg['timestamp'] - prev_msg['timestamp']).total_seconds()
            distance = self._calculate_distance(
                prev_msg['position'],
                curr_msg['position']
            )

            if time_diff > 0:
                speed = distance / time_diff
                if speed > 100:  # Unrealistic speed threshold
                    anomaly_score += 0.3

        return min(1.0, anomaly_score)

    def _check_message_flooding(self, sender_id: str) -> float:
        """Calculates likelihood of message flooding attack"""
        recent_messages = self.message_buffers[sender_id]
        if len(recent_messages) < 10:
            return 0.0

        # Calculate message frequency
        time_window = (recent_messages[-1]['timestamp'] -
                      recent_messages[0]['timestamp']).total_seconds()
        msg_frequency = len(recent_messages) / time_window if time_window > 0 else 0

        # Score based on frequency threshold
        if msg_frequency > 100:  # Messages per second
            return 0.9
        elif msg_frequency > 50:
            return 0.6
        elif msg_frequency > 20:
            return 0.3

        return 0.0