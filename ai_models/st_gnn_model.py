"""
MakFleet Spatio-Temporal Graph Neural Network (ST-GNN)
Implements ST-GNN for anomaly detection and behavior prediction
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, GATConv
from torch_geometric.data import Data, DataLoader
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
import math


@dataclass
class STGNNConfig:
    """Configuration for ST-GNN model"""
    node_features: int = 8  # speed, acceleration, lat, lon, time_features, etc.
    hidden_dim: int = 64
    num_layers: int = 3
    num_heads: int = 8  # For GAT layers
    dropout: float = 0.1
    learning_rate: float = 0.001
    weight_decay: float = 1e-5
    sequence_length: int = 10  # Temporal sequence length
    prediction_horizon: int = 5  # Steps to predict ahead
    anomaly_threshold: float = 0.8


class TemporalEncoder(nn.Module):
    """Encodes temporal features using sinusoidal positional encoding"""
    
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        self.d_model = d_model
        
        # Create positional encoding matrix
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add temporal encoding to input"""
        return x + self.pe[:, :x.size(1)]


class SpatialGCNLayer(nn.Module):
    """Spatial Graph Convolution Layer"""
    
    def __init__(self, in_channels: int, out_channels: int, use_gat: bool = True):
        super().__init__()
        if use_gat:
            self.conv = GATConv(in_channels, out_channels, heads=8, dropout=0.1)
        else:
            self.conv = GCNConv(in_channels, out_channels)
        
        self.norm = nn.LayerNorm(out_channels)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """Forward pass through spatial layer"""
        x = self.conv(x, edge_index)
        x = self.norm(x)
        x = F.relu(x)
        x = self.dropout(x)
        return x


class TemporalConvLayer(nn.Module):
    """Temporal Convolution Layer for capturing temporal dependencies"""
    
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2)
        self.norm = nn.LayerNorm(out_channels)
        self.dropout = nn.Dropout(0.1)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass through temporal layer"""
        # x shape: (batch, seq_len, features)
        x = x.transpose(1, 2)  # (batch, features, seq_len)
        x = self.conv(x)
        x = x.transpose(1, 2)  # (batch, seq_len, features)
        x = self.norm(x)
        x = F.relu(x)
        x = self.dropout(x)
        return x


class STGNNEncoder(nn.Module):
    """Spatio-Temporal Graph Neural Network Encoder"""
    
    def __init__(self, config: STGNNConfig):
        super().__init__()
        self.config = config
        
        # Feature projection
        self.feature_proj = nn.Linear(config.node_features, config.hidden_dim)
        
        # Temporal encoder
        self.temporal_encoder = TemporalEncoder(config.hidden_dim)
        
        # Spatial layers
        self.spatial_layers = nn.ModuleList([
            SpatialGCNLayer(config.hidden_dim, config.hidden_dim)
            for _ in range(config.num_layers)
        ])
        
        # Temporal layers
        self.temporal_layers = nn.ModuleList([
            TemporalConvLayer(config.hidden_dim, config.hidden_dim)
            for _ in range(config.num_layers)
        ])
        
        # Final projection
        self.final_proj = nn.Linear(config.hidden_dim, config.hidden_dim)
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        Args:
            x: Node features (batch_size, num_nodes, seq_len, features)
            edge_index: Graph edges (2, num_edges)
        Returns:
            Encoded representations (batch_size, num_nodes, hidden_dim)
        """
        batch_size, num_nodes, seq_len, features = x.shape
        
        # Flatten batch and nodes for processing
        x = x.view(batch_size * num_nodes, seq_len, features)
        
        # Feature projection
        x = self.feature_proj(x)  # (batch*num_nodes, seq_len, hidden_dim)
        
        # Temporal encoding
        x = self.temporal_encoder(x)
        
        # Apply spatio-temporal layers
        for spatial_layer, temporal_layer in zip(self.spatial_layers, self.temporal_layers):
            # Spatial aggregation (reshape to handle batching)
            x_temp = x.view(batch_size, num_nodes, seq_len, -1)
            x_spatial = []
            
            for b in range(batch_size):
                for t in range(seq_len):
                    node_features = x_temp[b, :, t, :]  # (num_nodes, hidden_dim)
                    spatial_out = spatial_layer(node_features, edge_index)
                    x_spatial.append(spatial_out)
            
            x = torch.stack(x_spatial).view(batch_size * num_nodes, seq_len, -1)
            
            # Temporal convolution
            x = temporal_layer(x)
        
        # Take last timestep and reshape
        x = x[:, -1, :]  # (batch*num_nodes, hidden_dim)
        x = self.final_proj(x)
        x = x.view(batch_size, num_nodes, -1)
        
        return x


