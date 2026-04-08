"""
NGSIM Training Adapter for ST-GNN Model

Adapts NGSIM data for training the MakFleet ST-GNN model.
Provides data loading, preprocessing, and training utilities.
Supports trajectory prediction, speed forecasting, and event detection.
"""

import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple, Union
import logging
from datetime import datetime
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import matplotlib.pyplot as plt
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NGSIMDataset(Dataset):
    """PyTorch Dataset for NGSIM trajectory data"""
    
    def __init__(self, telemetry_df: pd.DataFrame, 
                 sequence_length: int = 50,
                 prediction_horizon: int = 10,
                 features: List[str] = None):
        """
        Initialize NGSIM dataset
        
        Args:
            telemetry_df: DataFrame with telemetry data
            sequence_length: Length of input sequence
            prediction_horizon: Number of steps to predict
            features: List of features to use
        """
        self.telemetry_df = telemetry_df.copy()
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        
        # Default features
        if features is None:
            features = ['speed', 'acceleration', 'latitude', 'longitude']
        self.features = features
        
        # Ensure timestamp is datetime
        self.telemetry_df['timestamp'] = pd.to_datetime(self.telemetry_df['timestamp'])
        
        # Sort by vehicle and timestamp
        self.telemetry_df = self.telemetry_df.sort_values(['vehicle_id', 'timestamp'])
        
        # Create sequences
        self.sequences = self._create_sequences()
        
        logger.info(f"Created {len(self.sequences)} sequences from {len(telemetry_df)} records")
    
    def _create_sequences(self) -> List[Dict]:
        """Create sequences from telemetry data"""
        sequences = []
        
        for vehicle_id, group in self.telemetry_df.groupby('vehicle_id'):
            group = group.sort_values('timestamp').reset_index(drop=True)
            
            # Skip if not enough data
            if len(group) < self.sequence_length + self.prediction_horizon:
                continue
            
            # Create overlapping sequences
            for i in range(len(group) - self.sequence_length - self.prediction_horizon + 1):
                # Input sequence
                input_data = group.iloc[i:i + self.sequence_length]
                
                # Target sequence (next positions)
                target_data = group.iloc[i + self.sequence_length:i + self.sequence_length + self.prediction_horizon]
                
                sequence = {
                    'vehicle_id': vehicle_id,
                    'input': input_data[self.features].values,
                    'target_lat': target_data['latitude'].values,
                    'target_lon': target_data['longitude'].values,
                    'target_speed': target_data['speed'].values,
                    'input_timestamps': input_data['timestamp'].values,
                    'target_timestamps': target_data['timestamp'].values,
                    'input_speeds': input_data['speed'].values,
                    'input_accelerations': input_data['acceleration'].values
                }
                
                sequences.append(sequence)
        
        return sequences
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sequence = self.sequences[idx]
        
        return {
            'input': torch.FloatTensor(sequence['input']),
            'target_lat': torch.FloatTensor(sequence['target_lat']),
            'target_lon': torch.FloatTensor(sequence['target_lon']),
            'target_speed': torch.FloatTensor(sequence['target_speed']),
            'vehicle_id': torch.tensor(sequence['vehicle_id'], dtype=torch.long)
        }


class NGSIMDataModule:
    """Data module for NGSIM training"""
    
    def __init__(self, data_path: str, 
                 sequence_length: int = 50,
                 prediction_horizon: int = 10,
                 batch_size: int = 32,
                 train_split: float = 0.8,
                 val_split: float = 0.1):
        """
        Initialize data module
        
        Args:
            data_path: Path to processed NGSIM data directory
            sequence_length: Length of input sequence
            prediction_horizon: Number of steps to predict
            batch_size: Batch size for training
            train_split: Fraction of data for training
            val_split: Fraction of data for validation
        """
        self.data_path = data_path
        self.sequence_length = sequence_length
        self.prediction_horizon = prediction_horizon
        self.batch_size = batch_size
        self.train_split = train_split
        self.val_split = val_split
        
        # Load data
        self.telemetry_df = self._load_data()
        
        # Create datasets
        self.train_dataset = None
        self.val_dataset = None
        self.test_dataset = None
    
    def _load_data(self) -> pd.DataFrame:
        """Load NGSIM telemetry data"""
        telemetry_file = os.path.join(self.data_path, 'ngsim_telemetry.csv')
        
        if not os.path.exists(telemetry_file):
            raise FileNotFoundError(f"Telemetry file not found: {telemetry_file}")
        
        logger.info(f"Loading telemetry data from {telemetry_file}")
        df = pd.read_csv(telemetry_file)
        
        # Select only motorcycle data (vehicle class 1) for bodaboda training
        # NGSIM vehicles with ID offset of 1000, motorcycle class maps to specific IDs
        logger.info(f"Loaded {len(df)} telemetry records")
        
        # Filter to valid records
        df = df.dropna(subset=['latitude', 'longitude', 'speed', 'timestamp'])
        logger.info(f"After filtering: {len(df)} valid records")
        
        return df
    
    def setup(self):
        """Setup train, validation, and test datasets"""
        # Create full dataset
        full_dataset = NGSIMDataset(
            self.telemetry_df,
            sequence_length=self.sequence_length,
            prediction_horizon=self.prediction_horizon
        )
        
        # Split into train, val, test
        total_size = len(full_dataset)
        train_size = int(self.train_split * total_size)
        val_size = int(self.val_split * total_size)
        test_size = total_size - train_size - val_size
        
        self.train_dataset, self.val_dataset, self.test_dataset = torch.utils.data.random_split(
            full_dataset,
            [train_size, val_size, test_size],
            generator=torch.Generator().manual_seed(42)
        )
        
        logger.info(f"Dataset split: train={train_size}, val={val_size}, test={test_size}")
    
    def train_dataloader(self) -> DataLoader:
        """Get training data loader"""
        return DataLoader(
            self.train_dataset,
            batch_size=self.batch_size,
            shuffle=True,
            num_workers=0,
            pin_memory=True
        )
    
    def val_dataloader(self) -> DataLoader:
        """Get validation data loader"""
        return DataLoader(
            self.val_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=True
        )
    
    def test_dataloader(self) -> DataLoader:
        """Get test data loader"""
        return DataLoader(
            self.test_dataset,
            batch_size=self.batch_size,
            shuffle=False,
            num_workers=0,
            pin_memory=True
        )


