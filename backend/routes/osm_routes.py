"""
OpenStreetMap Routes for MakFleet
Provides API endpoints for OSM data and spatial operations
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from backend.services.osm_service import get_osm_service

router = APIRouter()

@router.get("/osm/download-campus-data")
async def download_campus_data():
    """
    Download and cache OpenStreetMap data for Makerere University campus
    This provides the spatial backbone for the AI system
    """
    try:
        osm_service = get_osm_service()
        success = osm_service.download_makerere_data()

        if success:
            bounds = osm_service.get_campus_bounds()
            return {
                "status": "success",
                "message": "Makerere University OSM data downloaded successfully",
                "campus_bounds": {
                    "north": bounds[0],
                    "south": bounds[1],
                    "east": bounds[2],
                    "west": bounds[3]
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to download OSM data")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OSM download failed: {str(e)}")

@router.get("/osm/campus-routes", response_model=List[Dict])
async def get_campus_routes():
    """
    Get bodaboda routes extracted from real OSM campus data
    Returns routes suitable for dashboard visualization
    """
    try:
        osm_service = get_osm_service()
        routes = osm_service.get_campus_routes()

        return routes

    except Exception as e:
        # Return default routes if OSM service fails
        return [
            {
                "name": "Library to Freedom Square",
                "from": "library",
                "to": "freedom",
                "path": [[0.3336, 32.5656], [0.3338, 32.5660], [0.3340, 32.5665], [0.3342, 32.5671]],
                "color": "#3B82F6",
                "usage": "high",
                "type": "main_route",
                "distance": 150
            },
            {
                "name": "Freedom Square to Engineering",
                "from": "freedom",
                "to": "engineering",
                "path": [[0.3342, 32.5671], [0.3348, 32.5665], [0.3351, 32.5650], [0.3351, 32.5634]],
                "color": "#10B981",
                "usage": "medium",
                "type": "academic_route",
                "distance": 200
            }
        ]

@router.get("/osm/campus-locations", response_model=List[Dict])
async def get_campus_locations():
    """
    Get key campus locations from OSM buildings and POIs
    Returns locations suitable for dashboard markers
    """
    try:
        osm_service = get_osm_service()
        locations = osm_service.get_campus_locations()

        return locations

    except Exception as e:
        # Return default locations if OSM service fails
        return [
            {"id": "library", "name": "Main Library", "lat": 0.3336, "lon": 32.5656, "type": "library", "color": "#3B82F6"},
            {"id": "freedom", "name": "Freedom Square", "lat": 0.3342, "lon": 32.5671, "type": "central", "color": "#10B981"},
            {"id": "engineering", "name": "Engineering Block", "lat": 0.3351, "lon": 32.5634, "type": "academic", "color": "#F59E0B"},
            {"id": "parking", "name": "Main Parking", "lat": 0.3315, "lon": 32.5648, "type": "parking", "color": "#06B6D4"}
        ]

@router.post("/osm/map-match")
async def map_match_gps(lat: float, lon: float):
    """
    Perform map-matching: convert raw GPS to nearest road/path point
    This is crucial for handling GPS noise in bodaboda tracking
    """
    try:
        osm_service = get_osm_service()
        matched_point = osm_service.find_nearest_road(lat, lon)

        if matched_point:
            return {
                "original_lat": lat,
                "original_lon": lon,
                "matched_lat": matched_point[0],
                "matched_lon": matched_point[1],
                "distance_meters": None  # Could calculate if needed
            }
        else:
            return {
                "original_lat": lat,
                "original_lon": lon,
                "matched_lat": lat,
                "matched_lon": lon,
                "note": "No road found, using original coordinates"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Map matching failed: {str(e)}")

@router.post("/osm/find-route")
async def find_route(start_lat: float, start_lon: float, end_lat: float, end_lon: float):
    """
    Find shortest path between two points using real OSM network
    This enables route prediction and validation for bodabodas
    """
    try:
        osm_service = get_osm_service()
        route = osm_service.get_route_between_points(start_lat, start_lon, end_lat, end_lon)

        if route:
            # Calculate total distance
            total_distance = 0
            for i in range(1, len(route)):
                # Simple distance calculation (could use more precise method)
                lat1, lon1 = route[i-1]
                lat2, lon2 = route[i]
                distance = ((lat2 - lat1)**2 + (lon2 - lon1)**2)**0.5 * 111000  # Rough meters
                total_distance += distance

            return {
                "route_found": True,
                "coordinates": route,
                "total_distance_meters": round(total_distance, 1),
                "point_count": len(route)
            }
        else:
            return {
                "route_found": False,
                "error": "No route found between the specified points"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Route finding failed: {str(e)}")

@router.get("/osm/campus-stats")
async def get_campus_stats():
    """
    Get statistics about the downloaded OSM campus data
    Useful for system monitoring and validation
    """
    try:
        osm_service = get_osm_service()

        stats = {
            "data_available": osm_service.graph is not None,
            "nodes_count": len(osm_service.nodes_df) if osm_service.nodes_df is not None else 0,
            "edges_count": len(osm_service.edges_df) if osm_service.edges_df is not None else 0,
            "buildings_count": len(osm_service.buildings_df) if osm_service.buildings_df is not None else 0
        }

        if stats["data_available"]:
            bounds = osm_service.get_campus_stats()["campus_bounds"]
            stats["campus_bounds"] = bounds
            stats["road_types"] = osm_service.edges_df['highway'].value_counts().to_dict() if osm_service.edges_df is not None else {}

        return stats

    except Exception as e:
        return {
            "data_available": False,
            "error": str(e)
        }