"""
MakFleet Fleet Management Routes
API routes for weather, routes, trips, driver performance, and vehicle maintenance.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Optional

# Import services
from ..services.weather_service import get_weather_service, WeatherData
from ..services.route_service import (
    get_route_service, get_trip_service,
    get_driver_performance_service, get_vehicle_maintenance_service
)

# Create blueprints
weather_bp = Blueprint('weather', __name__, url_prefix='/api/weather')
routes_bp = Blueprint('routes', __name__, url_prefix='/api/routes')
trips_bp = Blueprint('trips', __name__, url_prefix='/api/trips')
performance_bp = Blueprint('performance', __name__, url_prefix='/api/performance')
maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/api/maintenance')


# ============================================
# Weather Routes
# ============================================

@weather_bp.route('/current', methods=['GET'])
def get_current_weather():
    """Get current weather data."""
    try:
        latitude = float(request.args.get('latitude', 0.3336))
        longitude = float(request.args.get('longitude', 32.5656))
        
        weather_service = get_weather_service()
        weather = weather_service.fetch_weather_data(latitude, longitude)
        
        if weather:
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': weather.timestamp.isoformat(),
                    'temperature': weather.temperature,
                    'humidity': weather.humidity,
                    'precipitation': weather.precipitation,
                    'wind_speed': weather.wind_speed,
                    'wind_direction': weather.wind_direction,
                    'conditions': weather.conditions,
                    'visibility': weather.visibility,
                    'source': weather.source
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to fetch weather data'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@weather_bp.route('/history', methods=['GET'])
def get_weather_history():
    """Get historical weather data."""
    try:
        days = int(request.args.get('days', 7))
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        weather_service = get_weather_service()
        weather_list = weather_service.get_weather_for_timeframe(start_time, end_time)
        
        return jsonify({
            'success': True,
            'data': [{
                'timestamp': w.timestamp.isoformat(),
                'temperature': w.temperature,
                'humidity': w.humidity,
                'precipitation': w.precipitation,
                'wind_speed': w.wind_speed,
                'wind_direction': w.wind_direction,
                'conditions': w.conditions,
                'visibility': w.visibility
            } for w in weather_list],
            'count': len(weather_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@weather_bp.route('/impact-analysis', methods=['GET'])
def get_weather_impact_analysis():
    """Get weather impact analysis on driving safety."""
    try:
        days = int(request.args.get('days', 30))
        
        weather_service = get_weather_service()
        analysis = weather_service.get_weather_impact_analysis(days)
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@weather_bp.route('/update', methods=['POST'])
def update_weather():
    """Update weather data for all locations."""
    try:
        locations = request.json.get('locations', [
            {'latitude': 0.3336, 'longitude': 32.5656},  # Main Library
            {'latitude': 0.3342, 'longitude': 32.5671},  # Freedom Square
            {'latitude': 0.3351, 'longitude': 32.5634},  # Engineering Block
        ])
        
        weather_service = get_weather_service()
        result = weather_service.update_weather_for_all_locations(locations)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# Routes Management
# ============================================

@routes_bp.route('', methods=['GET'])
def get_all_routes():
    """Get all routes."""
    try:
        common_only = request.args.get('common', 'false').lower() == 'true'
        
        route_service = get_route_service()
        
        if common_only:
            routes = route_service.get_common_routes()
        else:
            # Get all routes (would need a get_all method)
            routes = route_service.get_common_routes()  # For now, return common routes
        
        return jsonify({
            'success': True,
            'data': [{
                'route_id': r.route_id,
                'name': r.name,
                'description': r.description,
                'start_location_id': r.start_location_id,
                'end_location_id': r.end_location_id,
                'distance_km': r.distance_km,
                'estimated_duration_min': r.estimated_duration_min,
                'is_common_route': r.is_common_route,
                'usage_count': r.usage_count,
                'safety_score': r.safety_score
            } for r in routes]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@routes_bp.route('/<int:route_id>', methods=['GET'])
def get_route(route_id):
    """Get route by ID."""
    try:
        route_service = get_route_service()
        route = route_service.get_route_by_id(route_id)
        
        if route:
            return jsonify({
                'success': True,
                'data': {
                    'route_id': route.route_id,
                    'name': route.name,
                    'description': route.description,
                    'start_location_id': route.start_location_id,
                    'end_location_id': route.end_location_id,
                    'distance_km': route.distance_km,
                    'estimated_duration_min': route.estimated_duration_min,
                    'is_common_route': route.is_common_route,
                    'usage_count': route.usage_count,
                    'safety_score': route.safety_score
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Route not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@routes_bp.route('/<int:route_id>/safety', methods=['GET'])
def get_route_safety(route_id):
    """Get safety analysis for a route."""
    try:
        days = int(request.args.get('days', 30))
        
        route_service = get_route_service()
        analysis = route_service.get_route_safety_analysis(route_id, days)
        
        return jsonify({
            'success': True,
            'data': analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@routes_bp.route('', methods=['POST'])
def create_route():
    """Create a new route."""
    try:
        data = request.json
        
        route_service = get_route_service()
        route = route_service.create_route(
            name=data.get('name'),
            start_location_id=data.get('start_location_id'),
            end_location_id=data.get('end_location_id'),
            description=data.get('description'),
            distance_km=data.get('distance_km'),
            estimated_duration_min=data.get('estimated_duration_min')
        )
        
        if route:
            return jsonify({
                'success': True,
                'data': {
                    'route_id': route.route_id,
                    'name': route.name,
                    'message': 'Route created successfully'
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to create route'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# Trips Management
# ============================================

@trips_bp.route('/active', methods=['GET'])
def get_active_trips():
    """Get all active trips."""
    try:
        trip_service = get_trip_service()
        trips = trip_service.get_active_trips()
        
        return jsonify({
            'success': True,
            'data': [{
                'trip_id': t.trip_id,
                'vehicle_id': t.vehicle_id,
                'driver_id': t.driver_id,
                'route_id': t.route_id,
                'start_time': t.start_time.isoformat(),
                'start_location_id': t.start_location_id,
                'status': t.status
            } for t in trips],
            'count': len(trips)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@trips_bp.route('/<int:trip_id>', methods=['GET'])
def get_trip(trip_id):
    """Get trip by ID."""
    try:
        trip_service = get_trip_service()
        trip = trip_service.get_trip_by_id(trip_id)
        
        if trip:
            return jsonify({
                'success': True,
                'data': {
                    'trip_id': trip.trip_id,
                    'vehicle_id': trip.vehicle_id,
                    'driver_id': trip.driver_id,
                    'route_id': trip.route_id,
                    'start_time': trip.start_time.isoformat(),
                    'end_time': trip.end_time.isoformat() if trip.end_time else None,
                    'start_location_id': trip.start_location_id,
                    'end_location_id': trip.end_location_id,
                    'distance_km': trip.distance_km,
                    'duration_min': trip.duration_min,
                    'avg_speed': trip.avg_speed,
                    'max_speed': trip.max_speed,
                    'status': trip.status
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Trip not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@trips_bp.route('/driver/<int:driver_id>', methods=['GET'])
def get_driver_trips(driver_id):
    """Get trips for a specific driver."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        
        trip_service = get_trip_service()
        trips = trip_service.get_trips_for_driver(driver_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': [{
                'trip_id': t.trip_id,
                'vehicle_id': t.vehicle_id,
                'route_id': t.route_id,
                'start_time': t.start_time.isoformat(),
                'end_time': t.end_time.isoformat() if t.end_time else None,
                'distance_km': t.distance_km,
                'duration_min': t.duration_min,
                'avg_speed': t.avg_speed,
                'max_speed': t.max_speed,
                'status': t.status
            } for t in trips],
            'count': len(trips)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@trips_bp.route('', methods=['POST'])
