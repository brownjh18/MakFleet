"""
MakFleet ST-GNN Training Script for NGSIM Data

Comprehensive training script that integrates NGSIM data with the ST-GNN model.
Supports trajectory prediction, speed forecasting, and event detection.
"""

import os
import sys
import argparse
import json
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, random_split
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrajectoryDataset(Dataset):
    """PyTorch Dataset for vehicle trajectory prediction"""
    
    def __init__(self, data: np.ndarray, 
                 sequence_length: int = 50,
                 prediction_horizon: int = 10,
                 feature_names: List[str] = None):
        """
        Initialize dataset
        
        Args:
            data: numpy array of shape (n_samples, n_features)
            sequence_length: Length of input sequence
            prediction_horizon: Number of steps to predict ahead
            feature_names: Names of features in data
        """
        self.data = data
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        
        if feature_names is None:
            feature_names = ['speed', 'acceleration', 'latitude', 'longitude']
        self.feature_names = feature_names
        self.n_features = len(feature_names)
        
        # Create sequences
        self.sequences, self.targets = self._create_sequences()
        
        logger.info(f"Created {len(self.sequences)} sequences")
    
    def _create_sequences(self):
        """Create input-output sequence pairs"""
        sequences = []
        targets = []
        
        # Split data by vehicle ID (assuming first column after features is vehicle_id)
        # For simplicity, create sequences from continuous data
        max_seq_len = self.sequence_length + self.prediction_horizon
        
        for i in range(len(self.data) - max_seq_len + 1):
            # Input sequence
            seq = self.data[i:i + self.sequence_length]
            # Target: next prediction_horizon steps
            target = self.data[i + self.sequence_length:i + self.sequence_length + self.prediction_horizon]
            
            sequences.append(seq)
            targets.append(target)
        
        return np.array(sequences), np.array(targets)
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return {
            'input': torch.FloatTensor(self.sequences[idx]),
            'target': torch.FloatTensor(self.targets[idx])
        }


class STGNNTrajectoryModel(nn.Module):
    """Spatio-Temporal Graph Neural Network for trajectory prediction"""
    
    def __init__(self, 
                 input_dim: int = 4,
                 hidden_dim: int = 64,
                 num_layers: int = 2,
                 output_dim: int = 4,
                 prediction_horizon: int = 10,
                 dropout: float = 0.2):
        """
        Initialize ST-GNN trajectory model
        
        Args:
            input_dim: Number of input features
            hidden_dim: Hidden layer dimension
            num_layers: Number of LSTM layers
            output_dim: Number of output features
            prediction_horizon: Number of steps to predict
            dropout: Dropout rate
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.output_dim = output_dim
        self.prediction_horizon = prediction_horizon
        
        # Spatial encoder (processes each timestep)
        self.spatial_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Temporal encoder (LSTM for sequence modeling)
        self.temporal_encoder = nn.LSTM(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Attention mechanism
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )
        
        # Decoder (predicts future trajectory)
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim * prediction_horizon)
        )
        
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_dim)
            
        Returns:
            Predictions of shape (batch, prediction_horizon, output_dim)
        """
        batch_size = x.shape[0]
        
        # Spatial encoding
        x_spatial = self.spatial_encoder(x)  # (batch, seq_len, hidden_dim)
        
        # Temporal encoding
        _, (h_n, c_n) = self.temporal_encoder(x_spatial)
        # Use last hidden state
        context = h_n[-1]  # (batch, hidden_dim)
        
        # Apply attention over sequence
        query = context.unsqueeze(1)  # (batch, 1, hidden_dim)
        attended, _ = self.attention(query, x_spatial, x_spatial)
        attended = attended.squeeze(1)  # (batch, hidden_dim)
        
        # Decode to predictions
        output = self.decoder(attended)  # (batch, output_dim * prediction_horizon)
        output = output.view(batch_size, self.prediction_horizon, self.output_dim)
        
        return output
    
    def predict_trajectory(self, x):
        """
        Predict trajectory with separate outputs for lat, lon, speed
        
        Args:
            x: Input tensor of shape (batch, seq_len, input_dim)
            
        Returns:
            Tuple of (lat, lon, speed) predictions
        """
        output = self.forward(x)  # (batch, horizon, output_dim)
        
        # Extract lat, lon, speed (assuming order: lat, lon, speed, acceleration)
        pred_lat = output[:, :, 0]  # (batch, horizon)
        pred_lon = output[:, :, 1]
        pred_speed = output[:, :, 2]
        
        return pred_lat, pred_lon, pred_speed


