"""
NGSIM Data Sampler

Reduces NGSIM dataset size by sampling vehicles and frames while preserving
essential traffic patterns and dynamics.

Usage:
    python data_pipeline/ngsim_sampler.py --input data/ngsim/raw/ngsim_data.csv --ratio 0.1
"""

import pandas as pd
import numpy as np
import argparse
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NGSIMSampler:
    """Samples NGSIM data to create smaller datasets"""
    
    def __init__(self, 
                 vehicle_ratio: float = 0.1,
                 frame_ratio: float = 0.2,
                 min_vehicles: int = 50,
                 max_vehicles: int = 500,
                 seed: int = 42):
        """
        Initialize sampler
        
        Args:
            vehicle_ratio: Fraction of vehicles to keep (0.0-1.0)
            frame_ratio: Fraction of frames to keep per vehicle (0.0-1.0)
            min_vehicles: Minimum number of vehicles to sample
            max_vehicles: Maximum number of vehicles to sample
            seed: Random seed for reproducibility
        """
        self.vehicle_ratio = vehicle_ratio
        self.frame_ratio = frame_ratio
        self.min_vehicles = min_vehicles
        self.max_vehicles = max_vehicles
        self.seed = seed
        
        np.random.seed(seed)
    
    def sample_vehicles(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sample a subset of vehicles while preserving class distribution
        
        Args:
            df: Full NGSIM DataFrame
            
        Returns:
            DataFrame with sampled vehicles
        """
        logger.info(f"Original dataset: {len(df)} records, {df['Vehicle_ID'].nunique()} vehicles")
        
        # Get unique vehicles with their class
        class_col = 'v_Class' if 'v_Class' in df.columns else 'Veh_Class'
        vehicles_by_class = df.groupby('Vehicle_ID')[class_col].first()
        
        # Calculate number of vehicles to sample
        total_vehicles = len(vehicles_by_class)
        target_vehicles = int(total_vehicles * self.vehicle_ratio)
        target_vehicles = max(self.min_vehicles, min(target_vehicles, self.max_vehicles))
        
        # Sample vehicles while preserving class distribution
        sampled_vehicles = []
        for vehicle_class in vehicles_by_class.unique():
            class_vehicles = vehicles_by_class[vehicles_by_class == vehicle_class].index.tolist()
            n_sample = max(1, int(len(class_vehicles) * self.vehicle_ratio))
            sampled = np.random.choice(class_vehicles, size=n_sample, replace=False)
            sampled_vehicles.extend(sampled)
        
        # Filter to sampled vehicles
        sampled_df = df[df['Vehicle_ID'].isin(sampled_vehicles)].copy()
        
        logger.info(f"Sampled {len(sampled_vehicles)} vehicles ({self.vehicle_ratio*100:.0f}% of original)")
        
        return sampled_df
    
    def sample_frames(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Sample frames for each vehicle while preserving trajectory continuity
        
        Args:
            df: DataFrame with vehicle data
            
        Returns:
            DataFrame with sampled frames
        """
        sampled_dfs = []
        
        for vehicle_id, group in df.groupby('Vehicle_ID'):
            group = group.sort_values('Frame_ID')
            
            # For each vehicle, sample frames but keep contiguous blocks
            n_frames = len(group)
            n_sample = max(10, int(n_frames * self.frame_ratio))
            
            # Sample contiguous blocks to preserve trajectory patterns
            if n_sample >= n_frames:
                sampled_dfs.append(group)
            else:
                # Divide into blocks and sample some
                block_size = max(5, n_frames // (n_frames // n_sample + 1))
                n_blocks = n_frames // block_size
                
                # Sample contiguous blocks
                n_sample_blocks = max(1, int(n_blocks * self.frame_ratio))
                block_indices = np.random.choice(n_blocks, size=n_sample_blocks, replace=False)
                
                sampled_indices = []
                for block_idx in block_indices:
                    start = block_idx * block_size
                    end = min(start + block_size, n_frames)
                    sampled_indices.extend(range(start, end))
                
                sampled_indices = sorted(sampled_indices)
                sampled_group = group.iloc[sampled_indices]
                sampled_dfs.append(sampled_group)
        
        result = pd.concat(sampled_dfs, ignore_index=True)
        logger.info(f"Sampled frames: {len(result)} records ({self.frame_ratio*100:.0f}% of input)")
        
        return result
    
    def sample(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply both vehicle and frame sampling
        
        Args:
            df: Full NGSIM DataFrame
            
        Returns:
            Sampled DataFrame
        """
        logger.info(f"Starting sampling process...")
        logger.info(f"  Vehicle ratio: {self.vehicle_ratio}")
        logger.info(f"  Frame ratio: {self.frame_ratio}")
        
        # Step 1: Sample vehicles
        sampled_df = self.sample_vehicles(df)
        
        # Step 2: Sample frames for each vehicle
        sampled_df = self.sample_frames(sampled_df)
        
        logger.info(f"Final sampled dataset: {len(sampled_df)} records")
        logger.info(f"  Vehicles: {sampled_df['Vehicle_ID'].nunique()}")
        logger.info(f"  Size reduction: {(1 - len(sampled_df)/len(df))*100:.1f}%")
        
        return sampled_df


def main():
    """Command-line interface for NGSIM sampler"""
    parser = argparse.ArgumentParser(description='Sample NGSIM data to reduce size')
    parser.add_argument('--input', required=True, help='Input CSV file')
    parser.add_argument('--output', default=None, help='Output CSV file')
    parser.add_argument('--vehicle-ratio', type=float, default=0.1, 
                       help='Fraction of vehicles to keep (default: 0.1)')
    parser.add_argument('--frame-ratio', type=float, default=0.2,
                       help='Fraction of frames to keep per vehicle (default: 0.2)')
    parser.add_argument('--max-vehicles', type=int, default=200,
                       help='Maximum number of vehicles to sample (default: 200)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed (default: 42)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show sampling stats without saving')
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"Loading data from {args.input}")
    df = pd.read_csv(args.input, thousands=',')
    original_size = len(df)
    original_mb = os.path.getsize(args.input) / (1024*1024)
    
    logger.info(f"Original: {original_size:,} records ({original_mb:.1f} MB)")
    
    # Create sampler
    sampler = NGSIMSampler(
        vehicle_ratio=args.vehicle_ratio,
        frame_ratio=args.frame_ratio,
        max_vehicles=args.max_vehicles,
        seed=args.seed
    )
    
    # Sample data
    sampled_df = sampler.sample(df)
    
    # Calculate size reduction
    reduction = (1 - len(sampled_df) / original_size) * 100
    estimated_mb = original_mb * (len(sampled_df) / original_size)
    
    logger.info(f"\n=== Sampling Summary ===")
    logger.info(f"Records: {original_size:,} → {len(sampled_df):,} ({reduction:.1f}% reduction)")
    logger.info(f"Vehicles: {df['Vehicle_ID'].nunique()} → {sampled_df['Vehicle_ID'].nunique()}")
    logger.info(f"Estimated size: {original_mb:.1f} MB → {estimated_mb:.1f} MB")
    
    # Save if not dry run
    if not args.dry_run:
        output_path = args.output or args.input.replace('.csv', '_sampled.csv')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        sampled_df.to_csv(output_path, index=False)
        logger.info(f"Saved sampled data to: {output_path}")
    else:
        logger.info("Dry run - no file saved")


if __name__ == '__main__':
    main()