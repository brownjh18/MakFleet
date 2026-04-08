"""
NGSIM Data Loader

Loads transformed NGSIM data into MakFleet PostgreSQL database.
Handles batch inserts, conflict resolution, and data validation.
Optimized for high-performance bulk loading with connection pooling.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import psycopg2
from psycopg2 import sql, extras, pool
import argparse
import json
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NGSIMLoader:
    """Loads transformed NGSIM data into MakFleet database with optimized bulk loading"""
    
    def __init__(self, database_url: str = None, 
                 batch_size: int = 5000,
                 use_connection_pool: bool = True,
                 pool_size: int = 3):
        """
        Initialize NGSIM loader
        
        Args:
            database_url: PostgreSQL connection string
                         If None, reads from DATABASE_URL environment variable
            batch_size: Number of records per batch insert
            use_connection_pool: Whether to use connection pooling
            pool_size: Size of connection pool
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.connection = None
        self.batch_size = batch_size
        self.use_connection_pool = use_connection_pool
        self.pool = None
        self.pool_size = pool_size
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_records': 0,
            'records_per_second': 0
        }
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            logger.info("Connected to MakFleet database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from database")
    
    def load_all(self, data_dir: str) -> Dict[str, int]:
        """
        Load all transformed NGSIM data into database
        
        Args:
            data_dir: Directory containing transformed CSV files
            
        Returns:
            Dictionary with record counts for each table
        """
        logger.info(f"Loading NGSIM data from {data_dir}")
        
        self.connect()
        
        try:
            # Load each component
            results = {}
            
            # Load vehicles first (foreign key dependencies)
            vehicles_file = os.path.join(data_dir, 'ngsim_vehicles.csv')
            if os.path.exists(vehicles_file):
                vehicles_df = pd.read_csv(vehicles_file)
                results['vehicles'] = self.load_vehicles(vehicles_df)
            
            # Load telemetry
            telemetry_file = os.path.join(data_dir, 'ngsim_telemetry.csv')
            if os.path.exists(telemetry_file):
                telemetry_df = pd.read_csv(telemetry_file)
                results['telemetry'] = self.load_telemetry(telemetry_df)
            
            # Load events
            events_file = os.path.join(data_dir, 'ngsim_events.csv')
            if os.path.exists(events_file):
                events_df = pd.read_csv(events_file)
                results['events'] = self.load_events(events_df)
            
            # Load trips
            trips_file = os.path.join(data_dir, 'ngsim_trips.csv')
            if os.path.exists(trips_file):
                trips_df = pd.read_csv(trips_file)
                results['trips'] = self.load_trips(trips_df)
            
            # Commit all changes
            self.connection.commit()
            logger.info("All NGSIM data loaded successfully")
            
            return results
            
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to load NGSIM data: {e}")
            raise
        finally:
            self.disconnect()
    
    def load_vehicles(self, df: pd.DataFrame) -> int:
        """
        Load vehicles into database
        
        Args:
            df: Vehicles DataFrame
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Loading {len(df)} vehicles")
        
        if df.empty:
            return 0
        
        # Prepare data for batch insert
        vehicle_records = []
        for _, row in df.iterrows():
            vehicle_records.append({
                'vehicle_id': int(row['vehicle_id']),
                'plate_number': str(row['plate_number']),
                'driver_id': int(row['driver_id']),
                'model': str(row['model']),
                'status': str(row.get('status', 'active')),
                'model_category': str(row.get('model_category', row['model'])),
                'created_at': datetime.now()
            })
        
        # Insert using ON CONFLICT DO UPDATE
        query = """
        INSERT INTO vehicles (vehicle_id, plate_number, driver_id, model, status, model_category, created_at)
        VALUES %s
        ON CONFLICT (vehicle_id) DO UPDATE SET
            plate_number = EXCLUDED.plate_number,
            driver_id = EXCLUDED.driver_id,
            model = EXCLUDED.model,
            status = EXCLUDED.status,
            model_category = EXCLUDED.model_category
        """
        
        with self.connection.cursor() as cursor:
            extras.execute_values(
                cursor,
                query,
                [tuple(record.values()) for record in vehicle_records],
                page_size=self.batch_size
            )
        
        logger.info(f"Loaded {len(vehicle_records)} vehicles")
        return len(vehicle_records)
    
    def load_telemetry(self, df: pd.DataFrame) -> int:
        """
        Load telemetry data into database
        
        Args:
            df: Telemetry DataFrame
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Loading {len(df)} telemetry records")
        
        if df.empty:
            return 0
        
        # Prepare data for batch insert
        telemetry_records = []
        for _, row in df.iterrows():
            telemetry_records.append({
                'vehicle_id': int(row['vehicle_id']),
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'speed': float(row['speed']),
                'acceleration': float(row['acceleration']) if pd.notna(row['acceleration']) else None,
                'engine_temp': float(row['engine_temp']) if pd.notna(row['engine_temp']) else None,
                'fuel_level': float(row['fuel_level']) if pd.notna(row['fuel_level']) else None,
                'timestamp': pd.to_datetime(row['timestamp']),
                'gps_accuracy': float(row.get('gps_accuracy', 10.0)),
                'data_quality_score': float(row.get('data_quality_score', 0.8)),
                'is_validated': bool(row.get('is_validated', True)),
                'semantic_context': str(row.get('semantic_context', '')),
                'map_matched': bool(row.get('map_matched', True)),
                'matched_location_id': str(row.get('matched_location_id', '')),
                'match_confidence': float(row.get('match_confidence', 0.95)),
                'provenance_id': str(row.get('provenance_id', ''))
            })
        
        # Insert in batches
        query = """
        INSERT INTO telemetry (vehicle_id, latitude, longitude, speed, acceleration, engine_temp, 
                               fuel_level, timestamp, gps_accuracy, data_quality_score, is_validated,
                               semantic_context, map_matched, matched_location_id, match_confidence, provenance_id)
        VALUES %s
        ON CONFLICT ON CONSTRAINT telemetry_pkey DO NOTHING
        """
        
        with self.connection.cursor() as cursor:
            # Process in batches
            for i in range(0, len(telemetry_records), self.batch_size):
                batch = telemetry_records[i:i + self.batch_size]
                extras.execute_values(
                    cursor,
                    query,
                    [tuple(record.values()) for record in batch],
                    page_size=self.batch_size
                )
                
                if (i // self.batch_size) % 10 == 0:
                    logger.info(f"  Processed {i + len(batch)}/{len(telemetry_records)} records")
        
        logger.info(f"Loaded {len(telemetry_records)} telemetry records")
        return len(telemetry_records)
    
    def load_events(self, df: pd.DataFrame) -> int:
        """
        Load events into database
        
        Args:
            df: Events DataFrame
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Loading {len(df)} events")
        
        if df.empty:
            return 0
        
        # Prepare data for batch insert
        event_records = []
        for _, row in df.iterrows():
            event_records.append({
                'vehicle_id': int(row['vehicle_id']),
                'event_type': str(row['event_type']),
                'latitude': float(row['latitude']),
                'longitude': float(row['longitude']),
                'speed': float(row['speed']) if pd.notna(row['speed']) else None,
                'acceleration': float(row['acceleration']) if pd.notna(row['acceleration']) else None,
                'timestamp': pd.to_datetime(row['timestamp']),
                'severity': str(row.get('severity', 'medium')),
                'confidence_score': float(row.get('confidence_score', 0.8)),
                'explanation': str(row.get('explanation', '')),
                'causal_factors': str(row.get('causal_factors', '')),
                'ai_detected': bool(row.get('ai_detected', False))
            })
        
        # Insert in batches
        query = """
        INSERT INTO events (vehicle_id, event_type, latitude, longitude, speed, acceleration,
                           timestamp, severity, confidence_score, explanation, causal_factors, ai_detected)
        VALUES %s
        """
        
        with self.connection.cursor() as cursor:
            for i in range(0, len(event_records), self.batch_size):
                batch = event_records[i:i + self.batch_size]
                extras.execute_values(
                    cursor,
                    query,
                    [tuple(record.values()) for record in batch],
                    page_size=self.batch_size
                )
                
                if (i // self.batch_size) % 10 == 0:
                    logger.info(f"  Processed {i + len(batch)}/{len(event_records)} records")
        
        logger.info(f"Loaded {len(event_records)} events")
        return len(event_records)
    
    def load_trips(self, df: pd.DataFrame) -> int:
        """
        Load trips into database
        
        Args:
            df: Trips DataFrame
            
        Returns:
            Number of records inserted
        """
        logger.info(f"Loading {len(df)} trips")
        
        if df.empty:
            return 0
        
        # Prepare data for batch insert
        trip_records = []
        for _, row in df.iterrows():
            trip_records.append({
                'vehicle_id': int(row['vehicle_id']),
                'driver_id': int(row['driver_id']),
                'route_id': int(row['route_id']) if pd.notna(row['route_id']) else None,
                'start_time': pd.to_datetime(row['start_time']),
                'end_time': pd.to_datetime(row['end_time']) if pd.notna(row['end_time']) else None,
                'start_location_id': int(row['start_location_id']) if pd.notna(row['start_location_id']) else None,
                'end_location_id': int(row['end_location_id']) if pd.notna(row['end_location_id']) else None,
                'distance_km': float(row['distance_km']) if pd.notna(row['distance_km']) else None,
                'duration_min': float(row['duration_min']) if pd.notna(row['duration_min']) else None,
                'avg_speed': float(row['avg_speed']) if pd.notna(row['avg_speed']) else None,
                'max_speed': float(row['max_speed']) if pd.notna(row['max_speed']) else None,
                'status': str(row.get('status', 'completed'))
            })
        
        # Insert in batches
        query = """
        INSERT INTO trips (vehicle_id, driver_id, route_id, start_time, end_time, start_location_id,
                          end_location_id, distance_km, duration_min, avg_speed, max_speed, status)
        VALUES %s
        """
        
        with self.connection.cursor() as cursor:
            for i in range(0, len(trip_records), self.batch_size):
                batch = trip_records[i:i + self.batch_size]
                extras.execute_values(
                    cursor,
                    query,
                    [tuple(record.values()) for record in batch],
                    page_size=self.batch_size
                )
                
                if (i // self.batch_size) % 10 == 0:
                    logger.info(f"  Processed {i + len(batch)}/{len(trip_records)} records")
        
        logger.info(f"Loaded {len(trip_records)} trips")
        return len(trip_records)
    
    def validate_loaded_data(self) -> Dict[str, int]:
        """
        Validate loaded data by checking record counts and data quality
        
        Returns:
            Dictionary with validation results
        """
        logger.info("Validating loaded NGSIM data")
        
        validation_results = {}
        
        with self.connection.cursor() as cursor:
            # Check telemetry count
            cursor.execute("SELECT COUNT(*) FROM telemetry WHERE provenance_id LIKE %s", ('ngsim%',))
            validation_results['telemetry_count'] = cursor.fetchone()[0]
            
            # Check events count
            cursor.execute("SELECT COUNT(*) FROM events WHERE vehicle_id >= 1000")
            validation_results['events_count'] = cursor.fetchone()[0]
            
            # Check trips count
            cursor.execute("SELECT COUNT(*) FROM trips WHERE vehicle_id >= 1000")
            validation_results['trips_count'] = cursor.fetchone()[0]
            
            # Check vehicles count
            cursor.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_id >= 1000")
            validation_results['vehicles_count'] = cursor.fetchone()[0]
            
            # Check data quality
            cursor.execute("""
                SELECT AVG(data_quality_score), AVG(gps_accuracy)
                FROM telemetry
                WHERE provenance_id LIKE %s
            """, ('ngsim%',))
            avg_quality, avg_accuracy = cursor.fetchone()
            validation_results['avg_data_quality'] = float(avg_quality) if avg_quality else 0
            validation_results['avg_gps_accuracy'] = float(avg_accuracy) if avg_accuracy else 0
            
            # Check for events detected
            cursor.execute("""
                SELECT event_type, COUNT(*)
                FROM events
                WHERE vehicle_id >= 1000
                GROUP BY event_type
            """)
            event_counts = dict(cursor.fetchall())
            validation_results['event_counts'] = event_counts
        
        logger.info(f"Validation results: {validation_results}")
        return validation_results


def main():
    """Command-line interface for NGSIM loader"""
    parser = argparse.ArgumentParser(description='Load transformed NGSIM data into MakFleet database')
    parser.add_argument('--input', required=True, help='Directory containing transformed CSV files')
    parser.add_argument('--database-url', help='PostgreSQL connection string')
    parser.add_argument('--validate', action='store_true', help='Validate loaded data')
    args = parser.parse_args()
    
    # Create loader
    loader = NGSIMLoader(database_url=args.database_url)
    
    # Load data
    results = loader.load_all(args.input)
    
    print("\n=== NGSIM Data Loading Results ===")
    for table, count in results.items():
        print(f"{table}: {count} records")
    
    # Validate if requested
    if args.validate:
        validation = loader.validate_loaded_data()
        print("\n=== Validation Results ===")
        for key, value in validation.items():
            print(f"{key}: {value}")


if __name__ == '__main__':
    main()