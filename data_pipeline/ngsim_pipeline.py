"""
NGSIM Complete Pipeline

Orchestrates the complete NGSIM data processing pipeline:
1. Parse raw NGSIM files
2. Transform to MakFleet format
3. Load into database
4. Validate results

Usage:
    python data_pipeline/ngsim_pipeline.py --input data/ngsim/raw/I-80/ --site I-80
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import Dict, Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ngsim_parser import NGSIMParser
from ngsim_transformer import NGSIMTransformer
from ngsim_loader import NGSIMLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NGSIMPipeline:
    """Complete NGSIM data processing pipeline"""
    
    def __init__(self, site_name: str = 'I-80', database_url: str = None):
        """
        Initialize NGSIM pipeline
        
        Args:
            site_name: NGSIM site name (I-80, US-101, Lankershim)
            database_url: PostgreSQL connection string
        """
        self.site_name = site_name
        self.database_url = database_url
        
        # Initialize components
        self.parser = NGSIMParser(site_name=site_name)
        self.transformer = None  # Will be initialized after parsing
        self.loader = NGSIMLoader(database_url=database_url)
        
        # Pipeline statistics
        self.stats = {
            'site': site_name,
            'start_time': None,
            'end_time': None,
            'parsing': {},
            'transformation': {},
            'loading': {},
            'validation': {}
        }
    
    def run(self, input_path: str, output_dir: str = None, 
            skip_load: bool = False, skip_validate: bool = False) -> Dict:
        """
        Run complete NGSIM pipeline
        
        Args:
            input_path: Path to raw NGSIM data (file or directory)
            output_dir: Directory for processed data output
            skip_load: Skip database loading step
            skip_validate: Skip validation step
            
        Returns:
            Dictionary with pipeline statistics and results
        """
        self.stats['start_time'] = datetime.now().isoformat()
        logger.info(f"Starting NGSIM pipeline for site: {self.site_name}")
        logger.info(f"Input: {input_path}")
        logger.info(f"Output: {output_dir or 'data/ngsim/processed'}")
        
        # Create output directory
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      'data', 'ngsim', 'processed')
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Step 1: Parse raw NGSIM data
            logger.info("=" * 60)
            logger.info("STEP 1: Parsing NGSIM data")
            logger.info("=" * 60)
            
            parsed_df = self._parse(input_path)
            
            # Save parsed data
            parsed_file = os.path.join(output_dir, 'ngsim_raw_parsed.csv')
            parsed_df.to_csv(parsed_file, index=False)
            logger.info(f"Saved parsed data to: {parsed_file}")
            
            # Step 2: Transform to MakFleet format
            logger.info("=" * 60)
            logger.info("STEP 2: Transforming to MakFleet format")
            logger.info("=" * 60)
            
            transformed_data = self._transform(parsed_df)
            
            # Save transformed data
            for name, df in transformed_data.items():
                output_file = os.path.join(output_dir, f'ngsim_{name}.csv')
                df.to_csv(output_file, index=False)
                logger.info(f"Saved {name} to: {output_file}")
            
            # Save transformation metadata
            metadata = {
                'pipeline': 'NGSIM to MakFleet',
                'site': self.site_name,
                'timestamp': datetime.now().isoformat(),
                'record_counts': {name: len(df) for name, df in transformed_data.items()},
                'statistics': self.parser.get_statistics(parsed_df)
            }
            
            metadata_file = os.path.join(output_dir, 'pipeline_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved metadata to: {metadata_file}")
            
            # Step 3: Load into database
            if not skip_load:
                logger.info("=" * 60)
                logger.info("STEP 3: Loading into database")
                logger.info("=" * 60)
                
                load_results = self._load(output_dir)
                self.stats['loading'] = load_results
            else:
                logger.info("Skipping database loading (skip_load=True)")
            
            # Step 4: Validate
            if not skip_validate and not skip_load:
                logger.info("=" * 60)
                logger.info("STEP 4: Validating loaded data")
                logger.info("=" * 60)
                
                validation_results = self._validate()
                self.stats['validation'] = validation_results
            
            self.stats['end_time'] = datetime.now().isoformat()
            logger.info("=" * 60)
            logger.info("Pipeline completed successfully!")
            logger.info("=" * 60)
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.stats['end_time'] = datetime.now().isoformat()
            self.stats['error'] = str(e)
            raise
    
    def _parse(self, input_path: str):
        """Parse raw NGSIM data"""
        if os.path.isfile(input_path):
            df = self.parser.parse_file(input_path)
        else:
            df = self.parser.parse_directory(input_path)
        
        # Validate
        valid_df, invalid_df = self.parser.validate_data(df)
        
        # Get statistics
        stats = self.parser.get_statistics(valid_df)
        
        self.stats['parsing'] = {
            'total_records': len(df),
            'valid_records': len(valid_df),
            'invalid_records': len(invalid_df),
            'statistics': stats
        }
        
        logger.info(f"Parsed {len(valid_df)} valid records from {len(df)} total")
        
        return valid_df
    
    def _transform(self, df):
        """Transform parsed data to MakFleet format"""
        site_config = self.parser.get_site_config()
        self.transformer = NGSIMTransformer(site_config=site_config)
        
        transformed = self.transformer.transform(df)
        
        self.stats['transformation'] = {
            'telemetry_records': len(transformed['telemetry']),
            'vehicles': len(transformed['vehicles']),
            'events': len(transformed['events']),
            'trips': len(transformed['trips'])
        }
        
        logger.info(f"Transformed data: {self.stats['transformation']}")
        
        return transformed
    
    def _load(self, output_dir: str) -> Dict:
        """Load transformed data into database"""
        results = self.loader.load_all(output_dir)
        
        logger.info(f"Loaded data: {results}")
        
        return results
    
    def _validate(self) -> Dict:
        """Validate loaded data"""
        return self.loader.validate_loaded_data()
    
    def print_summary(self):
        """Print pipeline summary"""
        print("\n" + "=" * 60)
        print("NGSIM Pipeline Summary")
        print("=" * 60)
        print(f"Site: {self.stats['site']}")
        print(f"Start: {self.stats['start_time']}")
        print(f"End: {self.stats['end_time']}")
        
        if 'parsing' in self.stats:
            print("\nParsing:")
            print(f"  Total records: {self.stats['parsing']['total_records']}")
            print(f"  Valid records: {self.stats['parsing']['valid_records']}")
            print(f"  Invalid records: {self.stats['parsing']['invalid_records']}")
        
        if 'transformation' in self.stats:
            print("\nTransformation:")
            for key, value in self.stats['transformation'].items():
                print(f"  {key}: {value}")
        
        if 'loading' in self.stats:
            print("\nLoading:")
            for table, count in self.stats['loading'].items():
                print(f"  {table}: {count} records")
        
        if 'validation' in self.stats:
            print("\nValidation:")
            for key, value in self.stats['validation'].items():
                print(f"  {key}: {value}")
        
        print("=" * 60)


def main():
    """Command-line interface for NGSIM pipeline"""
    parser = argparse.ArgumentParser(
        description='NGSIM to MakFleet Data Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process I-80 data
  python ngsim_pipeline.py --input data/ngsim/raw/I-80/ --site I-80
  
  # Process US-101 data with custom output
  python ngsim_pipeline.py --input data/ngsim/raw/US-101/ --site US-101 --output data/ngsim/processed/us101
  
  # Parse only (skip database loading)
  python ngsim_pipeline.py --input data/ngsim/raw/I-80/ --site I-80 --skip-load
        """
    )
    
    parser.add_argument('--input', required=True, 
                       help='Input path to raw NGSIM data (file or directory)')
    parser.add_argument('--site', default='I-80', choices=['I-80', 'US-101', 'Lankershim'],
                       help='NGSIM site name (default: I-80)')
    parser.add_argument('--output', default=None,
                       help='Output directory for processed data')
    parser.add_argument('--database-url', default=None,
                       help='PostgreSQL connection string (default: DATABASE_URL env var)')
    parser.add_argument('--skip-load', action='store_true',
                       help='Skip database loading step')
    parser.add_argument('--skip-validate', action='store_true',
                       help='Skip validation step')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and run pipeline
    pipeline = NGSIMPipeline(
        site_name=args.site,
        database_url=args.database_url
    )
    
    try:
        results = pipeline.run(
            input_path=args.input,
            output_dir=args.output,
            skip_load=args.skip_load,
            skip_validate=args.skip_validate
        )
        
        pipeline.print_summary()
        
        # Save summary to file
        if args.output:
            summary_file = os.path.join(args.output, 'pipeline_summary.json')
            with open(summary_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nPipeline summary saved to: {summary_file}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())