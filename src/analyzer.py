import numpy as np
import torch
import torch.nn as nn
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
import datetime

@dataclass
class AnalysisResult:
    """Represents the result of deep analysis"""
    timestamp: datetime.datetime
    anomaly_score: float
    anomaly_type: Optional[str]
    confidence: float
    feature_importance: Dict[str, float]
    temporal_pattern: Dict[str, List[float]]
    spatial_correlation: Dict[str, float]
    context_analysis: Dict[str, any]

class TimeSeriesEncoder(nn.Module):
    """Encodes temporal patterns in network behavior"""
    def __init__(self, input_dim: int, hidden_dim: int = 128):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            bidirectional=True
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim * 2,
            num_heads=4,
            batch_first=True
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # LSTM encoding
        lstm_out, _ = self.lstm(x)

        # Self-attention mechanism
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)

        return attn_out

class DataAnalyzer:
    """Main class for deep analysis of network behavior"""

    def _calculate_feature_based_score(self, features: np.ndarray) -> float:
        """
        Calculates anomaly score based on feature analysis
        using Isolation Forest algorithm
        """
        from sklearn.ensemble import IsolationForest

        # Initialize and fit Isolation Forest
        iso_forest = IsolationForest(
            contamination=0.1,
            random_state=42
        )

        # Get anomaly scores
        scores = iso_forest.fit_predict(features.reshape(1, -1))

        # Convert to probability-like score
        score = 1 - (scores[0] + 1) / 2
        return float(score)

    def _analyze_periodicity(self, time_series: np.ndarray) -> List[float]:
        """
        Analyzes periodic patterns in time series using FFT
        """
        from scipy.fft import fft

        # Apply FFT
        fft_result = fft(time_series)
        frequencies = np.abs(fft_result)

        # Find dominant frequencies
        peaks = self._find_peaks(frequencies)

        return peaks.tolist()

    def _analyze_trend(self, time_series: np.ndarray) -> List[float]:
        """
        Analyzes trends using moving averages and regression
        """
        from scipy import stats

        # Calculate moving averages
        window_sizes = [5, 10, 20]
        trends = []

        for window in window_sizes:
            ma = np.convolve(time_series, np.ones(window)/window, mode='valid')
            slope, _, _, _, _ = stats.linregress(
                np.arange(len(ma)),
                ma
            )
            trends.append(float(slope))

        return trends

    def _analyze_seasonality(self, time_series: np.ndarray) -> Dict[str, float]:
        """
        Analyzes seasonal patterns using decomposition
        """
        from statsmodels.tsa.seasonal import seasonal_decompose
        import pandas as pd

        # Convert to pandas series
        ts = pd.Series(time_series)

        # Perform decomposition
        decomposition = seasonal_decompose(
            ts,
            period=min(len(ts), 24),
            extrapolate_trend='freq'
        )

        return {
            'seasonal_strength': float(np.std(decomposition.seasonal)),
            'trend_strength': float(np.std(decomposition.trend)),
            'residual_strength': float(np.std(decomposition.resid))
        }

    def _calculate_temporal_anomalies(self,
                                    encoded_sequence: torch.Tensor) -> List[float]:
        """
        Calculates temporal anomalies using attention weights
        """
        # Convert to numpy for calculations
        encoded = encoded_sequence.detach().numpy()

        # Calculate reconstruction error
        reconstructed = self._reconstruct_sequence(encoded)
        error = np.mean((encoded - reconstructed) ** 2, axis=2)

        # Normalize errors
        normalized_error = (error - np.min(error)) / (np.max(error) - np.min(error))

        return normalized_error.tolist()

    def _find_nearby_nodes(self, node_id: str, raw_data: Dict) -> List[str]:
        """
        Finds nodes within communication range
        """
        nearby_nodes = []
        node_position = raw_data.get('position', {})

        for other_id, other_data in self.historical_data.items():
            if other_id == node_id:
                continue

            if not other_data:
                continue

            other_position = other_data[-1]['data'].get('position', {})

            # Calculate distance
            distance = self._calculate_distance(node_position, other_position)

            # Check if within range (e.g., 1000 meters)
            if distance <= 1000:
                nearby_nodes.append(other_id)

        return nearby_nodes

    def _calculate_node_correlation(self,
                                  node_id: str,
                                  other_node: str) -> float:
        """
        Calculates correlation between two nodes' behavior
        """
        node_data = self.historical_data[node_id]
        other_data = self.historical_data[other_node]

        if not node_data or not other_data:
            return 0.0

        # Extract comparable features
        node_features = self._extract_correlation_features(node_data)
        other_features = self._extract_correlation_features(other_data)

        # Calculate correlation coefficient
        correlation = np.corrcoef(node_features, other_features)[0, 1]

        return float(correlation)

    def _analyze_environment(self, raw_data: Dict) -> Dict[str, float]:
        """
        Analyzes environmental factors affecting node behavior
        """
        return {
            'time_of_day': self._encode_time_of_day(),
            'traffic_density': self._estimate_traffic_density(raw_data),
            'weather_impact': self._assess_weather_impact(raw_data),
            'road_conditions': self._assess_road_conditions(raw_data)
        }

    def _analyze_network_state(self, raw_data: Dict) -> Dict[str, float]:
        """
        Analyzes current network state and conditions
        """
        return {
            'congestion_level': self._calculate_congestion_level(raw_data),
            'communication_quality': self._assess_communication_quality(raw_data),
            'network_load': self._calculate_network_load(raw_data),
            'connectivity_status': self._assess_connectivity(raw_data)
        }

    def _analyze_threat_context(self,
                              detection_result: DetectionResult) -> Dict[str, any]:
        """
        Analyzes threat-related contextual information
        """
        return {
            'historical_threats': self._get_historical_threats(),
            'threat_probability': self._calculate_threat_probability(
                detection_result
            ),
            'impact_severity': self._assess_impact_severity(detection_result),
            'vulnerability_status': self._assess_vulnerabilities()
        }

    def _analyze_historical_context(self, node_id: str) -> Dict[str, any]:
        """
        Analyzes historical behavior patterns
        """
        return {
            'behavior_baseline': self._calculate_behavior_baseline(node_id),
            'deviation_patterns': self._analyze_deviation_patterns(node_id),
            'trust_history': self._analyze_trust_history(node_id),
            'interaction_patterns': self._analyze_interaction_patterns(node_id)
        }

    def _calculate_temporal_factor(self,
                                 temporal_patterns: Dict) -> float:
        """
        Calculates temporal anomaly factor
        """
        scores = []

        # Analyze periodicity
        if 'periodicity' in temporal_patterns:
            period_score = self._evaluate_periodicity(
                temporal_patterns['periodicity']
            )
            scores.append(period_score)

        # Analyze trend
        if 'trend' in temporal_patterns:
            trend_score = self._evaluate_trend(
                temporal_patterns['trend']
            )
            scores.append(trend_score)

        # Analyze seasonality
        if 'seasonality' in temporal_patterns:
            season_score = self._evaluate_seasonality(
                temporal_patterns['seasonality']
            )
            scores.append(season_score)

        # Combine scores
        if scores:
            return float(np.mean(scores))
        return 0.0

    def _calculate_spatial_factor(self,
                                spatial_correlations: Dict[str, float]) -> float:
        """
        Calculates spatial anomaly factor
        """
        if not spatial_correlations:
            return 0.0

        # Calculate average correlation
        avg_correlation = np.mean(list(spatial_correlations.values()))

        # Calculate correlation variance
        correlation_var = np.var(list(spatial_correlations.values()))

        # Combine metrics
        spatial_factor = (1 - avg_correlation) * (1 + correlation_var)

        return float(np.clip(spatial_factor, 0, 1))

    def _calculate_context_factor(self, context: Dict) -> float:
        """
        Calculates contextual anomaly factor
        """
        factors = []

        # Environmental factor
        if 'environmental_factors' in context:
            env_factor = self._evaluate_environmental_impact(
                context['environmental_factors']
            )
            factors.append(env_factor)

        # Network state factor
        if 'network_state' in context:
            net_factor = self._evaluate_network_impact(
                context['network_state']
            )
            factors.append(net_factor)

        # Threat context factor
        if 'threat_context' in context:
            threat_factor = self._evaluate_threat_impact(
                context['threat_context']
            )
            factors.append(threat_factor)

        # Historical context factor
        if 'historical_context' in context:
            hist_factor = self._evaluate_historical_impact(
                context['historical_context']
            )
            factors.append(hist_factor)

        # Combine factors
        if factors:
            # Weight factors based on reliability
            weights = [0.3, 0.2, 0.3, 0.2]
            return float(np.average(factors, weights=weights))
        return 0.0

    def __init__(self,
                 time_window: int = 100,
                 feature_dim: int = 64,
                 anomaly_threshold: float = 0.85):

        self.time_window = time_window
        self.feature_dim = feature_dim
        self.anomaly_threshold = anomaly_threshold

        # Initialize components
        self.time_series_encoder = TimeSeriesEncoder(feature_dim)
        self.scaler = StandardScaler()

        # Storage for historical data
        self.historical_data: Dict[str, List[Dict]] = defaultdict(list)
        self.node_profiles: Dict[str, Dict] = {}

    def analyze_detection(self,
                         detection_result: DetectionResult,
                         raw_data: Dict) -> AnalysisResult:
        """
        Performs deep analysis of detection results
        """
        # Extract node ID
        node_id = detection_result.affected_nodes[0]

        # Update historical data
        self._update_historical_data(node_id, raw_data)

        # Feature extraction
        features = self._extract_analysis_features(
            node_id,
            raw_data,
            detection_result
        )

        # Time series analysis
        temporal_patterns = self._analyze_temporal_patterns(node_id)

        # Spatial analysis
        spatial_correlations = self._analyze_spatial_correlations(
            node_id,
            raw_data
        )

        # Context analysis
        context_analysis = self._analyze_context(
            node_id,
            detection_result,
            raw_data
        )

        # Calculate anomaly score
        anomaly_score = self._calculate_anomaly_score(
            features,
            temporal_patterns,
            spatial_correlations,
            context_analysis
        )

        # Determine anomaly type
        anomaly_type = self._classify_anomaly(
            anomaly_score,
            features,
            temporal_patterns
        )

        # Calculate feature importance
        feature_importance = self._calculate_feature_importance(
            features,
            anomaly_score
        )

        return AnalysisResult(
            timestamp=datetime.datetime.now(),
            anomaly_score=anomaly_score,
            anomaly_type=anomaly_type,
            confidence=self._calculate_confidence(anomaly_score, features),
            feature_importance=feature_importance,
            temporal_pattern=temporal_patterns,
            spatial_correlation=spatial_correlations,
            context_analysis=context_analysis
        )

    def _update_historical_data(self, node_id: str, raw_data: Dict) -> None:
        """Updates historical data storage with new observations"""
        self.historical_data[node_id].append({
            'timestamp': datetime.datetime.now(),
            'data': raw_data
        })

        # Maintain window size
        if len(self.historical_data[node_id]) > self.time_window:
            self.historical_data[node_id].pop(0)

        # Update node profile
        self._update_node_profile(node_id)

    def _update_node_profile(self, node_id: str) -> None:
        """Updates behavioral profile for the node"""
        data = self.historical_data[node_id]

        if not data:
            return

        # Calculate statistical profiles
        self.node_profiles[node_id] = {
            'avg_message_rate': self._calculate_message_rate(data),
            'movement_pattern': self._extract_movement_pattern(data),
            'behavior_stats': self._calculate_behavior_statistics(data)
        }

    def _analyze_temporal_patterns(self, node_id: str) -> Dict[str, List[float]]:
        """Analyzes temporal patterns in node behavior"""
        data = self.historical_data[node_id]
        if not data:
            return {}

        # Extract time series features
        time_series = self._extract_time_series_features(data)

        # Encode using LSTM
        encoded = self.time_series_encoder(
            torch.tensor(time_series).unsqueeze(0)
        )

        # Analyze patterns
        patterns = {
            'periodicity': self._analyze_periodicity(time_series),
            'trend': self._analyze_trend(time_series),
            'seasonality': self._analyze_seasonality(time_series),
            'anomaly_scores': self._calculate_temporal_anomalies(encoded)
        }

        return patterns

    def _analyze_spatial_correlations(self,
                                    node_id: str,
                                    raw_data: Dict) -> Dict[str, float]:
        """Analyzes spatial relationships between nodes"""
        correlations = {}

        # Get nearby nodes
        nearby_nodes = self._find_nearby_nodes(node_id, raw_data)

        for other_node in nearby_nodes:
            # Calculate correlation score
            correlation = self._calculate_node_correlation(
                node_id,
                other_node
            )
            correlations[other_node] = correlation

        return correlations

    def _analyze_context(self,
                        node_id: str,
                        detection_result: DetectionResult,
                        raw_data: Dict) -> Dict:
        """Analyzes contextual factors"""
        context = {
            'environmental_factors': self._analyze_environment(raw_data),
            'network_state': self._analyze_network_state(raw_data),
            'threat_context': self._analyze_threat_context(detection_result),
            'historical_context': self._analyze_historical_context(node_id)
        }

        return context

    def _calculate_anomaly_score(self,
                                features: np.ndarray,
                                temporal_patterns: Dict,
                                spatial_correlations: Dict,
                                context: Dict) -> float:
        """Calculates final anomaly score combining all factors"""
        # Base score from features
        base_score = self._calculate_feature_based_score(features)

        # Temporal factor
        temporal_factor = self._calculate_temporal_factor(temporal_patterns)

        # Spatial factor
        spatial_factor = self._calculate_spatial_factor(spatial_correlations)

        # Context factor
        context_factor = self._calculate_context_factor(context)

        # Combine scores with weights
        final_score = (
            0.4 * base_score +
            0.3 * temporal_factor +
            0.2 * spatial_factor +
            0.1 * context_factor
        )

        return float(np.clip(final_score, 0, 1))