def start_trip():
    """Start a new trip."""
    try:
        data = request.json
        
        trip_service = get_trip_service()
        trip = trip_service.start_trip(
            vehicle_id=data.get('vehicle_id'),
            driver_id=data.get('driver_id'),
            start_location_id=data.get('start_location_id'),
            route_id=data.get('route_id')
        )
        
        if trip:
            return jsonify({
                'success': True,
                'data': {
                    'trip_id': trip.trip_id,
                    'vehicle_id': trip.vehicle_id,
                    'driver_id': trip.driver_id,
                    'start_time': trip.start_time.isoformat(),
                    'status': trip.status,
                    'message': 'Trip started successfully'
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start trip'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@trips_bp.route('/<int:trip_id>/end', methods=['POST'])
def end_trip(trip_id):
    """End a trip."""
    try:
        data = request.json
        
        trip_service = get_trip_service()
        trip = trip_service.end_trip(
            trip_id=trip_id,
            end_location_id=data.get('end_location_id'),
            distance_km=data.get('distance_km'),
            duration_min=data.get('duration_min'),
            avg_speed=data.get('avg_speed'),
            max_speed=data.get('max_speed')
        )
        
        if trip:
            return jsonify({
                'success': True,
                'data': {
                    'trip_id': trip.trip_id,
                    'end_time': trip.end_time.isoformat() if trip.end_time else None,
                    'distance_km': trip.distance_km,
                    'duration_min': trip.duration_min,
                    'status': trip.status,
                    'message': 'Trip ended successfully'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to end trip - trip may not exist or already completed'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# Driver Performance Routes
# ============================================

@performance_bp.route('/driver/<int:driver_id>', methods=['GET'])
def get_driver_performance(driver_id):
    """Get performance data for a driver."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        
        perf_service = get_driver_performance_service()
        
        # Get summary
        summary = perf_service.get_driver_performance_summary(driver_id)
        
        # Get history
        history = perf_service.get_driver_performance_history(driver_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': {
                'summary': summary,
                'history': [{
                    'date': p.date.isoformat(),
                    'total_trips': p.total_trips,
                    'total_distance_km': p.total_distance_km,
                    'total_duration_min': p.total_duration_min,
                    'avg_speed': p.avg_speed,
                    'max_speed': p.max_speed,
                    'harsh_braking_count': p.harsh_braking_count,
                    'overspeed_count': p.overspeed_count,
                    'rapid_acceleration_count': p.rapid_acceleration_count,
                    'risk_score': p.risk_score,
                    'safety_score': p.safety_score,
                    'efficiency_score': p.efficiency_score
                } for p in history]
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@performance_bp.route('/driver/<int:driver_id>/calculate', methods=['POST'])
def calculate_driver_performance(driver_id):
    """Calculate and store daily performance for a driver."""
    try:
        date_str = request.json.get('date')
        date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()
        
        perf_service = get_driver_performance_service()
        performance = perf_service.calculate_daily_performance(driver_id, date)
        
        if performance:
            return jsonify({
                'success': True,
                'data': {
                    'driver_id': driver_id,
                    'date': performance.date.isoformat(),
                    'risk_score': performance.risk_score,
                    'safety_score': performance.safety_score,
                    'efficiency_score': performance.efficiency_score,
                    'message': 'Performance calculated successfully'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No data available to calculate performance'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@performance_bp.route('/summary', methods=['GET'])
def get_all_drivers_performance():
    """Get performance summary for all drivers."""
    try:
        # This would need a method to get all drivers
        # For now, return empty
        return jsonify({
            'success': True,
            'data': [],
            'message': 'Use /api/performance/driver/<driver_id> for specific driver'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# Vehicle Maintenance Routes
# ============================================

@maintenance_bp.route('/upcoming', methods=['GET'])
def get_upcoming_maintenance():
    """Get upcoming maintenance tasks."""
    try:
        days = int(request.args.get('days', 30))
        
        maint_service = get_vehicle_maintenance_service()
        maintenance_list = maint_service.get_upcoming_maintenance(days)
        
        return jsonify({
            'success': True,
            'data': [{
                'maintenance_id': m.maintenance_id,
                'vehicle_id': m.vehicle_id,
                'maintenance_type': m.maintenance_type,
                'description': m.description,
                'scheduled_date': m.scheduled_date.isoformat() if m.scheduled_date else None,
                'status': m.status,
                'next_service_due': m.next_service_due.isoformat() if m.next_service_due else None
            } for m in maintenance_list],
            'count': len(maintenance_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@maintenance_bp.route('/overdue', methods=['GET'])
def get_overdue_maintenance():
    """Get overdue maintenance tasks."""
    try:
        maint_service = get_vehicle_maintenance_service()
        maintenance_list = maint_service.get_overdue_maintenance()
        
        return jsonify({
            'success': True,
            'data': [{
                'maintenance_id': m.maintenance_id,
                'vehicle_id': m.vehicle_id,
                'maintenance_type': m.maintenance_type,
                'description': m.description,
                'scheduled_date': m.scheduled_date.isoformat() if m.scheduled_date else None,
                'status': m.status
            } for m in maintenance_list],
            'count': len(maintenance_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@maintenance_bp.route('/vehicle/<int:vehicle_id>', methods=['GET'])
def get_vehicle_maintenance_history(vehicle_id):
    """Get maintenance history for a vehicle."""
    try:
        maint_service = get_vehicle_maintenance_service()
        maintenance_list = maint_service.get_vehicle_maintenance_history(vehicle_id)
        
        return jsonify({
            'success': True,
            'data': [{
                'maintenance_id': m.maintenance_id,
                'maintenance_type': m.maintenance_type,
                'description': m.description,
                'scheduled_date': m.scheduled_date.isoformat() if m.scheduled_date else None,
                'completed_date': m.completed_date.isoformat() if m.completed_date else None,
                'cost': m.cost,
                'status': m.status,
                'notes': m.notes
            } for m in maintenance_list],
            'count': len(maintenance_list)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@maintenance_bp.route('', methods=['POST'])
def schedule_maintenance():
    """Schedule maintenance for a vehicle."""
    try:
        data = request.json
        
        scheduled_date = data.get('scheduled_date')
        if scheduled_date:
            scheduled_date = datetime.fromisoformat(scheduled_date)
        
        next_service_due = data.get('next_service_due')
        if next_service_due:
            next_service_due = datetime.fromisoformat(next_service_due)
        
        maint_service = get_vehicle_maintenance_service()
        maintenance = maint_service.schedule_maintenance(
            vehicle_id=data.get('vehicle_id'),
            maintenance_type=data.get('maintenance_type'),
            scheduled_date=scheduled_date,
            description=data.get('description'),
            next_service_due=next_service_due,
            next_service_mileage=data.get('next_service_mileage'),
            service_provider=data.get('service_provider')
        )
        
        if maintenance:
            return jsonify({
                'success': True,
                'data': {
                    'maintenance_id': maintenance.maintenance_id,
                    'vehicle_id': maintenance.vehicle_id,
                    'scheduled_date': maintenance.scheduled_date.isoformat() if maintenance.scheduled_date else None,
                    'status': maintenance.status,
                    'message': 'Maintenance scheduled successfully'
                }
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to schedule maintenance'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@maintenance_bp.route('/<int:maintenance_id>/complete', methods=['POST'])
def complete_maintenance(maintenance_id):
    """Mark maintenance as completed."""
    try:
        data = request.json
        
        completed_date = data.get('completed_date')
        if completed_date:
            completed_date = datetime.fromisoformat(completed_date)
        
        maint_service = get_vehicle_maintenance_service()
        maintenance = maint_service.complete_maintenance(
            maintenance_id=maintenance_id,
            cost=data.get('cost'),
            mileage_at_service=data.get('mileage_at_service'),
            completed_date=completed_date,
            notes=data.get('notes')
        )
        
        if maintenance:
            return jsonify({
                'success': True,
                'data': {
                    'maintenance_id': maintenance.maintenance_id,
                    'completed_date': maintenance.completed_date.isoformat() if maintenance.completed_date else None,
                    'cost': maintenance.cost,
                    'status': maintenance.status,
                    'message': 'Maintenance completed successfully'
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to complete maintenance - maintenance may not exist'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@maintenance_bp.route('/update-overdue', methods=['POST'])
def update_overdue_maintenance():
    """Update maintenance status to overdue where applicable."""
    try:
        maint_service = get_vehicle_maintenance_service()
        updated_count = maint_service.update_overdue_maintenance()
        
        return jsonify({
            'success': True,
            'data': {
                'updated_count': updated_count,
                'message': f'{updated_count} maintenance records updated to overdue'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================
# Register Blueprints
# ============================================

def register_fleet_blueprints(app):
    """Register all fleet management blueprints with the Flask app."""
    app.register_blueprint(weather_bp)
    app.register_blueprint(routes_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(maintenance_bp)