import torch
import torch.nn as nn
import numpy as np
from typing import Dict, List, Optional, Tuple
import math
from dataclasses import dataclass

@dataclass
class TransformerConfig:
    """Configuration for V2I Transformer model"""
    d_model: int = 256          # Model dimension
    n_heads: int = 8           # Number of attention heads
    n_layers: int = 6          # Number of transformer layers
    d_ff: int = 1024          # Feed-forward dimension
    dropout: float = 0.1       # Dropout rate
    max_seq_length: int = 200  # Maximum sequence length
    n_message_types: int = 6   # Number of different message types

class PositionalEncoding(nn.Module):
    """Positional encoding for temporal information"""
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor, shape [batch_size, seq_len, embedding_dim]
        """
        return x + self.pe[:x.size(1)]

class V2ITransformerEncoderLayer(nn.Module):
    """Custom transformer encoder layer for V2I network analysis"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True
        )

        self.feed_forward = nn.Sequential(
            nn.Linear(config.d_model, config.d_ff),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_ff, config.d_model)
        )

        self.norm1 = nn.LayerNorm(config.d_model)
        self.norm2 = nn.LayerNorm(config.d_model)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self,
                x: torch.Tensor,
                mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        # Self-attention block
        attn_output, _ = self.self_attn(x, x, x, attn_mask=mask)
        x = self.norm1(x + self.dropout(attn_output))

        # Feed-forward block
        ff_output = self.feed_forward(x)
        x = self.norm2(x + self.dropout(ff_output))

        return x