class Trainer:
    """Training manager for ST-GNN model"""
    
    def __init__(self, model: nn.Module, 
                 train_loader: DataLoader,
                 val_loader: DataLoader,
                 learning_rate: float = 0.001,
                 weight_decay: float = 1e-4,
                 device: str = None,
                 output_dir: str = 'outputs'):
        """Initialize trainer"""
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.output_dir = output_dir
        
        # Move model to device
        self.model.to(self.device)
        
        # Loss functions
        self.mse_loss = nn.MSELoss()
        self.huber_loss = nn.HuberLoss(delta=1.0)
        
        # Optimizer with learning rate scheduling
        self.optimizer = torch.optim.AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=5,
            verbose=True
        )
        
        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_position_loss': [],
            'val_position_loss': [],
            'learning_rates': []
        }
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def train_epoch(self) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        total_pos_loss = 0.0
        num_batches = 0
        
        for batch in self.train_loader:
            input_data = batch['input'].to(self.device)
            target = batch['target'].to(self.device)
            
            self.optimizer.zero_grad()
            
            # Forward pass
            predictions = self.model(input_data)
            
            # Calculate loss (weighted combination)
            pos_loss = self.mse_loss(predictions[:, :, 0], target[:, :, 0]) + \
                      self.mse_loss(predictions[:, :, 1], target[:, :, 1])
            speed_loss = self.huber_loss(predictions[:, :, 2], target[:, :, 2])
            
            loss = pos_loss + 0.3 * speed_loss
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            total_pos_loss += pos_loss.item()
            num_batches += 1
        
        return total_loss / num_batches, total_pos_loss / num_batches
    
    def validate(self) -> float:
        """Validate model"""
        self.model.eval()
        total_loss = 0.0
        total_pos_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in self.val_loader:
                input_data = batch['input'].to(self.device)
                target = batch['target'].to(self.device)
                
                predictions = self.model(input_data)
                
                pos_loss = self.mse_loss(predictions[:, :, 0], target[:, :, 0]) + \
                          self.mse_loss(predictions[:, :, 1], target[:, :, 1])
                speed_loss = self.huber_loss(predictions[:, :, 2], target[:, :, 2])
                
                loss = pos_loss + 0.3 * speed_loss
                
                total_loss += loss.item()
                total_pos_loss += pos_loss.item()
                num_batches += 1
        
        return total_loss / num_batches, total_pos_loss / num_batches
    
    def train(self, epochs: int = 100, patience: int = 15) -> Dict:
        """Full training loop with early stopping"""
        logger.info(f"Starting training for {epochs} epochs on {self.device}")
        logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(epochs):
            # Train
            train_loss, train_pos_loss = self.train_epoch()
            
            # Validate
            val_loss, val_pos_loss = self.validate()
            
            # Update learning rate
            self.scheduler.step(val_loss)
            current_lr = self.optimizer.param_groups[0]['lr']
            
            # Update history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_position_loss'].append(train_pos_loss)
            self.history['val_position_loss'].append(val_pos_loss)
            self.history['learning_rates'].append(current_lr)
            
            # Log progress
            logger.info(f"Epoch {epoch+1}/{epochs}: "
                       f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, "
                       f"pos_loss={train_pos_loss:.4f}/{val_pos_loss:.4f}, "
                       f"lr={current_lr:.6f}")
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save_checkpoint(f"best_model.pth")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        return self.history
    
    def evaluate(self, test_loader: DataLoader) -> Dict:
        """Evaluate on test set"""
        logger.info("Evaluating on test set")
        
        self.model.eval()
        total_loss = 0.0
        total_pos_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in test_loader:
                input_data = batch['input'].to(self.device)
                target = batch['target'].to(self.device)
                
                predictions = self.model(input_data)
                
                pos_loss = self.mse_loss(predictions[:, :, 0], target[:, :, 0]) + \
                          self.mse_loss(predictions[:, :, 1], target[:, :, 1])
                speed_loss = self.huber_loss(predictions[:, :, 2], target[:, :, 2])
                
                loss = pos_loss + 0.3 * speed_loss
                
                total_loss += loss.item()
                total_pos_loss += pos_loss.item()
                num_batches += 1
        
        metrics = {
            'test_loss': total_loss / num_batches,
            'test_position_loss': total_pos_loss / num_batches,
            'test_rmse': np.sqrt(total_pos_loss / num_batches)
        }
        
        logger.info(f"Test metrics: {metrics}")
        return metrics
    
    def save_checkpoint(self, path: str):
        """Save model checkpoint"""
        checkpoint_path = os.path.join(self.output_dir, path)
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'history': self.history,
            'model_config': {
                'input_dim': self.model.input_dim,
                'hidden_dim': self.model.hidden_dim,
                'num_layers': self.model.num_layers,
                'output_dim': self.model.output_dim,
                'prediction_horizon': self.model.prediction_horizon
            }
        }, checkpoint_path)
        logger.info(f"Saved checkpoint to {checkpoint_path}")
    
    def load_checkpoint(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        if 'scheduler_state_dict' in checkpoint:
            self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.history = checkpoint.get('history', self.history)
        logger.info(f"Loaded checkpoint from {path}")
    
    def plot_training_history(self, save_path: str = None):
        """Plot training history"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        # Loss curves
        axes[0].plot(self.history['train_loss'], label='Train')
        axes[0].plot(self.history['val_loss'], label='Validation')
        axes[0].set_xlabel('Epoch')
        axes[0].set_ylabel('Loss')
        axes[0].set_title('Training and Validation Loss')
        axes[0].legend()
        axes[0].grid(True)
        
        # Position loss
        axes[1].plot(self.history['train_position_loss'], label='Train')
        axes[1].plot(self.history['val_position_loss'], label='Validation')
        axes[1].set_xlabel('Epoch')
        axes[1].set_ylabel('Position Loss')
        axes[1].set_title('Position Prediction Loss')
        axes[1].legend()
        axes[1].grid(True)
        
        # Learning rate
        axes[2].plot(self.history['learning_rates'])
        axes[2].set_xlabel('Epoch')
        axes[2].set_ylabel('Learning Rate')
        axes[2].set_title('Learning Rate Schedule')
        axes[2].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            logger.info(f"Saved training plot to {save_path}")
        else:
            plt.show()


def load_ngsim_data(data_path: str, sample_ratio: float = 1.0) -> pd.DataFrame:
    """Load and preprocess NGSIM telemetry data"""
    telemetry_file = os.path.join(data_path, 'ngsim_telemetry.csv')
    
    if not os.path.exists(telemetry_file):
        raise FileNotFoundError(f"Telemetry file not found: {telemetry_file}")
    
    logger.info(f"Loading telemetry data from {telemetry_file}")
    df = pd.read_csv(telemetry_file)
    
    # Filter valid records
    df = df.dropna(subset=['latitude', 'longitude', 'speed', 'timestamp', 'acceleration'])
    
    # Sort by vehicle and timestamp
    df = df.sort_values(['vehicle_id', 'timestamp']).reset_index(drop=True)
    
    # Optional sampling for faster experimentation
    if sample_ratio < 1.0:
        df = df.sample(frac=sample_ratio, random_state=42).reset_index(drop=True)
    
    logger.info(f"Loaded {len(df)} valid records")
    return df


def prepare_features(df: pd.DataFrame, feature_names: List[str]) -> Tuple[np.ndarray, StandardScaler]:
    """Prepare feature matrix and scale"""
    features = df[feature_names].values
    
    # Scale features
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    logger.info(f"Prepared features: {features_scaled.shape}")
    return features_scaled, scaler


def main():
    """Main training script"""
    parser = argparse.ArgumentParser(description='Train ST-GNN model on NGSIM data')
    parser.add_argument('--data-path', required=True, help='Path to processed NGSIM data directory')
    parser.add_argument('--output-dir', default='outputs', help='Output directory for models and plots')
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=64, help='Batch size')
    parser.add_argument('--sequence-length', type=int, default=50, help='Input sequence length')
    parser.add_argument('--prediction-horizon', type=int, default=10, help='Prediction horizon')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Hidden layer dimension')
    parser.add_argument('--num-layers', type=int, default=2, help='Number of LSTM layers')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--weight-decay', type=float, default=1e-4, help='Weight decay')
    parser.add_argument('--dropout', type=float, default=0.2, help='Dropout rate')
    parser.add_argument('--sample-ratio', type=float, default=1.0, help='Data sampling ratio for faster experiments')
    parser.add_argument('--resume', type=str, default=None, help='Path to checkpoint to resume training')
    args = parser.parse_args()
    
    # Set random seeds for reproducibility
    torch.manual_seed(42)
    np.random.seed(42)
    
    # Load data
    df = load_ngsim_data(args.data_path, args.sample_ratio)
    
    # Define features
    feature_names = ['speed', 'acceleration', 'latitude', 'longitude']
    
    # Prepare features
    features_scaled, scaler = prepare_features(df, feature_names)
    
    # Create dataset
    dataset = TrajectoryDataset(
        data=features_scaled,
        sequence_length=args.sequence_length,
        prediction_horizon=args.prediction_horizon,
        feature_names=feature_names
    )
    
    # Split data
    train_size = int(0.7 * len(dataset))
    val_size = int(0.15 * len(dataset))
    test_size = len(dataset) - train_size - val_size
    
    train_dataset, val_dataset, test_dataset = random_split(
        dataset, [train_size, val_size, test_size],
        generator=torch.Generator().manual_seed(42)
    )
    
    logger.info(f"Dataset split: train={train_size}, val={val_size}, test={test_size}")
    
    # Create data loaders
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    
    # Create model
    model = STGNNTrajectoryModel(
        input_dim=len(feature_names),
        hidden_dim=args.hidden_dim,
        num_layers=args.num_layers,
        output_dim=len(feature_names),
        prediction_horizon=args.prediction_horizon,
        dropout=args.dropout
    )
    
    logger.info(f"Model created with {sum(p.numel() for p in model.parameters()):,} parameters")
    
    # Create trainer
    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        output_dir=args.output_dir
    )
    
    # Resume training if checkpoint provided
    if args.resume:
        trainer.load_checkpoint(args.resume)
        logger.info(f"Resumed training from {args.resume}")
    
    # Train model
    history = trainer.train(epochs=args.epochs)
    
    # Evaluate on test set
    test_metrics = trainer.evaluate(test_loader)
    
    # Save final model
    trainer.save_checkpoint("final_model.pth")
    
    # Plot training history
    trainer.plot_training_history(save_path=os.path.join(args.output_dir, "training_history.png"))
    
    # Save training metrics
    metrics_path = os.path.join(args.output_dir, "training_metrics.json")
    with open(metrics_path, 'w') as f:
        json.dump({
            'history': {k: v[-1] if isinstance(v, list) else v for k, v in history.items()},
            'test_metrics': test_metrics
        }, f, indent=2)
    
    logger.info(f"Training complete! Results saved to {args.output_dir}")
    logger.info(f"Final test loss: {test_metrics['test_loss']:.4f}")
    logger.info(f"Final test RMSE: {test_metrics['test_rmse']:.4f}")


if __name__ == '__main__':
    main()