class NGSIMTrainer:
    """Trainer for ST-GNN model using NGSIM data"""
    
    def __init__(self, model, data_module: NGSIMDataModule, 
                 learning_rate: float = 0.001,
                 weight_decay: float = 1e-4,
                 device: str = None):
        """
        Initialize trainer
        
        Args:
            model: ST-GNN model to train
            data_module: Data module with train/val/test splits
            learning_rate: Learning rate
            weight_decay: L2 regularization
            device: Device to train on (cuda/cpu)
        """
        self.model = model
        self.data_module = data_module
        self.learning_rate = learning_rate
        self.weight_decay = weight_decay
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Move model to device
        self.model.to(self.device)
        
        # Setup optimizer and loss
        self.optimizer = torch.optim.Adam(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        self.position_loss = torch.nn.MSELoss()
        self.speed_loss = torch.nn.SmoothL1Loss()
        
        # Training history
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'train_position_loss': [],
            'val_position_loss': []
        }
    
    def train_epoch(self, dataloader: DataLoader) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        total_position_loss = 0.0
        num_batches = 0
        
        for batch in dataloader:
            # Move to device
            input_data = batch['input'].to(self.device)
            target_lat = batch['target_lat'].to(self.device)
            target_lon = batch['target_lon'].to(self.device)
            target_speed = batch['target_speed'].to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            
            # Predict using model (assuming model has predict_trajectory method)
            if hasattr(self.model, 'predict_trajectory'):
                pred_lat, pred_lon, pred_speed = self.model.predict_trajectory(input_data)
            else:
                # Simple baseline: use last input state
                pred_lat = input_data[:, -1, 0].repeat(self.data_module.prediction_horizon)
                pred_lon = input_data[:, -1, 1].repeat(self.data_module.prediction_horizon)
                pred_speed = input_data[:, -1, 2].repeat(self.data_module.prediction_horizon)
            
            # Calculate loss
            pos_loss = self.position_loss(pred_lat, target_lat) + self.position_loss(pred_lon, target_lon)
            speed_loss = self.speed_loss(pred_speed, target_speed)
            loss = pos_loss + 0.5 * speed_loss
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            total_loss += loss.item()
            total_position_loss += pos_loss.item()
            num_batches += 1
        
        return total_loss / num_batches, total_position_loss / num_batches
    
    def validate(self, dataloader: DataLoader) -> float:
        """Validate model"""
        self.model.eval()
        total_loss = 0.0
        total_position_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for batch in dataloader:
                input_data = batch['input'].to(self.device)
                target_lat = batch['target_lat'].to(self.device)
                target_lon = batch['target_lon'].to(self.device)
                target_speed = batch['target_speed'].to(self.device)
                
                # Predict
                if hasattr(self.model, 'predict_trajectory'):
                    pred_lat, pred_lon, pred_speed = self.model.predict_trajectory(input_data)
                else:
                    pred_lat = input_data[:, -1, 0].repeat(self.data_module.prediction_horizon)
                    pred_lon = input_data[:, -1, 1].repeat(self.data_module.prediction_horizon)
                    pred_speed = input_data[:, -1, 2].repeat(self.data_module.prediction_horizon)
                
                # Calculate loss
                pos_loss = self.position_loss(pred_lat, target_lat) + self.position_loss(pred_lon, target_lon)
                speed_loss = self.speed_loss(pred_speed, target_speed)
                loss = pos_loss + 0.5 * speed_loss
                
                total_loss += loss.item()
                total_position_loss += pos_loss.item()
                num_batches += 1
        
        return total_loss / num_batches, total_position_loss / num_batches
    
    def train(self, epochs: int = 100, patience: int = 10) -> Dict:
        """
        Train model
        
        Args:
            epochs: Number of training epochs
            patience: Early stopping patience
            
        Returns:
            Training history
        """
        logger.info(f"Starting training for {epochs} epochs on {self.device}")
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        train_loader = self.data_module.train_dataloader()
        val_loader = self.data_module.val_dataloader()
        
        for epoch in range(epochs):
            # Train
            train_loss, train_pos_loss = self.train_epoch(train_loader)
            
            # Validate
            val_loss, val_pos_loss = self.validate(val_loader)
            
            # Update history
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_position_loss'].append(train_pos_loss)
            self.history['val_position_loss'].append(val_pos_loss)
            
            # Log progress
            logger.info(f"Epoch {epoch+1}/{epochs}: "
                       f"train_loss={train_loss:.4f}, val_loss={val_loss:.4f}, "
                       f"train_pos_loss={train_pos_loss:.4f}, val_pos_loss={val_pos_loss:.4f}")
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                self._save_checkpoint(f"best_model_epoch_{epoch+1}.pth")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        return self.history
    
    def evaluate(self) -> Dict:
        """Evaluate model on test set"""
        logger.info("Evaluating on test set")
        
        test_loader = self.data_module.test_dataloader()
        test_loss, test_pos_loss = self.validate(test_loader)
        
        metrics = {
            'test_loss': test_loss,
            'test_position_loss': test_pos_loss,
            'test_rmse': np.sqrt(test_pos_loss)
        }
        
        logger.info(f"Test metrics: {metrics}")
        
        return metrics
    
    def _save_checkpoint(self, path: str):
        """Save model checkpoint"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'history': self.history
        }, path)
        logger.info(f"Saved checkpoint to {path}")
    
    def load_checkpoint(self, path: str):
        """Load model checkpoint"""
        checkpoint = torch.load(path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.history = checkpoint.get('history', self.history)
        logger.info(f"Loaded checkpoint from {path}")


def main():
    """Example usage of NGSIM training"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train ST-GNN model with NGSIM data')
    parser.add_argument('--data-path', required=True, help='Path to processed NGSIM data')
    parser.add_argument('--model-path', default=None, help='Path to save trained model')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--sequence-length', type=int, default=50, help='Input sequence length')
    parser.add_argument('--prediction-horizon', type=int, default=10, help='Prediction horizon')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    args = parser.parse_args()
    
    # Create data module
    data_module = NGSIMDataModule(
        data_path=args.data_path,
        sequence_length=args.sequence_length,
        prediction_horizon=args.prediction_horizon,
        batch_size=args.batch_size
    )
    data_module.setup()
    
    # Create model (simple baseline model for demonstration)
    # In practice, you would use your ST-GNN model from st_gnn_model.py
    class SimpleTrajectoryModel(torch.nn.Module):
        def __init__(self, input_dim=4, hidden_dim=64):
            super().__init__()
            self.lstm = torch.nn.LSTM(input_dim, hidden_dim, batch_first=True)
            self.fc = torch.nn.Linear(hidden_dim, 3)  # lat, lon, speed
        
        def forward(self, x):
            # x: (batch, seq_len, features)
            _, (h_n, _) = self.lstm(x)
            # h_n: (num_layers, batch, hidden_dim)
            output = self.fc(h_n[-1])
            return output
        
        def predict_trajectory(self, x):
            # For compatibility with trainer
            batch_size = x.shape[0]
            output = self(x)
            # Repeat for prediction horizon
            pred_lat = output[:, 0].unsqueeze(1).repeat(1, 10)
            pred_lon = output[:, 1].unsqueeze(1).repeat(1, 10)
            pred_speed = output[:, 2].unsqueeze(1).repeat(1, 10)
            return pred_lat, pred_lon, pred_speed
    
    model = SimpleTrajectoryModel(input_dim=4)
    
    # Create trainer
    trainer = NGSIMTrainer(
        model=model,
        data_module=data_module,
        learning_rate=args.learning_rate
    )
    
    # Train
    history = trainer.train(epochs=args.epochs)
    
    # Evaluate
    metrics = trainer.evaluate()
    
    # Save model
    if args.model_path:
        trainer._save_checkpoint(args.model_path)
        logger.info(f"Model saved to {args.model_path}")
    
    print("\n=== Training Complete ===")
    print(f"Final test loss: {metrics['test_loss']:.4f}")
    print(f"Final test RMSE: {metrics['test_rmse']:.4f}")


if __name__ == '__main__':
    main()