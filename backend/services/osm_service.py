"""
OpenStreetMap Service for MakFleet
Provides spatial backbone using real Makerere University campus data
"""

# Try to import optional dependencies for serverless deployment
try:
    import osmnx as ox
    import networkx as nx
    import geopandas as gpd
    import numpy as np
    OSM_AVAILABLE = True
except ImportError:
    ox = None
    nx = None
    gpd = None
    np = None
    OSM_AVAILABLE = False

from typing import Dict, List, Tuple, Optional
import json
import os
from pathlib import Path
import pickle
import logging

# pandas is needed for basic operations, try to import
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    PANDAS_AVAILABLE = False

logger = logging.getLogger(__name__)

class OSMService:
    """
    Service for downloading and processing OpenStreetMap data for Makerere University
    Provides the spatial graph backbone for the AI system
    """

    def __init__(self, cache_dir: str = "data/osm_cache"):
        self.cache_dir = Path(cache_dir)
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Read-only file system (e.g., Vercel serverless)
            logger.warning(f"Cannot create cache directory {cache_dir} - running in read-only mode")
            self.cache_dir = None

        self.graph = None
        self.nodes_df = None
        self.edges_df = None
        self.buildings_df = None

        if not OSM_AVAILABLE:
            logger.warning("OSMnx module not available - OSM features disabled")
            return

        # Configure OSMnx
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(self.cache_dir / "osmnx_cache")

    def download_makerere_data(self) -> bool:
        """
        Download OpenStreetMap data for Makerere University campus
        Returns True if successful
        """
        try:
            logger.info("Downloading Makerere University OSM data...")

            # Define the place name for Makerere University
            place_name = "Makerere University, Kampala, Uganda"

            # Download the street network (roads, paths, walkways)
            # Use 'all' network_type to include walkways and paths for bodabodas
            self.graph = ox.graph_from_place(
                place_name,
                network_type='all',  # Includes walkways, paths, service roads
                simplify=True,
                retain_all=False
            )

            # Download buildings data
            self.buildings_df = ox.features_from_place(
                place_name,
                tags={'building': True}
            )

            # Convert graph to GeoDataFrames
            self.nodes_df, self.edges_df = ox.graph_to_gdfs(self.graph)

            # Cache the data
            self._save_cache()

            logger.info(f"Successfully downloaded {len(self.nodes_df)} nodes, {len(self.edges_df)} edges, and {len(self.buildings_df)} buildings")
            return True

        except Exception as e:
            logger.error(f"Failed to download OSM data: {str(e)}")
            # Try to load from cache if download fails
            return self._load_cache()

    def get_campus_bounds(self) -> Tuple[float, float, float, float]:
        """
        Get the bounding box of Makerere University campus
        Returns (north, south, east, west)
        """
        if self.nodes_df is None:
            return (0.3420, 0.3300, 32.5720, 32.5600)  # Default bounds

        bounds = self.nodes_df.total_bounds
        return (bounds[3], bounds[1], bounds[2], bounds[0])  # north, south, east, west

    def get_campus_routes(self) -> List[Dict]:
        """
        Extract common bodaboda routes from OSM data
        Returns list of route dictionaries with coordinates and metadata
        """
        routes = []

        if self.edges_df is None:
            # Return default routes if no OSM data
            return self._get_default_routes()

        # Filter edges by highway type (roads, paths, etc.)
        road_types = ['primary', 'secondary', 'tertiary', 'residential', 'unclassified',
                     'path', 'footway', 'pedestrian', 'track', 'service']

        campus_edges = self.edges_df[self.edges_df['highway'].isin(road_types)]

        # Group edges by connectivity to find route segments
        route_segments = self._extract_route_segments(campus_edges)

        # Convert to route format expected by dashboard
        for i, segment in enumerate(route_segments[:10]):  # Limit to top 10 routes
            route_data = {
                'name': f'Campus Route {i+1}',
                'from': f'Point {segment["start_node"]}',
                'to': f'Point {segment["end_node"]}',
                'path': segment['coordinates'],
                'color': self._get_route_color(segment.get('highway', 'unknown')),
                'usage': segment.get('usage', 'medium'),
                'type': segment.get('highway', 'road'),
                'distance': segment.get('length', 0)
            }
            routes.append(route_data)

        return routes

    def get_campus_locations(self) -> List[Dict]:
        """
        Extract key campus locations from OSM buildings and POIs
        Returns list of location dictionaries
        """
        locations = []

        if self.buildings_df is None:
            # Return default locations if no OSM data
            return self._get_default_locations()

        # Process buildings to extract key locations
        for idx, building in self.buildings_df.iterrows():
            if building.geometry and not building.geometry.is_empty:
                centroid = building.geometry.centroid

                location = {
                    'id': f'building_{idx}',
                    'name': building.get('name', f'Building {idx}'),
                    'lat': centroid.y,
                    'lon': centroid.x,
                    'type': building.get('building', 'building'),
                    'color': self._get_location_color(building.get('building', 'unknown'))
                }
                locations.append(location)

        # Add key campus POIs if available
        poi_locations = self._get_key_pois()
        locations.extend(poi_locations)

        return locations[:20]  # Limit to 20 locations

    def find_nearest_road(self, lat: float, lon: float) -> Optional[Tuple[float, float]]:
        """
        Find the nearest road/path point to given GPS coordinates
        This implements map-matching for GPS noise reduction
        """
        if self.graph is None:
            return None

        try:
            # Find nearest node in the graph
            nearest_node = ox.distance.nearest_nodes(self.graph, lon, lat)
            node_data = self.graph.nodes[nearest_node]

            return (node_data['y'], node_data['x'])  # lat, lon

        except Exception as e:
            logger.warning(f"Could not find nearest road for ({lat}, {lon}): {str(e)}")
            return None

    def get_route_between_points(self, start_lat: float, start_lon: float,
                               end_lat: float, end_lon: float) -> Optional[List[Tuple[float, float]]]:
        """
        Find shortest path between two points using OSM network
        Returns list of (lat, lon) coordinates
        """
        if self.graph is None:
            return None

        try:
            # Find nearest nodes
            start_node = ox.distance.nearest_nodes(self.graph, start_lon, start_lat)
            end_node = ox.distance.nearest_nodes(self.graph, end_lon, end_lat)

            # Find shortest path
            route = nx.shortest_path(self.graph, start_node, end_node, weight='length')

            # Extract coordinates
            coordinates = []
            for node_id in route:
                node_data = self.graph.nodes[node_id]
                coordinates.append((node_data['y'], node_data['x']))  # lat, lon

            return coordinates

        except Exception as e:
            logger.warning(f"Could not find route between points: {str(e)}")
            return None

    def _extract_route_segments(self, edges_df) -> List[Dict]:
        """Extract route segments from edges DataFrame"""
        segments = []

        for idx, edge in edges_df.iterrows():
            try:
                # Extract geometry coordinates
                if hasattr(edge.geometry, 'coords'):
                    coords = list(edge.geometry.coords)
                    coordinates = [[lat, lon] for lon, lat in coords]  # Convert to [lat, lon]

                    segment = {
                        'start_node': idx[0] if isinstance(idx, tuple) else idx,
                        'end_node': idx[1] if isinstance(idx, tuple) else idx,
                        'coordinates': coordinates,
                        'highway': edge.get('highway', 'unknown'),
                        'length': edge.get('length', 0),
                        'usage': self._estimate_usage(edge)
                    }
                    segments.append(segment)
            except Exception as e:
                continue

        # Sort by estimated usage (high usage first)
        segments.sort(key=lambda x: x.get('usage_priority', 0), reverse=True)
        return segments

    def _estimate_usage(self, edge) -> str:
        """Estimate route usage based on edge properties"""
        highway = edge.get('highway', '')

        if isinstance(highway, list):
            highway = highway[0] if highway else ''

        # Primary roads get high usage
        if highway in ['primary', 'secondary']:
            return 'high'
        elif highway in ['tertiary', 'residential']:
            return 'medium'
        elif highway in ['path', 'footway', 'track']:
            return 'low'
        else:
            return 'medium'

    def _get_route_color(self, highway_type: str) -> str:
        """Get color for route visualization"""
        color_map = {
            'primary': '#EF4444',      # Red
            'secondary': '#F59E0B',    # Yellow
            'tertiary': '#10B981',     # Green
            'residential': '#3B82F6',  # Blue
            'path': '#8B5CF6',         # Purple
            'footway': '#06B6D4',      # Cyan
            'pedestrian': '#EC4899',   # Pink
            'track': '#84CC16',        # Lime
            'service': '#6B7280'       # Gray
        }
        return color_map.get(highway_type, '#6B7280')

    def _get_location_color(self, building_type: str) -> str:
        """Get color for location markers"""
        color_map = {
            'university': '#3B82F6',    # Blue
            'school': '#10B981',        # Green
            'residential': '#EF4444',    # Red
            'commercial': '#F59E0B',    # Yellow
            'library': '#8B5CF6',       # Purple
            'hospital': '#EC4899',      # Pink
            'church': '#06B6D4',        # Cyan
            'office': '#84CC16'         # Lime
        }
        return color_map.get(building_type, '#6B7280')

    def _get_key_pois(self) -> List[Dict]:
        """Get key points of interest for Makerere campus"""
        pois = [
            {
                'id': 'main_gate',
                'name': 'Main Gate',
                'lat': 0.3340,
                'lon': 32.5670,
                'type': 'entrance',
                'color': '#EF4444'
            },
            {
                'id': 'freedom_square',
                'name': 'Freedom Square',
                'lat': 0.3342,
                'lon': 32.5671,
                'type': 'central',
                'color': '#10B981'
            },
            {
                'id': 'main_library',
                'name': 'Main Library',
                'lat': 0.3336,
                'lon': 32.5656,
                'type': 'library',
                'color': '#8B5CF6'
            },
            {
                'id': 'engineering_block',
                'name': 'Engineering Block',
                'lat': 0.3351,
                'lon': 32.5634,
                'type': 'academic',
                'color': '#3B82F6'
            }
        ]
        return pois

    def _get_default_routes(self) -> List[Dict]:
        """Return default campus routes when OSM data is not available"""
        return [
            {
                'name': 'Library to Freedom Square',
                'from': 'library',
                'to': 'freedom',
                'path': [[0.3336, 32.5656], [0.3338, 32.5660], [0.3340, 32.5665], [0.3342, 32.5671]],
                'color': '#3B82F6',
                'usage': 'high',
                'type': 'main_route',
                'distance': 150
            },
            {
                'name': 'Freedom Square to Engineering',
                'from': 'freedom',
                'to': 'engineering',
                'path': [[0.3342, 32.5671], [0.3348, 32.5665], [0.3351, 32.5650], [0.3351, 32.5634]],
                'color': '#10B981',
                'usage': 'medium',
                'type': 'academic_route',
                'distance': 200
            }
        ]

    def _get_default_locations(self) -> List[Dict]:
        """Return default campus locations when OSM data is not available"""
        return [
            {'id': 'library', 'name': 'Main Library', 'lat': 0.3336, 'lon': 32.5656, 'type': 'library', 'color': '#3B82F6'},
            {'id': 'freedom', 'name': 'Freedom Square', 'lat': 0.3342, 'lon': 32.5671, 'type': 'central', 'color': '#10B981'},
            {'id': 'engineering', 'name': 'Engineering Block', 'lat': 0.3351, 'lon': 32.5634, 'type': 'academic', 'color': '#F59E0B'},
            {'id': 'parking', 'name': 'Main Parking', 'lat': 0.3315, 'lon': 32.5648, 'type': 'parking', 'color': '#06B6D4'}
        ]

    def _save_cache(self):
        """Save downloaded data to cache"""
        try:
            cache_data = {
                'graph': self.graph,
                'nodes_df': self.nodes_df,
                'edges_df': self.edges_df,
                'buildings_df': self.buildings_df
            }

            cache_file = self.cache_dir / 'makerere_osm_data.pkl'
            with open(cache_file, 'wb') as f:
                pickle.dump(cache_data, f)

            logger.info(f"OSM data cached to {cache_file}")

        except Exception as e:
            logger.warning(f"Failed to cache OSM data: {str(e)}")

    def _load_cache(self) -> bool:
        """Load data from cache if available"""
        try:
            cache_file = self.cache_dir / 'makerere_osm_data.pkl'
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    cache_data = pickle.load(f)

                self.graph = cache_data.get('graph')
                self.nodes_df = cache_data.get('nodes_df')
                self.edges_df = cache_data.get('edges_df')
                self.buildings_df = cache_data.get('buildings_df')

                logger.info("Loaded OSM data from cache")
                return True
            else:
                logger.warning("No cache file found")
                return False

        except Exception as e:
            logger.error(f"Failed to load OSM cache: {str(e)}")
            return False

# Global service instance
osm_service = OSMService()

def get_osm_service() -> OSMService:
    """Get the global OSM service instance"""
    return osm_service