class V2IMessageEmbedding(nn.Module):
    """Embeds V2I messages into continuous space"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config

        # Message type embedding
        self.type_embedding = nn.Embedding(
            config.n_message_types,
            config.d_model
        )

        # Linear projections for different features
        self.position_proj = nn.Linear(3, config.d_model)  # lat, lon, alt
        self.velocity_proj = nn.Linear(3, config.d_model)  # speed, direction, acceleration
        self.metadata_proj = nn.Linear(5, config.d_model)  # timestamp, priority, etc

        # Final projection
        self.output_proj = nn.Linear(4 * config.d_model, config.d_model)

    def forward(self, message_batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        # Embed different components
        type_emb = self.type_embedding(message_batch['message_type'])
        pos_emb = self.position_proj(message_batch['position'])
        vel_emb = self.velocity_proj(message_batch['velocity'])
        meta_emb = self.metadata_proj(message_batch['metadata'])

        # Concatenate and project
        combined = torch.cat([type_emb, pos_emb, vel_emb, meta_emb], dim=-1)

        return self.output_proj(combined)

class V2ITransformer(nn.Module):
    """Main transformer model for V2I network analysis"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config

        # Message embedding
        self.message_embedding = V2IMessageEmbedding(config)

        # Positional encoding
        self.pos_encoding = PositionalEncoding(config.d_model)

        # Transformer layers
        self.layers = nn.ModuleList([
            V2ITransformerEncoderLayer(config)
            for _ in range(config.n_layers)
        ])

        # Output heads
        self.anomaly_head = nn.Linear(config.d_model, 1)
        self.pattern_head = nn.Linear(config.d_model, config.d_model)
        self.classification_head = nn.Linear(config.d_model, config.n_message_types)

    def forward(self,
                messages: Dict[str, torch.Tensor],
                mask: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        # Embed messages
        x = self.message_embedding(messages)

        # Add positional encoding
        x = self.pos_encoding(x)

        # Pass through transformer layers
        for layer in self.layers:
            x = layer(x, mask)

        # Global sequence representation
        sequence_repr = x.mean(dim=1)

        # Generate outputs
        return {
            'anomaly_scores': torch.sigmoid(self.anomaly_head(sequence_repr)),
            'pattern_embeddings': self.pattern_head(sequence_repr),
            'message_classifications': self.classification_head(x)
        }

class V2ITransformerTrainer:
    """Handles training and evaluation of the V2I Transformer"""
    def __init__(self,
                 model: V2ITransformer,
                 learning_rate: float = 1e-4,
                 device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.model = model.to(device)
        self.device = device
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        # Loss functions
        self.anomaly_criterion = nn.BCELoss()
        self.pattern_criterion = nn.MSELoss()
        self.classification_criterion = nn.CrossEntropyLoss()

    def train_step(self,
                   batch: Dict[str, torch.Tensor],
                   labels: Dict[str, torch.Tensor]) -> Dict[str, float]:
        self.model.train()
        self.optimizer.zero_grad()

        # Forward pass
        outputs = self.model(batch)

        # Calculate losses
        anomaly_loss = self.anomaly_criterion(
            outputs['anomaly_scores'],
            labels['anomaly_labels']
        )

        pattern_loss = self.pattern_criterion(
            outputs['pattern_embeddings'],
            labels['pattern_labels']
        )

        classification_loss = self.classification_criterion(
            outputs['message_classifications'].view(-1, self.model.config.n_message_types),
            labels['message_types'].view(-1)
        )

        # Combine losses
        total_loss = anomaly_loss + pattern_loss + classification_loss

        # Backward pass
        total_loss.backward()
        self.optimizer.step()

        return {
            'total_loss': total_loss.item(),
            'anomaly_loss': anomaly_loss.item(),
            'pattern_loss': pattern_loss.item(),
            'classification_loss': classification_loss.item()
        }

    @torch.no_grad()
    def evaluate(self,
                 val_loader: torch.utils.data.DataLoader) -> Dict[str, float]:
        self.model.eval()
        total_metrics = defaultdict(float)

        for batch, labels in val_loader:
            outputs = self.model(batch)

            # Calculate metrics
            metrics = self._calculate_metrics(outputs, labels)

            # Accumulate metrics
            for k, v in metrics.items():
                total_metrics[k] += v

        # Average metrics
        return {k: v / len(val_loader) for k, v in total_metrics.items()}

    def _calculate_metrics(self,
                         outputs: Dict[str, torch.Tensor],
                         labels: Dict[str, torch.Tensor]) -> Dict[str, float]:
        """Calculates evaluation metrics"""
        metrics = {}

        # Anomaly detection metrics
        anomaly_preds = (outputs['anomaly_scores'] > 0.5).float()
        metrics['anomaly_accuracy'] = (
            anomaly_preds == labels['anomaly_labels']
        ).float().mean()

        # Classification metrics
        pred_classes = outputs['message_classifications'].argmax(dim=-1)
        metrics['classification_accuracy'] = (
            pred_classes == labels['message_types']
        ).float().mean()

        # Pattern recognition metrics
        pattern_similarity = F.cosine_similarity(
            outputs['pattern_embeddings'],
            labels['pattern_labels']
        ).mean()
        metrics['pattern_similarity'] = pattern_similarity

        return metrics


class TemporalAttention(nn.Module):
    """Temporal attention mechanism for analyzing time-dependent patterns"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.time_embedding = nn.Linear(1, config.d_model)
        self.attention = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True
        )
        self.time_scale = nn.Parameter(torch.ones(1))

    def forward(self, x: torch.Tensor, timestamps: torch.Tensor) -> torch.Tensor:
        # Embed timestamps
        time_emb = self.time_embedding(timestamps.unsqueeze(-1))

        # Scale time embeddings
        time_emb = time_emb * self.time_scale

        # Apply attention
        attn_output, _ = self.attention(
            query=x + time_emb,
            key=x + time_emb,
            value=x
        )

        return attn_output

class SpatialCorrelationLayer(nn.Module):
    """Analyzes spatial correlations between V2I nodes"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.distance_embedding = nn.Linear(1, config.d_model)
        self.spatial_attention = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True
        )
        self.distance_scale = nn.Parameter(torch.ones(1))

    def forward(self, x: torch.Tensor,
                positions: torch.Tensor) -> torch.Tensor:
        # Calculate pairwise distances
        distances = self._calculate_pairwise_distances(positions)

        # Embed distances
        dist_emb = self.distance_embedding(distances.unsqueeze(-1))

        # Scale distance embeddings
        dist_emb = dist_emb * self.distance_scale

        # Apply spatial attention
        spatial_output, _ = self.spatial_attention(
            query=x + dist_emb,
            key=x + dist_emb,
            value=x
        )

        return spatial_output

    def _calculate_pairwise_distances(self,
                                    positions: torch.Tensor) -> torch.Tensor:
        """Calculates pairwise distances between all positions"""
        diffs = positions.unsqueeze(1) - positions.unsqueeze(2)
        return torch.norm(diffs, dim=-1)

class BehavioralPatternLayer(nn.Module):
    """Analyzes behavioral patterns in message sequences"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.pattern_embedding = nn.Linear(config.d_model, config.d_model)
        self.pattern_memory = nn.Parameter(
            torch.randn(config.n_message_types, config.d_model)
        )
        self.pattern_attention = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True
        )

    def forward(self, x: torch.Tensor,
                message_types: torch.Tensor) -> torch.Tensor:
        # Embed current patterns
        pattern_emb = self.pattern_embedding(x)

        # Get relevant pattern memories
        memories = self.pattern_memory[message_types]

        # Apply pattern attention
        pattern_output, _ = self.pattern_attention(
            query=pattern_emb,
            key=memories,
            value=memories
        )

        return pattern_output


class EnhancedV2ITransformer(nn.Module):
    """Enhanced transformer with additional analysis capabilities"""
    def __init__(self, config: TransformerConfig):
        super().__init__()
        self.config = config

        # Base components
        self.message_embedding = V2IMessageEmbedding(config)
        self.pos_encoding = PositionalEncoding(config.d_model)

        # Enhanced analysis layers
        self.temporal_attention = TemporalAttention(config)
        self.spatial_correlation = SpatialCorrelationLayer(config)
        self.behavioral_pattern = BehavioralPatternLayer(config)

        # Transformer layers
        self.layers = nn.ModuleList([
            V2ITransformerEncoderLayer(config)
            for _ in range(config.n_layers)
        ])

        # Enhanced output heads
        self.anomaly_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model // 2, 1),
            nn.Sigmoid()
        )

        self.pattern_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model, config.d_model)
        )

        self.classification_head = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model // 2, config.n_message_types)
        )

        # Additional analysis heads
        self.behavior_head = nn.Linear(config.d_model, config.d_model)
        self.risk_assessment_head = nn.Linear(config.d_model, 3)  # Low/Medium/High
        self.forecast_head = nn.Linear(config.d_model, config.d_model)

    def forward(self,
                messages: Dict[str, torch.Tensor],
                mask: Optional[torch.Tensor] = None) -> Dict[str, torch.Tensor]:
        # Embed messages
        x = self.message_embedding(messages)
        x = self.pos_encoding(x)

        # Apply enhanced analysis
        temporal_features = self.temporal_attention(
            x,
            messages['timestamps']
        )

        spatial_features = self.spatial_correlation(
            x,
            messages['positions']
        )

        behavioral_features = self.behavioral_pattern(
            x,
            messages['message_type']
        )

        # Combine features
        x = x + temporal_features + spatial_features + behavioral_features

        # Pass through transformer layers
        for layer in self.layers:
            x = layer(x, mask)

        # Global sequence representation
        sequence_repr = x.mean(dim=1)

        # Generate enhanced outputs
        return {
            'anomaly_scores': self.anomaly_head(sequence_repr),
            'pattern_embeddings': self.pattern_head(sequence_repr),
            'message_classifications': self.classification_head(x),
            'behavioral_patterns': self.behavior_head(sequence_repr),
            'risk_assessment': self.risk_assessment_head(sequence_repr),
            'future_forecast': self.forecast_head(sequence_repr)
        }


class EnhancedV2ITransformerTrainer:
    """Enhanced trainer with additional training capabilities"""
    def __init__(self,
                 model: EnhancedV2ITransformer,
                 config: Dict[str, any]):
        self.model = model
        self.config = config

        # Optimizers
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=config['learning_rate'],
            weight_decay=config['weight_decay']
        )

        # Learning rate scheduler
        self.scheduler = torch.optim.lr_scheduler.OneCycleLR(
            self.optimizer,
            max_lr=config['learning_rate'],
            epochs=config['epochs'],
            steps_per_epoch=config['steps_per_epoch']
        )

        # Loss functions
        self.losses = {
            'anomaly': nn.BCELoss(),
            'pattern': nn.MSELoss(),
            'classification': nn.CrossEntropyLoss(),
            'behavioral': nn.CosineEmbeddingLoss(),
            'risk': nn.CrossEntropyLoss(),
            'forecast': nn.MSELoss()
        }

        # Metrics tracking
        self.metrics = defaultdict(list)

    def train_epoch(self,
                    train_loader: torch.utils.data.DataLoader) -> Dict[str, float]:
        self.model.train()
        epoch_losses = defaultdict(float)

        for batch_idx, (batch, labels) in enumerate(train_loader):
            self.optimizer.zero_grad()

            # Forward pass
            outputs = self.model(batch)

            # Calculate losses
            losses = self._calculate_losses(outputs, labels)
            total_loss = sum(losses.values())

            # Backward pass
            total_loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.config['max_grad_norm']
            )

            self.optimizer.step()
            self.scheduler.step()

            # Update metrics
            for k, v in losses.items():
                epoch_losses[k] += v.item()

        # Average losses
        return {k: v / len(train_loader) for k, v in epoch_losses.items()}

    def _calculate_losses(self,
                         outputs: Dict[str, torch.Tensor],
                         labels: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """Calculates all component losses"""
        losses = {}

        # Anomaly detection loss
        losses['anomaly'] = self.losses['anomaly'](
            outputs['anomaly_scores'],
            labels['anomaly_labels']
        )

        # Pattern recognition loss
        losses['pattern'] = self.losses['pattern'](
            outputs['pattern_embeddings'],
            labels['pattern_labels']
        )

        # Classification loss
        losses['classification'] = self.losses['classification'](
            outputs['message_classifications'].view(-1, self.model.config.n_message_types),
            labels['message_types'].view(-1)
        )

        # Behavioral pattern loss
        losses['behavioral'] = self.losses['behavioral'](
            outputs['behavioral_patterns'],
            labels['behavioral_patterns'],
            torch.ones(outputs['behavioral_patterns'].size(0))
        )

        # Risk assessment loss
        losses['risk'] = self.losses['risk'](
            outputs['risk_assessment'],
            labels['risk_levels']
        )

        # Forecast loss
        losses['forecast'] = self.losses['forecast'](
            outputs['future_forecast'],
            labels['future_states']
        )

        return losses