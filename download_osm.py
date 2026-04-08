#!/usr/bin/env python3
"""
Script to download OpenStreetMap data for Makerere University campus
This provides the spatial backbone for the MakFleet AI system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.services.osm_service import get_osm_service

def main():
    print("Starting OSM data download for Makerere University campus...")

    try:
        osm_service = get_osm_service()
        success = osm_service.download_makerere_data()

        if success:
            print("✅ OSM data downloaded successfully!")
            print(f"📊 Downloaded {len(osm_service.nodes_df)} nodes, {len(osm_service.edges_df)} edges")
            print(f"🏢 Found {len(osm_service.buildings_df)} buildings")

            # Get bounds
            bounds = osm_service.get_campus_bounds()
            print(".4f")

            # Get some stats
            routes = osm_service.get_campus_routes()
            locations = osm_service.get_campus_locations()
            print(f"🛣️  Extracted {len(routes)} campus routes")
            print(f"📍 Found {len(locations)} key locations")

        else:
            print("❌ Failed to download OSM data")
            return 1

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1

    print("🎉 OSM integration complete! The spatial graph is ready for AI processing.")
    return 0

if __name__ == "__main__":
    exit(main())