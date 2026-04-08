"""
NGSIM Data Parser

Parses NGSIM trajectory data files into structured format for MakFleet data warehouse.
NGSIM files are space-delimited text files with vehicle trajectory data.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class NGSIMRecord:
    """Represents a single NGSIM trajectory record"""
    frame_id: int
    vehicle_id: int
    local_x: float  # feet
    local_y: float  # feet
    velocity: float  # ft/s
    acceleration: float  # ft/s²
    lane_id: int
    preceding_vehicle_id: int
    following_vehicle_id: int
    spacing: float  # feet
    headway: float  # seconds
    vehicle_class: int
    vehicle_length: float  # feet
    vehicle_type: str


class NGSIMParser:
    """Parser for NGSIM trajectory data files"""
    
    # NGSIM site configurations
    SITE_CONFIGS = {
        'I-80': {
            'reference_lat': 37.9372,
            'reference_lon': -122.2608,
            'rotation_angle': 52.5,  # degrees
            'frame_rate': 10,  # frames per second
            'start_times': {
                '0750-0800': '07:50:00',
                '0805-0815': '08:05:00',
                '0815-0830': '08:15:00'
            }
        },
        'US-101': {
            'reference_lat': 34.0522,
            'reference_lon': -118.2437,
            'rotation_angle': 38.2,
            'frame_rate': 10,
            'start_times': {
                '0750-0805': '07:50:00',
                '0805-0815': '08:05:00',
                '0825-0835': '08:25:00'
            }
        },
        'Lankershim': {
            'reference_lat': 34.1508,
            'reference_lon': -118.3742,
            'rotation_angle': 15.8,
            'frame_rate': 10,
            'start_times': {
                '0830-0845': '08:30:00',
                '0845-0900': '08:45:00',
                '0900-0915': '09:00:00'
            }
        }
    }
    
    # Vehicle class mapping
    VEHICLE_CLASS_MAP = {
        1: 'motorcycle',
        2: 'passenger_car',
        3: 'other',
        4: 'heavy_truck'
    }
    
    def __init__(self, site_name: str = 'I-80'):
        """
        Initialize NGSIM parser
        
        Args:
            site_name: Name of NGSIM site (I-80, US-101, Lankershim)
        """
        if site_name not in self.SITE_CONFIGS:
            raise ValueError(f"Unknown site: {site_name}. Choose from {list(self.SITE_CONFIGS.keys())}")
        
        self.site_name = site_name
        self.config = self.SITE_CONFIGS[site_name]
        
    def parse_file(self, filepath: str) -> pd.DataFrame:
        """
        Parse a single NGSIM trajectory file
        
        Args:
            filepath: Path to NGSIM .txt or .csv file
            
        Returns:
            DataFrame with parsed trajectory data
        """
        logger.info(f"Parsing NGSIM file: {filepath}")
        
        try:
            # Detect file type based on extension
            is_csv = filepath.lower().endswith('.csv')
            
            if is_csv:
                # CSV format (from data.transportation.gov)
                # Numbers may have thousands separators (e.g., '9,999')
                df = pd.read_csv(
                    filepath,
                    thousands=',',  # Handle thousands separators
                    dtype={
                        'Frame_ID': np.int32,
                        'Vehicle_ID': np.int32,
                        'Local_X': np.float32,
                        'Local_Y': np.float32,
                        'v_Vel': np.float32,
                        'v_Acc': np.float32,
                        'Lane_ID': np.int8,
                        'Prec_Veh_ID': np.int32,
                        'Fol_Veh_ID': np.int32,
                        'Spacing': np.float32,
                        'Headway': np.float32,
                        'Veh_Class': np.int8,
                        'Veh_Length': np.float32,
                        'Veh_Type': np.int8
                    }
                )
            else:
                # Space-delimited format (original NGSIM .txt files)
                df = pd.read_csv(
                    filepath,
                    delim_whitespace=True,
                    comment='#',
                    header=0,
                    dtype={
                        'Frame_ID': np.int32,
                        'Vehicle_ID': np.int32,
                        'Local_X': np.float32,
                        'Local_Y': np.float32,
                        'v_Vel': np.float32,
                        'v_Acc': np.float32,
                        'Lane_ID': np.int8,
                        'Prec_Veh_ID': np.int32,
                        'Fol_Veh_ID': np.int32,
                        'Spacing': np.float32,
                        'Headway': np.float32,
                        'Veh_Class': np.int8,
                        'Veh_Length': np.float32,
                        'Veh_Type': np.int8
                    }
                )
            
            # Add metadata
            df['site'] = self.site_name
            df['source_file'] = os.path.basename(filepath)
            
            # Extract time period from filename
            filename = os.path.basename(filepath)
            df['time_period'] = self._extract_time_period(filename)
            
            logger.info(f"Parsed {len(df)} records from {filepath}")
            return df
            
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            raise
    
    def parse_directory(self, directory: str) -> pd.DataFrame:
        """
        Parse all NGSIM files in a directory
        
        Args:
            directory: Path to directory containing NGSIM .txt files
            
        Returns:
            Combined DataFrame with all trajectory data
        """
        logger.info(f"Parsing NGSIM directory: {directory}")
        
        all_dataframes = []
        
        # Find all .txt files
        txt_files = [f for f in os.listdir(directory) if f.endswith('.txt')]
        
        if not txt_files:
            raise FileNotFoundError(f"No .txt files found in {directory}")
        
        for txt_file in sorted(txt_files):
            filepath = os.path.join(directory, txt_file)
            try:
                df = self.parse_file(filepath)
                all_dataframes.append(df)
            except Exception as e:
                logger.warning(f"Skipping {filepath}: {e}")
        
        if not all_dataframes:
            raise ValueError(f"No valid NGSIM files found in {directory}")
        
        # Combine all dataframes
        combined_df = pd.concat(all_dataframes, ignore_index=True)
        logger.info(f"Combined {len(combined_df)} records from {len(txt_files)} files")
        
        return combined_df
    
    def _extract_time_period(self, filename: str) -> str:
        """Extract time period from filename (e.g., '0750-0800' from 'trajectories_I-80_0750-0800.txt')"""
        # Look for pattern like 0750-0800
        import re
        match = re.search(r'(\d{4}-\d{4})', filename)
        return match.group(1) if match else 'unknown'
    
    def get_site_config(self) -> Dict:
        """Get configuration for current site"""
        return self.config.copy()
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Validate NGSIM data and separate valid/invalid records
        
        Args:
            df: Raw NGSIM DataFrame
            
        Returns:
            Tuple of (valid_df, invalid_df)
        """
        logger.info("Validating NGSIM data")
        
        # Handle different column name formats
        # CSV from data.transportation.gov uses 'v_Class', original NGSIM uses 'Veh_Class'
        class_col = 'v_Class' if 'v_Class' in df.columns else 'Veh_Class'
        
        # Create validation flags
        valid_mask = (
            df['Local_X'].notna() & 
            df['Local_Y'].notna() &
            df['v_Vel'].notna() &
            df['Vehicle_ID'].notna() &
            (df['v_Vel'] >= 0) &  # Negative speed is invalid
            (df[class_col] >= 1) & (df[class_col] <= 4)  # Valid vehicle class
        )
        
        valid_df = df[valid_mask].copy()
        invalid_df = df[~valid_mask].copy()
        
        logger.info(f"Validation: {len(valid_df)} valid, {len(invalid_df)} invalid records")
        
        return valid_df, invalid_df
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Get statistics about NGSIM dataset
        
        Args:
            df: NGSIM DataFrame
            
        Returns:
            Dictionary of statistics
        """
        # Handle different column name formats
        class_col = 'v_Class' if 'v_Class' in df.columns else 'Veh_Class'
        
        stats = {
            'total_records': len(df),
            'unique_vehicles': df['Vehicle_ID'].nunique(),
            'unique_frames': df['Frame_ID'].nunique(),
            'vehicle_classes': df[class_col].value_counts().to_dict(),
            'sites': df['site'].value_counts().to_dict() if 'site' in df.columns else {},
            'time_periods': df['time_period'].value_counts().to_dict() if 'time_period' in df.columns else {},
            'speed_stats': {
                'min': float(df['v_Vel'].min()),
                'max': float(df['v_Vel'].max()),
                'mean': float(df['v_Vel'].mean()),
                'std': float(df['v_Vel'].std())
            },
            'acceleration_stats': {
                'min': float(df['v_Acc'].min()),
                'max': float(df['v_Acc'].max()),
                'mean': float(df['v_Acc'].mean()),
                'std': float(df['v_Acc'].std())
            }
        }
        
        return stats


def main():
    """Example usage of NGSIM parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse NGSIM trajectory data')
    parser.add_argument('--input', required=True, help='Input directory or file path')
    parser.add_argument('--output', default='data/ngsim/processed', help='Output directory')
    parser.add_argument('--site', default='I-80', choices=['I-80', 'US-101', 'Lankershim'])
    args = parser.parse_args()
    
    # Create parser
    ngsim_parser = NGSIMParser(site_name=args.site)
    
    # Parse data
    if os.path.isfile(args.input):
        df = ngsim_parser.parse_file(args.input)
    else:
        df = ngsim_parser.parse_directory(args.input)
    
    # Validate
    valid_df, invalid_df = ngsim_parser.validate_data(df)
    
    # Get statistics
    stats = ngsim_parser.get_statistics(valid_df)
    
    print("\n=== NGSIM Dataset Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Save processed data
    os.makedirs(args.output, exist_ok=True)
    output_file = os.path.join(args.output, 'ngsim_raw_parsed.csv')
    valid_df.to_csv(output_file, index=False)
    print(f"\nSaved processed data to: {output_file}")
    
    # Save invalid records for analysis
    if len(invalid_df) > 0:
        invalid_file = os.path.join(args.output, 'ngsim_invalid_records.csv')
        invalid_df.to_csv(invalid_file, index=False)
        print(f"Saved invalid records to: {invalid_file}")


if __name__ == '__main__':
    main()