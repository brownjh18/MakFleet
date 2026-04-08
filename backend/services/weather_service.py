"""
MakFleet Weather Service
Handles weather data collection, storage, and correlation with driving events.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WeatherData:
    """Weather data structure"""
    timestamp: datetime
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float
    wind_direction: str
    conditions: str
    visibility: float
    source: str = "OpenWeatherMap"


class WeatherService:
    """
    Service for weather data collection and analysis.
    Integrates with weather APIs and correlates weather with driving events.
    """
    
    def __init__(self, db_session=None, api_key: Optional[str] = None):
        """
        Initialize weather service.
        
        Args:
            db_session: Database session for storing weather data
            api_key: API key for weather service (OpenWeatherMap, etc.)
        """
        self.db_session = db_session
        self.api_key = api_key
        self._api_available = api_key is not None
        
        # Weather conditions mapping
        self.condition_mapping = {
            'clear': 'sunny',
            'sunny': 'sunny',
            'partly_cloudy': 'partly_cloudy',
            'cloudy': 'cloudy',
            'overcast': 'cloudy',
            'light_rain': 'rainy',
            'rain': 'rainy',
            'heavy_rain': 'rainy',
            'thunderstorm': 'stormy',
            'snow': 'snowy',
            'fog': 'foggy',
            'mist': 'foggy',
            'haze': 'foggy',
        }
    
    def fetch_weather_data(self, latitude: float, longitude: float) -> Optional[WeatherData]:
        """
        Fetch current weather data from API.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            WeatherData object or None if unavailable
        """
        if not self._api_available:
            logger.warning("Weather API key not configured, using simulated data")
            return self._generate_simulated_weather()
        
        try:
            # OpenWeatherMap API call (would be implemented with actual API)
            # For now, return simulated data
            return self._generate_simulated_weather()
        except Exception as e:
            logger.error(f"Failed to fetch weather data: {e}")
            return None
    
    def _generate_simulated_weather(self) -> WeatherData:
        """Generate simulated weather data for testing"""
        import random
        
        conditions_list = ['sunny', 'partly_cloudy', 'cloudy', 'rainy', 'foggy']
        
        return WeatherData(
            timestamp=datetime.utcnow(),
            temperature=random.uniform(18.0, 32.0),
            humidity=random.uniform(40.0, 95.0),
            precipitation=random.uniform(0.0, 10.0) if random.random() > 0.7 else 0.0,
            wind_speed=random.uniform(0.0, 25.0),
            wind_direction=random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            conditions=random.choice(conditions_list),
            visibility=random.uniform(5.0, 20.0),
            source="simulated"
        )
    
    def store_weather_data(self, weather: WeatherData) -> Optional[int]:
        """
        Store weather data in database.
        
        Args:
            weather: WeatherData object to store
            
        Returns:
            weather_id if successful, None otherwise
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return None
        
        try:
            from sqlalchemy import text
            
            query = text("""
                INSERT INTO weather (
                    timestamp, temperature, humidity, precipitation,
                    wind_speed, wind_direction, conditions, visibility, source
                ) VALUES (
                    :timestamp, :temperature, :humidity, :precipitation,
                    :wind_speed, :wind_direction, :conditions, :visibility, :source
                ) RETURNING weather_id
            """)
            
            result = self.db_session.execute(query, {
                'timestamp': weather.timestamp,
                'temperature': weather.temperature,
                'humidity': weather.humidity,
                'precipitation': weather.precipitation,
                'wind_speed': weather.wind_speed,
                'wind_direction': weather.wind_direction,
                'conditions': weather.conditions,
                'visibility': weather.visibility,
                'source': weather.source
            })
            
            self.db_session.commit()
            weather_id = result.scalar()
            logger.info(f"Stored weather data with id: {weather_id}")
            return weather_id
            
        except Exception as e:
            logger.error(f"Failed to store weather data: {e}")
            self.db_session.rollback()
            return None
    
    def get_weather_for_timeframe(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[WeatherData]:
        """
        Retrieve weather data for a specific timeframe.
        
        Args:
            start_time: Start of timeframe
            end_time: End of timeframe
            
        Returns:
            List of WeatherData objects
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            query = text("""
                SELECT weather_id, timestamp, temperature, humidity, precipitation,
                       wind_speed, wind_direction, conditions, visibility, source
                FROM weather
                WHERE timestamp >= :start_time AND timestamp <= :end_time
                ORDER BY timestamp DESC
            """)
            
            result = self.db_session.execute(query, {
                'start_time': start_time,
                'end_time': end_time
            })
            
            weather_list = []
            for row in result:
                weather_list.append(WeatherData(
                    timestamp=row.timestamp,
                    temperature=row.temperature,
                    humidity=row.humidity,
                    precipitation=row.precipitation,
                    wind_speed=row.wind_speed,
                    wind_direction=row.wind_direction,
                    conditions=row.conditions,
                    visibility=row.visibility,
                    source=row.source
                ))
            
            return weather_list
            
        except Exception as e:
            logger.error(f"Failed to retrieve weather data: {e}")
            return []
    
    def correlate_weather_with_events(
        self,
        start_time: datetime,
        end_time: datetime,
        time_window_hours: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Correlate weather conditions with driving events.
        
        Args:
            start_time: Start of analysis period
            end_time: End of analysis period
            time_window_hours: Time window for correlation (hours)
            
        Returns:
            List of correlation results
        """
        if self.db_session is None:
            logger.error("Database session not available")
            return []
        
        try:
            from sqlalchemy import text
            
            # Use the weather_event_correlation view
            query = text("""
                SELECT 
                    hour_bucket,
                    conditions,
                    precipitation,
                    wind_speed,
                    event_count,
                    high_severity_ratio,
                    affected_vehicles
                FROM weather_event_correlation
                WHERE hour_bucket >= :start_time AND hour_bucket <= :end_time
                ORDER BY hour_bucket DESC
            """)
            
            result = self.db_session.execute(query, {
                'start_time': start_time,
                'end_time': end_time
            })
            
            correlations = []
            for row in result:
                correlations.append({
                    'hour_bucket': row.hour_bucket.isoformat() if row.hour_bucket else None,
                    'conditions': row.conditions,
                    'precipitation': row.precipitation,
                    'wind_speed': row.wind_speed,
                    'event_count': row.event_count,
                    'high_severity_ratio': row.high_severity_ratio,
                    'affected_vehicles': row.affected_vehicles
                })
            
            return correlations
            
        except Exception as e:
            logger.error(f"Failed to correlate weather with events: {e}")
            return []
    
    def get_weather_impact_analysis(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze the impact of weather on driving safety.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with weather impact analysis
        """
        start_time = datetime.utcnow() - timedelta(days=days)
        end_time = datetime.utcnow()
        
        correlations = self.correlate_weather_with_events(start_time, end_time)
        
        if not correlations:
            return {
                'analysis_period_days': days,
                'message': 'No data available for analysis',
                'weather_event_correlation': []
            }
        
        # Calculate weather impact metrics
        weather_impact = {}
        for corr in correlations:
            conditions = corr['conditions'] or 'unknown'
            if conditions not in weather_impact:
                weather_impact[conditions] = {
                    'total_events': 0,
                    'high_severity_events': 0,
                    'occurrences': 0
                }
            
            weather_impact[conditions]['total_events'] += corr['event_count'] or 0
            weather_impact[conditions]['occurrences'] += 1
            if corr['high_severity_ratio']:
                weather_impact[conditions]['high_severity_events'] += (
                    corr['event_count'] * corr['high_severity_ratio']
                )
        
        # Calculate averages
        for conditions, data in weather_impact.items():
            if data['occurrences'] > 0:
                data['avg_events_per_occurrence'] = (
                    data['total_events'] / data['occurrences']
                )
                data['high_severity_ratio'] = (
                    data['high_severity_events'] / max(data['total_events'], 1)
                )
            else:
                data['avg_events_per_occurrence'] = 0
                data['high_severity_ratio'] = 0
        
        return {
            'analysis_period_days': days,
            'total_records': len(correlations),
            'weather_impact': weather_impact,
            'summary': self._generate_weather_summary(weather_impact)
        }
    
    def _generate_weather_summary(self, weather_impact: Dict) -> str:
        """Generate a summary of weather impact findings"""
        if not weather_impact:
            return "No weather data available for analysis."
        
        # Find weather condition with highest event rate
        highest_risk = max(
            weather_impact.items(),
            key=lambda x: x[1].get('avg_events_per_occurrence', 0)
        )
        
        return (
            f"Based on analysis, '{highest_risk[0]}' conditions are associated with "
            f"the highest average event rate ({highest_risk[1]['avg_events_per_occurrence']:.2f} "
            f"events per occurrence)."
        )
    
    def update_weather_for_all_locations(
        self,
        locations: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Update weather data for multiple locations.
        
        Args:
            locations: List of location dicts with 'latitude' and 'longitude'
            
        Returns:
            Dictionary with update results
        """
        results = {
            'updated': 0,
            'failed': 0,
            'locations': []
        }
        
        for location in locations:
            try:
                weather = self.fetch_weather_data(
                    location['latitude'],
                    location['longitude']
                )
                
                if weather:
                    weather_id = self.store_weather_data(weather)
                    if weather_id:
                        results['updated'] += 1
                        results['locations'].append({
                            'latitude': location['latitude'],
                            'longitude': location['longitude'],
                            'weather_id': weather_id,
                            'conditions': weather.conditions
                        })
                    else:
                        results['failed'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to update weather for location {location}: {e}")
                results['failed'] += 1
        
        return results


# Singleton instance for easy access
_weather_service_instance = None


def get_weather_service(db_session=None, api_key=None) -> WeatherService:
    """
    Get or create weather service instance.
    
    Args:
        db_session: Database session
        api_key: Weather API key
        
    Returns:
        WeatherService instance
    """
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService(db_session, api_key)
    return _weather_service_instance