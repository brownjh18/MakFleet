"""
NGSIM Data Transformer

Transforms parsed NGSIM data into MakFleet data warehouse format.
Handles coordinate transformation, unit conversion, and schema mapping.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import math
import logging
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NGSIMTransformer:
    """Transforms NGSIM data to MakFleet data warehouse format"""
    
    # Unit conversion constants
    FEET_TO_METERS = 0.3048
    FT_S_TO_KM_H = 1.09728  # ft/s to km/h
    FT_S2_TO_M_S2 = 0.3048  # ft/s² to m/s²
    
    # MakFleet vehicle ID mapping (synthetic)
    VEHICLE_ID_OFFSET = 1000  # Start MakFleet vehicle IDs from 1000
    
    def __init__(self, site_config: Dict, target_location: str = 'kampala'):
        """
        Initialize NGSIM transformer
        
        Args:
            site_config: NGSIM site configuration (from parser)
            target_location: Target location for coordinate transformation
        """
        self.site_config = site_config
        self.target_location = target_location
        
        # Target location reference points (Makerere University campus area)
        self.target_refs = {
            'kampala': {
                'lat': 0.3336,
                'lon': 32.5656,
                'description': 'Makerere University Main Library'
            }
        }
        
    def transform(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Transform NGSIM data to MakFleet format
        
        Args:
            df: Parsed NGSIM DataFrame
            
        Returns:
            Dictionary with transformed DataFrames:
            - telemetry: Telemetry data
            - vehicles: Vehicle data
            - events: Detected events
            - trips: Trip data
        """
        logger.info(f"Transforming {len(df)} NGSIM records to MakFleet format")
        
        # Transform each component
        telemetry_df = self._transform_telemetry(df)
        vehicles_df = self._transform_vehicles(df)
        events_df = self._transform_events(df)
        trips_df = self._transform_trips(df)
        
        logger.info(f"Transformation complete:")
        logger.info(f"  - Telemetry: {len(telemetry_df)} records")
        logger.info(f"  - Vehicles: {len(vehicles_df)} records")
        logger.info(f"  - Events: {len(events_df)} records")
        logger.info(f"  - Trips: {len(trips_df)} records")
        
        return {
            'telemetry': telemetry_df,
            'vehicles': vehicles_df,
            'events': events_df,
            'trips': trips_df
        }
    
    def _transform_telemetry(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform NGSIM data to MakFleet telemetry format"""
        
        # Convert coordinates from local (feet) to GPS
        gps_coords = self._convert_to_gps(df['Local_X'], df['Local_Y'])
        
        # Convert timestamp from frame ID
        timestamps = self._convert_frame_to_timestamp(df['Frame_ID'], df['time_period'])
        
        # Create telemetry DataFrame
        telemetry = pd.DataFrame({
            'vehicle_id': df['Vehicle_ID'] + self.VEHICLE_ID_OFFSET,
            'latitude': gps_coords['lat'],
            'longitude': gps_coords['lon'],
            'speed': df['v_Vel'] * self.FT_S_TO_KM_H,  # ft/s to km/h
            'acceleration': df['v_Acc'] * self.FT_S2_TO_M_S2,  # ft/s² to m/s²
            'timestamp': timestamps,
            'engine_temp': self._generate_engine_temp(df),  # Synthetic
            'fuel_level': self._generate_fuel_level(df),  # Synthetic
            'gps_accuracy': self._calculate_gps_accuracy(df),
            'data_quality_score': self._calculate_data_quality(df),
            'is_validated': True,
            'semantic_context': self._generate_semantic_context(df),
            'map_matched': True,
            'matched_location_id': self._generate_location_id(gps_coords),
            'match_confidence': 0.95,
            'provenance_id': self._generate_provenance_id(df)
        })
        
        # Sort by vehicle and timestamp
        telemetry = telemetry.sort_values(['vehicle_id', 'timestamp']).reset_index(drop=True)
        
        return telemetry
    
    def _transform_vehicles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform NGSIM vehicle data to MakFleet format"""
        
        # Handle different column name formats
        class_col = 'v_Class' if 'v_Class' in df.columns else 'Veh_Class'
        length_col = 'v_length' if 'v_length' in df.columns else 'Veh_Length'
        
        # Get unique vehicles
        unique_vehicles = df.groupby('Vehicle_ID').agg({
            class_col: 'first',
            length_col: 'mean',
            'site': 'first'
        }).reset_index()
        
        # Map vehicle class to MakFleet categories
        class_mapping = {
            1: 'motorcycle',  # Motorcycle → bodaboda
            2: 'scooter_standard',  # Passenger car → standard
            3: 'other',  # Other
            4: 'truck'  # Heavy truck
        }
        
        vehicles = pd.DataFrame({
            'vehicle_id': unique_vehicles['Vehicle_ID'] + self.VEHICLE_ID_OFFSET,
            'plate_number': unique_vehicles['Vehicle_ID'].apply(lambda x: f'NGSIM_{x:05d}'),
            'model': unique_vehicles[class_col].map(class_mapping),
            'status': 'active',
            'model_category': unique_vehicles[class_col].map(class_mapping),
            'driver_id': unique_vehicles['Vehicle_ID'].apply(lambda x: (x % 5) + 1)  # Map to existing drivers
        })
        
        return vehicles
    
    def _transform_events(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and transform events from NGSIM data"""
        
        events = []
        
        # Group by vehicle to detect events
        for vehicle_id, group in df.groupby('Vehicle_ID'):
            group = group.sort_values('Frame_ID')
            
            # Calculate derived metrics for event detection
            speeds = group['v_Vel'].values
            accelerations = group['v_Acc'].values
            timestamps = self._convert_frame_to_timestamp(group['Frame_ID'], group['time_period'].iloc[0])
            
            # Detect harsh braking (acceleration < -4 m/s²)
            harsh_braking_mask = (accelerations * self.FT_S2_TO_M_S2) < -4.0
            if harsh_braking_mask.any():
                braking_indices = np.where(harsh_braking_mask)[0]
                for idx in braking_indices:
                    events.append({
                        'vehicle_id': vehicle_id + self.VEHICLE_ID_OFFSET,
                        'event_type': 'HARSH_BRAKING',
                        'latitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lat'],
                        'longitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lon'],
                        'speed': speeds[idx] * self.FT_S_TO_KM_H,
                        'acceleration': accelerations[idx] * self.FT_S2_TO_M_S2,
                        'timestamp': timestamps.iloc[idx],
                        'severity': 'high' if accelerations[idx] < -13.1 else 'medium',  # -13.1 ft/s² = -4 m/s²
                        'confidence_score': 0.9,
                        'explanation': f'Harsh braking detected: {accelerations[idx] * self.FT_S2_TO_M_S2:.2f} m/s²',
                        'causal_factors': self._get_causal_factors(group, idx),
                        'ai_detected': False
                    })
            
            # Detect rapid acceleration (acceleration > 4 m/s²)
            rapid_accel_mask = (accelerations * self.FT_S2_TO_M_S2) > 4.0
            if rapid_accel_mask.any():
                accel_indices = np.where(rapid_accel_mask)[0]
                for idx in accel_indices:
                    events.append({
                        'vehicle_id': vehicle_id + self.VEHICLE_ID_OFFSET,
                        'event_type': 'RAPID_ACCELERATION',
                        'latitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lat'],
                        'longitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lon'],
                        'speed': speeds[idx] * self.FT_S_TO_KM_H,
                        'acceleration': accelerations[idx] * self.FT_S2_TO_M_S2,
                        'timestamp': timestamps.iloc[idx],
                        'severity': 'high' if accelerations[idx] > 13.1 else 'medium',
                        'confidence_score': 0.9,
                        'explanation': f'Rapid acceleration detected: {accelerations[idx] * self.FT_S2_TO_M_S2:.2f} m/s²',
                        'causal_factors': self._get_causal_factors(group, idx),
                        'ai_detected': False
                    })
            
            # Detect overspeed (speed > 70 km/h)
            overspeed_mask = (speeds * self.FT_S_TO_KM_H) > 70
            if overspeed_mask.any():
                overspeed_indices = np.where(overspeed_mask)[0]
                for idx in overspeed_indices:
                    events.append({
                        'vehicle_id': vehicle_id + self.VEHICLE_ID_OFFSET,
                        'event_type': 'OVERSPEED',
                        'latitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lat'],
                        'longitude': self._convert_to_gps(group['Local_X'].iloc[idx], group['Local_Y'].iloc[idx])['lon'],
                        'speed': speeds[idx] * self.FT_S_TO_KM_H,
                        'acceleration': accelerations[idx] * self.FT_S2_TO_M_S2,
                        'timestamp': timestamps.iloc[idx],
                        'severity': 'high' if speeds[idx] * self.FT_S_TO_KM_H > 100 else 'medium',
                        'confidence_score': 0.95,
                        'explanation': f'Overspeed detected: {speeds[idx] * self.FT_S_TO_KM_H:.1f} km/h',
                        'causal_factors': self._get_causal_factors(group, idx),
                        'ai_detected': False
                    })
        
        return pd.DataFrame(events)
    
    def _transform_trips(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform NGSIM data into trip segments"""
        
        trips = []
        
        # Group by vehicle to identify trips
        for vehicle_id, group in df.groupby('Vehicle_ID'):
            group = group.sort_values('Frame_ID')
            
            # Split into trips based on gaps in frames (>300 frames = 30 seconds gap)
            frame_diffs = group['Frame_ID'].diff().fillna(0)
            trip_breaks = (frame_diffs > 300).cumsum()
            
            for trip_id, trip_group in group.groupby(trip_breaks):
                if len(trip_group) < 10:  # Skip very short trips
                    continue
                
                start_time = self._convert_frame_to_timestamp(trip_group['Frame_ID'].min(), trip_group['time_period'].iloc[0])
                end_time = self._convert_frame_to_timestamp(trip_group['Frame_ID'].max(), trip_group['time_period'].iloc[0])
                
                start_coords = self._convert_to_gps(trip_group['Local_X'].iloc[0], trip_group['Local_Y'].iloc[0])
                end_coords = self._convert_to_gps(trip_group['Local_X'].iloc[-1], trip_group['Local_Y'].iloc[-1])
                
                distance = self._calculate_distance(trip_group)
                duration = (end_time - start_time).total_seconds() / 60.0  # minutes
                avg_speed = trip_group['v_Vel'].mean() * self.FT_S_TO_KM_H
                max_speed = trip_group['v_Vel'].max() * self.FT_S_TO_KM_H
                
                trips.append({
                    'vehicle_id': vehicle_id + self.VEHICLE_ID_OFFSET,
                    'driver_id': (vehicle_id % 5) + 1,
                    'route_id': None,  # Will be assigned later
                    'start_time': start_time,
                    'end_time': end_time,
                    'start_location_id': self._generate_location_id(start_coords),
                    'end_location_id': self._generate_location_id(end_coords),
                    'distance_km': distance,
                    'duration_min': duration,
                    'avg_speed': avg_speed,
                    'max_speed': max_speed,
                    'status': 'completed'
                })
        
        return pd.DataFrame(trips)
    
    def _convert_to_gps(self, local_x: pd.Series, local_y: pd.Series) -> Dict[str, pd.Series]:
        """
        Convert local NGSIM coordinates to GPS coordinates
        
        Uses affine transformation with rotation and translation
        """
        # Get site configuration
        ref_lat = self.site_config['reference_lat']
        ref_lon = self.site_config['reference_lon']
        rotation = math.radians(self.site_config['rotation_angle'])
        
        # Convert feet to meters
        x_meters = local_x * self.FEET_TO_METERS
        y_meters = local_y * self.FEET_TO_METERS
        
        # Apply rotation
        x_rotated = x_meters * math.cos(rotation) - y_meters * math.sin(rotation)
        y_rotated = x_meters * math.sin(rotation) + y_meters * math.cos(rotation)
        
        # Convert meters to degrees (approximate)
        # 1 degree latitude ≈ 111,320 meters
        # 1 degree longitude ≈ 111,320 * cos(latitude) meters
        lat_deg = y_rotated / 111320.0
        lon_deg = x_rotated / (111320.0 * math.cos(math.radians(ref_lat)))
        
        # Translate to reference point
        gps_lat = ref_lat + lat_deg
        gps_lon = ref_lon + lon_deg
        
        return {'lat': gps_lat, 'lon': gps_lon}
    
    def _convert_frame_to_timestamp(self, frame_id: pd.Series, time_period: str) -> pd.Series:
        """Convert NGSIM frame ID to timestamp"""
        # Get frame rate from site config
        frame_rate = self.site_config['frame_rate']
        
        # Get start time for time period
        start_time_str = self.site_config['start_times'].get(time_period, '08:00:00')
        base_time = datetime.strptime(start_time_str, '%H:%M:%S')
        
        # Calculate timestamp for each frame
        # Frame IDs start from 1
        timestamps = [base_time + timedelta(seconds=(fid - 1) / frame_rate) for fid in frame_id]
        
        return pd.Series(timestamps)
    
    def _generate_engine_temp(self, df: pd.DataFrame) -> pd.Series:
        """Generate synthetic engine temperature based on speed and acceleration"""
        # Base temperature + speed/acceleration effects
        base_temp = 85.0  # Base engine temp in °C
        speed_effect = df['v_Vel'] * 0.1  # Speed increases temp
        accel_effect = np.abs(df['v_Acc']) * 2.0  # Acceleration increases temp more
        
        # Add some noise
        noise = np.random.normal(0, 2, len(df))
        
        return (base_temp + speed_effect + accel_effect + noise).clip(70, 110)
    
    def _generate_fuel_level(self, df: pd.DataFrame) -> pd.Series:
        """Generate synthetic fuel level (decreasing over time)"""
        # Start with random fuel level between 50-100%
        # Decrease based on distance traveled
        
        fuel_levels = []
        for vehicle_id, group in df.groupby('Vehicle_ID'):
            initial_fuel = np.random.uniform(50, 100)
            # Decrease fuel based on cumulative distance
            cumulative_distance = group['v_Vel'].cumsum() * 0.1  # Rough estimate
            fuel_consumption = cumulative_distance * 0.001  # 0.1% per unit distance
            
            vehicle_fuel = (initial_fuel - fuel_consumption).clip(10, 100)
            fuel_levels.extend(vehicle_fuel.values)
        
        return pd.Series(fuel_levels, index=df.index)
    
    def _calculate_gps_accuracy(self, df: pd.DataFrame) -> pd.Series:
        """Calculate GPS accuracy based on vehicle dynamics"""
        # Higher accuracy for stable driving, lower for rapid maneuvers
        base_accuracy = 5.0  # meters
        dynamics_penalty = np.abs(df['v_Acc']) * 0.5  # Penalty for acceleration
        
        return (base_accuracy + dynamics_penalty).clip(2, 20)
    
    def _calculate_data_quality(self, df: pd.DataFrame) -> pd.Series:
        """Calculate data quality score"""
        # High quality if all fields present and reasonable
        base_quality = 0.95
        
        # Reduce quality for extreme values
        quality_penalty = np.zeros(len(df))
        quality_penalty[df['v_Vel'] > 50] += 0.1  # Very high speed
        quality_penalty[np.abs(df['v_Acc']) > 15] += 0.1  # Extreme acceleration
        
        return (base_quality - quality_penalty).clip(0.5, 1.0)
    
    def _generate_semantic_context(self, df: pd.DataFrame) -> pd.Series:
        """Generate semantic context as JSON string"""
        contexts = []
        for _, row in df.iterrows():
            context = {
                'lane': int(row['Lane_ID']),
                'vehicle_class': self.site_config.get('VEHICLE_CLASS_MAP', {}).get(row['Veh_Class'], 'unknown'),
                'traffic_density': self._estimate_traffic_density(df, row['Vehicle_ID'], row['Frame_ID']),
                'road_type': 'highway' if row['v_Vel'] > 30 else 'urban'
            }
            contexts.append(str(context))
        
        return pd.Series(contexts, index=df.index)
    
    def _generate_location_id(self, coords: Dict[str, pd.Series]) -> pd.Series:
        """Generate location ID from coordinates"""
        # Create hash from coordinates
        if isinstance(coords['lat'], pd.Series):
            return coords['lat'].astype(str) + '_' + coords['lon'].astype(str)
        else:
            return f"{coords['lat']:.6f}_{coords['lon']:.6f}"
    
    def _generate_provenance_id(self, df: pd.DataFrame) -> pd.Series:
        """Generate data provenance ID"""
        # Create unique ID based on source data
        provenance_ids = []
        for _, row in df.iterrows():
            data = f"{row.get('site', 'ngsim')}_{row.get('source_file', 'unknown')}_{row['Frame_ID']}_{row['Vehicle_ID']}"
            hash_id = hashlib.md5(data.encode()).hexdigest()
            provenance_ids.append(hash_id)
        
        return pd.Series(provenance_ids, index=df.index)
    
    def _estimate_traffic_density(self, df: pd.DataFrame, vehicle_id: int, frame_id: int) -> str:
        """Estimate traffic density based on vehicle spacing"""
        # Count vehicles in same frame within 100 feet
        same_frame = df[df['Frame_ID'] == frame_id]
        if len(same_frame) == 0:
            return 'low'
        
        # Simple density estimation
        vehicle_count = len(same_frame)
        if vehicle_count > 50:
            return 'high'
        elif vehicle_count > 20:
            return 'medium'
        else:
            return 'low'
    
    def _get_causal_factors(self, group: pd.DataFrame, idx: int) -> str:
        """Get causal factors for an event"""
        # Look at surrounding context
        preceding = group['Prec_Veh_ID'].iloc[idx] if 'Prec_Veh_ID' in group.columns else None
        following = group['Fol_Veh_ID'].iloc[idx] if 'Fol_Veh_ID' in group.columns else None
        spacing = group['Spacing'].iloc[idx] if 'Spacing' in group.columns else None
        headway = group['Headway'].iloc[idx] if 'Headway' in group.columns else None
        
        factors = []
        if preceding and preceding > 0:
            factors.append(f'preceding_vehicle_{preceding}')
        if following and following > 0:
            factors.append(f'following_vehicle_{following}')
        if spacing and spacing < 20:
            factors.append('close_spacing')
        if headway and headway < 1:
            factors.append('short_headway')
        
        return ', '.join(factors) if factors else 'isolated_event'
    
    def _calculate_distance(self, trip_group: pd.DataFrame) -> float:
        """Calculate total distance of a trip in km"""
        # Sum up distances between consecutive points
        total_distance = 0.0
        
        for i in range(1, len(trip_group)):
            dx = (trip_group['Local_X'].iloc[i] - trip_group['Local_X'].iloc[i-1]) * self.FEET_TO_METERS
            dy = (trip_group['Local_Y'].iloc[i] - trip_group['Local_Y'].iloc[i-1]) * self.FEET_TO_METERS
            distance = math.sqrt(dx**2 + dy**2)
            total_distance += distance
        
        return total_distance / 1000.0  # Convert to km


def main():
    """Example usage of NGSIM transformer"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Transform NGSIM data to MakFleet format')
    parser.add_argument('--input', required=True, help='Input CSV file from parser')
    parser.add_argument('--output', default='data/ngsim/processed', help='Output directory')
    parser.add_argument('--site', default='I-80', choices=['I-80', 'US-101', 'Lankershim'])
    args = parser.parse_args()
    
    # Load parsed data
    logger.info(f"Loading parsed NGSIM data from {args.input}")
    df = pd.read_csv(args.input)
    
    # Create transformer
    from ngsim_parser import NGSIMParser
    ngsim_parser = NGSIMParser(site_name=args.site)
    site_config = ngsim_parser.get_site_config()
    
    transformer = NGSIMTransformer(site_config=site_config)
    
    # Transform data
    transformed = transformer.transform(df)
    
    # Save transformed data
    os.makedirs(args.output, exist_ok=True)
    
    for name, data_df in transformed.items():
        output_file = os.path.join(args.output, f'ngsim_{name}.csv')
        data_df.to_csv(output_file, index=False)
        logger.info(f"Saved {name} to {output_file}")
    
    # Save metadata
    metadata = {
        'source': 'NGSIM',
        'site': args.site,
        'transformation_date': datetime.now().isoformat(),
        'record_counts': {name: len(df) for name, df in transformed.items()}
    }
    
    with open(os.path.join(args.output, 'transformation_metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)


if __name__ == '__main__':
    main()