class STGNNDecoder(nn.Module):
    """Decoder for prediction and anomaly detection"""
    
    def __init__(self, config: STGNNConfig):
        super().__init__()
        self.config = config
        
        # Prediction head
        self.predictor = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(config.hidden_dim // 2, config.prediction_horizon * config.node_features)
        )
        
        # Anomaly detection head
        self.anomaly_detector = nn.Sequential(
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(config.hidden_dim // 2, 1),
            nn.Sigmoid()
        )
    
    def forward(self, encoded: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        Args:
            encoded: Encoded representations (batch_size, num_nodes, hidden_dim)
        Returns:
            predictions: (batch_size, num_nodes, prediction_horizon, features)
            anomaly_scores: (batch_size, num_nodes, 1)
        """
        batch_size, num_nodes, hidden_dim = encoded.shape
        
        # Flatten for prediction
        encoded_flat = encoded.view(batch_size * num_nodes, hidden_dim)
        
        # Predictions
        pred_flat = self.predictor(encoded_flat)
        predictions = pred_flat.view(batch_size, num_nodes, self.config.prediction_horizon, self.config.node_features)
        
        # Anomaly scores
        anomaly_scores = self.anomaly_detector(encoded_flat)
        anomaly_scores = anomaly_scores.view(batch_size, num_nodes, 1)
        
        return predictions, anomaly_scores


class STGNNModel(nn.Module):
    """Complete Spatio-Temporal Graph Neural Network"""
    
    def __init__(self, config: STGNNConfig):
        super().__init__()
        self.config = config
        self.encoder = STGNNEncoder(config)
        self.decoder = STGNNDecoder(config)
    
    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        Args:
            x: Input features (batch_size, num_nodes, seq_len, features)
            edge_index: Graph structure (2, num_edges)
        Returns:
            predictions, anomaly_scores
        """
        encoded = self.encoder(x, edge_index)
        predictions, anomaly_scores = self.decoder(encoded)
        return predictions, anomaly_scores


class STGNNTrainer:
    """Trainer for ST-GNN model"""
    
    def __init__(self, model: STGNNModel, config: STGNNConfig):
        self.model = model
        self.config = config
        
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=config.learning_rate,
            weight_decay=config.weight_decay
        )
        
        self.prediction_criterion = nn.MSELoss()
        self.anomaly_criterion = nn.BCELoss()
        
        self.best_loss = float('inf')
    
    def train_epoch(self, train_loader: DataLoader) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0
        
        for batch in train_loader:
            self.optimizer.zero_grad()
            
            # Forward pass
            predictions, anomaly_scores = self.model(batch.x, batch.edge_index)
            
            # Compute losses
            pred_loss = self.prediction_criterion(
                predictions[..., :self.config.node_features],  # Only predict current features
                batch.y
            )
            
            # For anomaly detection, use reconstruction error as supervision
            anomaly_target = (batch.anomaly_labels.float()).unsqueeze(-1)
            anomaly_loss = self.anomaly_criterion(anomaly_scores, anomaly_target)
            
            # Combined loss
            loss = pred_loss + 0.1 * anomaly_loss
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(train_loader)
    
    def validate(self, val_loader: DataLoader) -> Dict[str, float]:
        """Validate model"""
        self.model.eval()
        total_pred_loss = 0
        total_anomaly_loss = 0
        
        with torch.no_grad():
            for batch in val_loader:
                predictions, anomaly_scores = self.model(batch.x, batch.edge_index)
                
                pred_loss = self.prediction_criterion(
                    predictions[..., :self.config.node_features],
                    batch.y
                )
                
                anomaly_target = (batch.anomaly_labels.float()).unsqueeze(-1)
                anomaly_loss = self.anomaly_criterion(anomaly_scores, anomaly_target)
                
                total_pred_loss += pred_loss.item()
                total_anomaly_loss += anomaly_loss.item()
        
        return {
            'prediction_loss': total_pred_loss / len(val_loader),
            'anomaly_loss': total_anomaly_loss / len(val_loader),
            'total_loss': (total_pred_loss + 0.1 * total_anomaly_loss) / len(val_loader)
        }


class CampusGraphBuilder:
    """Builds graph representation of campus for ST-GNN"""
    
    def __init__(self):
        self.node_mapping = {}  # location_id -> node_id
        self.node_features = {}  # node_id -> features
    
    def build_graph(self, telemetry_data: List[Dict[str, Any]],
                   campus_locations: List[Dict[str, Any]]) -> Data:
        """
        Build PyTorch Geometric Data object from telemetry and campus data
        """
        # Create node mapping
        for i, location in enumerate(campus_locations):
            self.node_mapping[location['location_id']] = i
        
        num_nodes = len(campus_locations)
        
        # Build edge index (connect nearby locations)
        edge_index = []
        for i, loc1 in enumerate(campus_locations):
            for j, loc2 in enumerate(campus_locations):
                if i != j:
                    dist = self._calculate_distance(loc1, loc2)
                    if dist < 500:  # Connect locations within 500m
                        edge_index.extend([[i, j], [j, i]])  # Bidirectional
        
        edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
        
        # Process telemetry data into temporal sequences
        sequences = self._create_temporal_sequences(telemetry_data)
        
        # Convert to PyTorch tensors
        if sequences:
            x = torch.tensor(sequences, dtype=torch.float)
        else:
            # Dummy data if no sequences
            x = torch.randn(1, num_nodes, self.config.sequence_length, self.config.node_features)
        
        return Data(x=x, edge_index=edge_index)
    
    def _calculate_distance(self, loc1: Dict[str, Any], loc2: Dict[str, Any]) -> float:
        """Calculate distance between two locations"""
        R = 6371000
        lat1, lon1 = math.radians(loc1['latitude']), math.radians(loc1['longitude'])
        lat2, lon2 = math.radians(loc2['latitude']), math.radians(loc2['longitude'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _create_temporal_sequences(self, telemetry_data: List[Dict[str, Any]]) -> np.ndarray:
        """Create temporal sequences from telemetry data"""
        # Group by vehicle and time
        vehicle_sequences = {}
        
        for point in telemetry_data:
            vehicle_id = point['vehicle_id']
            if vehicle_id not in vehicle_sequences:
                vehicle_sequences[vehicle_id] = []
            vehicle_sequences[vehicle_id].append(point)
        
        # Create sequences for each vehicle
        sequences = []
        for vehicle_points in vehicle_sequences.values():
            # Sort by timestamp
            vehicle_points.sort(key=lambda x: x['timestamp'])
            
            # Create sliding windows
            for i in range(len(vehicle_points) - self.config.sequence_length):
                window = vehicle_points[i:i+self.config.sequence_length]
                seq_features = []
                
                for point in window:
                    features = [
                        point.get('speed', 0),
                        point.get('acceleration', 0),
                        point.get('latitude', 0),
                        point.get('longitude', 0),
                        point.get('hour_of_day', 12) / 24,  # Normalize
                        point.get('is_peak_hour', 0),
                        point.get('data_quality_score', 0.5),
                        point.get('safety_score', 0.5)
                    ]
                    seq_features.append(features)
                
                sequences.append(seq_features)
        
        return np.array(sequences) if sequences else np.array([])


class STGNNPredictor:
    """High-level interface for ST-GNN predictions and anomaly detection"""
    
    def __init__(self, model_path: str, config: STGNNConfig):
        self.config = config
        self.model = STGNNModel(config)
        self.model.load_state_dict(torch.load(model_path))
        self.model.eval()
        
        self.graph_builder = CampusGraphBuilder()
    
    def detect_anomalies(self, telemetry_batch: List[Dict[str, Any]],
                        campus_locations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in telemetry batch"""
        anomalies = []
        
        # Build graph data
        graph_data = self.graph_builder.build_graph(telemetry_batch, campus_locations)
        
        if graph_data.x.size(0) == 0:
            return anomalies
        
        with torch.no_grad():
            predictions, anomaly_scores = self.model(graph_data.x, graph_data.edge_index)
            
            # Process anomaly scores
            scores = anomaly_scores.squeeze().numpy()
            
            for i, score in enumerate(scores):
                if score > self.config.anomaly_threshold:
                    # Get corresponding telemetry point
                    if i < len(telemetry_batch):
                        point = telemetry_batch[i]
                        
                        anomaly = {
                            'anomaly_id': f"anomaly_{datetime.utcnow().timestamp()}",
                            'timestamp': point['timestamp'],
                            'anomaly_type': 'ST_GNN_DETECTED',
                            'severity_score': float(score),
                            'detection_model': 'ST-GNN',
                            'confidence': float(score),
                            'explanation': f"ST-GNN detected anomaly with score {score:.3f}",
                            'causal_factors': ['spatial_temporal_pattern_anomaly'],
                            'affected_entities': [point['vehicle_id']],
                            'recommended_action': 'Investigate vehicle behavior and environmental factors'
                        }
                        
                        anomalies.append(anomaly)
        
        return anomalies
    
    def predict_behavior(self, current_state: Dict[str, Any],
                        campus_locations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict future behavior"""
        # Build graph with current state
        graph_data = self.graph_builder.build_graph([current_state], campus_locations)
        
        with torch.no_grad():
            predictions, _ = self.model(graph_data.x, graph_data.edge_index)
            
            # Extract prediction
            pred = predictions[0, 0, :, :].numpy()  # First node, first batch
            
            return {
                'predicted_speed': pred[:, 0].tolist(),
                'predicted_acceleration': pred[:, 1].tolist(),
                'predicted_location_lat': pred[:, 2].tolist(),
                'predicted_location_lon': pred[:, 3].tolist(),
                'confidence': 0.85  # Placeholder
            }
    
    def explain_anomaly(self, anomaly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide explainable AI explanation for anomaly"""
        # This would use techniques like SHAP or LIME for model interpretability
        # For now, return basic explanation
        return {
            'explanation': "ST-GNN detected unusual spatio-temporal patterns",
            'contributing_factors': [
                'Unusual speed changes',
                'Deviation from typical routes',
                'Temporal pattern anomalies'
            ],
            'spatial_context': anomaly_data.get('location_context', {}),
            'temporal_context': anomaly_data.get('time_context', {}),
            'confidence_factors': [
                'Graph structure consistency: High',
                'Temporal sequence likelihood: Low',
                'Spatial distribution: Anomalous'
            ]
        }
