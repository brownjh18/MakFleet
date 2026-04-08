"""
MakFleet Prototype - IoT Data Simulator
Simulates bodaboda telemetry data (GPS + sensors)

This script simulates GPS trackers and sensors sending data to the backend API.
It creates realistic movement patterns along Kampala roads, specifically around
Makerere University and surrounding areas.
"""
import requests
import random
import time
import math
from datetime import datetime
from typing import List, Tuple, Optional


# Configuration
API_URL = "http://localhost:8000"
SIMULATION_INTERVAL = 2  # seconds between readings

# Kampala center coordinates
KAMPALA_CENTER_LAT = 0.3476
KAMPALA_CENTER_LNG = 32.5825

# Makerere University area bounds
LAT_MIN = 0.3310
LAT_MAX = 0.3600
LNG_MIN = 32.5650
LNG_MAX = 32.6000

# Event thresholds
HARSH_BRAKING_PROBABILITY = 0.05  # 5% chance
OVERSPEED_PROBABILITY = 0.10  # 10% chance
RAPID_ACCEL_PROBABILITY = 0.08  # 8% chance


# Predefined road routes in Kampala (list of [lat, lng] points)
# Each route represents a major road or path
KAMPALA_ROUTES = {
    # Makerere University area routes
    "makerere_main": [
        [0.3336, 32.5671],  # Makerere Main Gate
        [0.3350, 32.5680],
        [0.3365, 32.5690],
        [0.3380, 32.5700],
        [0.3395, 32.5710],  # Makerere Hill
        [0.3410, 32.5720],
        [0.3425, 32.5730],  # New Hall
        [0.3440, 32.5740],  # Library
    ],
    "makerere_to_kikoni": [
        [0.3336, 32.5671],  # Makerere Main Gate
        [0.3350, 32.5650],
        [0.3365, 32.5630],
        [0.3380, 32.5610],
        [0.3395, 32.5590],  # Kikoni
    ],
    "gayaza_road": [
        [0.3336, 32.5671],  # Makerere
        [0.3350, 32.5700],
        [0.3370, 32.5730],
        [0.3390, 32.5760],
        [0.3410, 32.5790],  # Wandegeya
        [0.3430, 32.5820],
        [0.3450, 32.5850],  # Nakasero
    ],
    "bombo_road": [
        [0.3336, 32.5671],  # Makerere
        [0.3350, 32.5690],
        [0.3370, 32.5710],
        [0.3390, 32.5730],
        [0.3410, 32.5750],
        [0.3430, 32.5770],  # Kawempe
        [0.3450, 32.5790],
    ],
    "ng_road": [
        [0.3476, 32.5825],  # City Center
        [0.3460, 32.5810],
        [0.3445, 32.5795],
        [0.3430, 32.5780],
        [0.3415, 32.5765],
        [0.3400, 32.5750],  # Kabalagala
    ],
    "port_bell_road": [
        [0.3476, 32.5825],  # City Center
        [0.3485, 32.5800],
        [0.3495, 32.5780],
        [0.3505, 32.5760],  # Port Bell
    ],
    "entebbe_road": [
        [0.3476, 32.5825],  # City Center
        [0.3500, 32.5850],
        [0.3525, 32.5880],
        [0.3550, 32.5910],
        [0.3575, 32.5940],  # Entebbe Airport area
    ],
    "kubika_road": [
        [0.3336, 32.5671],  # Makerere
        [0.3345, 32.5685],
        [0.3355, 32.5700],
        [0.3365, 32.5715],
        [0.3375, 32.5730],  # Kubika
    ],
    "kyebando": [
        [0.3395, 32.5710],  # Makerere Hill
        [0.3410, 32.5730],
        [0.3425, 32.5750],
        [0.3440, 32.5770],
        [0.3455, 32.5790],  # Kyebando
    ],
    "nties": [
        [0.3336, 32.5671],  # Makerere
        [0.3345, 32.5690],
        [0.3355, 32.5710],
        [0.3365, 32.5730],
        [0.3375, 32.5750],
        [0.3385, 32.5770],  # NTIs
    ],
}

# Create a network of connected routes for realistic routing
ROUTE_CONNECTIONS = {
    "makerere_main": ["makerere_to_kikoni", "gayaza_road", "bombo_road", "kubika_road"],
    "makerere_to_kikoni": ["makerere_main"],
    "gayaza_road": ["makerere_main", "ng_road"],
    "bombo_road": ["makerere_main", "kyebando"],
    "ng_road": ["gayaza_road", "port_bell_road", "entebbe_road"],
    "port_bell_road": ["ng_road"],
    "entebbe_road": ["ng_road"],
    "kubika_road": ["makerere_main", "nties"],
    "kyebando": ["bombo_road", "nties"],
    "nties": ["kubika_road", "kyebando"],
}

# All routes as a list for random selection
ALL_ROUTE_NAMES = list(KAMPALA_ROUTES.keys())


def get_vehicles_from_api() -> List[dict]:
    """Fetch vehicles from the API"""
    try:
        response = requests.get(f"{API_URL}/api/vehicles/", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching vehicles: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to API: {e}")
        return []


def get_point_on_route(route_name: str, progress: float) -> Tuple[float, float]:
    """Get a point along a route based on progress (0.0 to 1.0)"""
    route = KAMPALA_ROUTES[route_name]
    if len(route) == 1:
        return route[0]
    
    # Scale progress to route indices
    scaled_progress = progress * (len(route) - 1)
    index = int(scaled_progress)
    fraction = scaled_progress - index
    
    if index >= len(route) - 1:
        return route[-1]
    
    # Interpolate between points
    lat = route[index][0] + (route[index + 1][0] - route[index][0]) * fraction
    lng = route[index][1] + (route[index + 1][1] - route[index][1]) * fraction
    
    return lat, lng


def interpolate_points(route_name: str, num_points: int = 50) -> List[Tuple[float, float]]:
    """Get interpolated points along a route for smooth movement"""
    return [get_point_on_route(route_name, i / num_points) for i in range(num_points + 1)]


class BodabodaSimulator:
    """Simulates bodaboda movement along Kampala roads"""
    
    def __init__(self, vehicle_id: int, start_lat: float, start_lng: float, plate_number: str = ""):
        self.vehicle_id = vehicle_id
        self.plate_number = plate_number
        
        # Start at given position
        self.latitude = start_lat
        self.longitude = start_lng
        self.speed = 0.0
        self.acceleration = 0.0
        self.engine_temp = 85.0  # Normal operating temperature
        self.fuel_level = random.uniform(60, 95)  # Start with 60-95% fuel
        
        # Route-based movement
        self.current_route = random.choice(ALL_ROUTE_NAMES)
        self.route_progress = 0.0  # 0.0 to 1.0
        self.route_direction = 1  # 1 = forward, -1 = backward
        self.is_moving = True  # Start moving immediately
        
        # Pre-calculate route points
        self.route_points = interpolate_points(self.current_route, 100)
        
        # Get starting position on route
        start_point = self.route_points[0]
        self.latitude = start_point[0]
        self.longitude = start_point[1]
    
    def pick_new_route(self):
        """Pick a new connected route"""
        # Get connected routes
        connected = ROUTE_CONNECTIONS.get(self.current_route, [])
        
        if connected and random.random() < 0.7:
            # 70% chance to go to connected route
            self.current_route = random.choice(connected)
        else:
            # 30% chance to pick any random route
            self.current_route = random.choice(ALL_ROUTE_NAMES)
        
        # Reset route progress based on direction
        if self.route_direction == 1:
            self.route_progress = 0.0
        else:
            self.route_progress = 1.0
        
        # Pre-calculate new route points
        self.route_points = interpolate_points(self.current_route, 100)
    
    def update_position(self) -> Tuple[float, float]:
        """Update position based on route-based movement"""
        
        if self.is_moving:
            # Move along the route
            # Speed factor determines how fast we move along the route
            speed_factor = 0.008  # Adjust for realistic movement speed
            self.route_progress += speed_factor * self.route_direction
            
            # Check if we've reached the end of the route
            if self.route_progress >= 1.0:
                self.route_progress = 1.0
                # 80% chance to reverse direction, 20% to pick new route
                if random.random() < 0.8:
                    self.route_direction = -1
                    self.route_progress = 1.0
                else:
                    self.pick_new_route()
                    self.route_direction = 1
            elif self.route_progress <= 0.0:
                self.route_progress = 0.0
                # 80% chance to reverse direction, 20% to pick new route
                if random.random() < 0.8:
                    self.route_direction = 1
                    self.route_progress = 0.0
                else:
                    self.pick_new_route()
                    self.route_direction = -1
            
            # Get position from route
            index = int(self.route_progress * 100)
            index = min(index, len(self.route_points) - 1)
            self.latitude, self.longitude = self.route_points[index]
        
        return self.latitude, self.longitude
    
    def update_speed(self) -> float:
        """Update speed based on movement and events"""
        
        if not self.is_moving:
            # Slow down to stop
            self.speed = max(0, self.speed - random.uniform(0, 2))
            self.acceleration = -random.uniform(0, 1)
        else:
            # Randomly adjust speed
            speed_change = random.uniform(-3, 4)
            
            # Apply event probabilities
            if random.random() < HARSH_BRAKING_PROBABILITY:
                # Simulate harsh braking
                speed_change = -random.uniform(5, 8)
                self.acceleration = -random.uniform(4, 7)
            elif random.random() < OVERSPEED_PROBABILITY:
                # Simulate overspeeding
                speed_change = random.uniform(3, 6)
            elif random.random() < RAPID_ACCEL_PROBABILITY:
                # Simulate rapid acceleration
                speed_change = random.uniform(4, 7)
            else:
                self.acceleration = speed_change * 0.5
            
            # Update speed
            self.speed = max(0, min(80, self.speed + speed_change))
        
        return self.speed
    
    def update_engine_temp(self) -> float:
        """Simulate engine temperature changes"""
        
        if self.speed > 40:
            # High speed - engine heats up
            self.engine_temp += random.uniform(0, 1)
        elif self.speed > 20:
            # Medium speed - stable temperature
            self.engine_temp += random.uniform(-0.5, 0.5)
        else:
            # Low speed - engine cools down
            self.engine_temp -= random.uniform(0, 1)
        
        # Clamp temperature
        self.engine_temp = max(70, min(110, self.engine_temp))
        
        return self.engine_temp
    
    def update_fuel_level(self) -> float:
        """Simulate fuel consumption based on speed and acceleration"""
        
        # Fuel consumption rates (percentage per update)
        if self.speed == 0:
            # Idling - minimal consumption
            consumption = 0.02
        elif self.speed < 20:
            # Low speed
            consumption = 0.05
        elif self.speed < 50:
            # Medium speed - normal consumption
            consumption = 0.08
        else:
            # High speed - higher consumption
            consumption = 0.12
        
        # Add extra consumption for rapid acceleration
        if self.acceleration > 3:
            consumption += 0.05
        
        # Reduce fuel level
        self.fuel_level = max(5, self.fuel_level - consumption)
        
        return self.fuel_level
    
    def get_telemetry_data(self) -> dict:
        """Generate telemetry data packet with real timestamp"""
        
        # Update all values
        self.update_position()
        speed = self.update_speed()
        engine_temp = self.update_engine_temp()
        fuel_level = self.update_fuel_level()
        
        # Use real current timestamp
        current_time = datetime.now()
        
        return {
            "vehicle_id": self.vehicle_id,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "speed": round(speed, 1),
            "acceleration": round(self.acceleration, 2),
            "engine_temp": round(engine_temp, 1),
            "fuel_level": round(fuel_level, 1),
            "timestamp": current_time.isoformat()
        }


def send_telemetry(data: dict) -> bool:
    """Send telemetry data to API"""
    try:
        response = requests.post(f"{API_URL}/api/telemetry", json=data, timeout=5)
        return response.status_code == 201
    except requests.exceptions.RequestException as e:
        print(f"Error sending data: {e}")
        return False


def simulate_vehicles(num_vehicles: int = None):
    """Main simulation loop - fetches vehicles from API if num_vehicles not specified"""
    
    print(f"Starting IoT Simulator with Kampala Road Routes...")
    print(f"API URL: {API_URL}")
    print(f"Available routes: {', '.join(ALL_ROUTE_NAMES)}")
    print("-" * 50)
    
    # Fetch vehicles from API
    vehicles = get_vehicles_from_api()
    
    if not vehicles:
        print("No vehicles found in database. Please seed the database first.")
        print("Run: python seed_data.py")
        return
    
    print(f"Found {len(vehicles)} vehicles in database")
    
    # Create simulators for each vehicle from API
    simulators = []
    for i, vehicle in enumerate(vehicles):
        # Start at different points on different routes
        start_route = ALL_ROUTE_NAMES[i % len(ALL_ROUTE_NAMES)]
        start_point = get_point_on_route(start_route, random.uniform(0, 1))
        
        sim = BodabodaSimulator(
            vehicle_id=vehicle.get("vehicle_id"),
            start_lat=start_point[0],
            start_lng=start_point[1],
            plate_number=vehicle.get("plate_number", "")
        )
        sim.current_route = start_route
        sim.route_points = interpolate_points(start_route, 100)
        simulators.append(sim)
        
        print(f"  - Vehicle {vehicle.get('vehicle_id')}: {vehicle.get('plate_number')} ({vehicle.get('model')})")
        print(f"    Starting at: {start_route}")
    
    print("-" * 50)
    
    iteration = 0
    while True:
        iteration += 1
        
        # Refresh vehicles from API periodically (every 50 iterations)
        if iteration % 50 == 0:
            vehicles = get_vehicles_from_api()
            if vehicles and len(vehicles) != len(simulators):
                print(f"Vehicle count changed, refreshing simulators...")
                simulators = []
                for i, vehicle in enumerate(vehicles):
                    start_route = ALL_ROUTE_NAMES[i % len(ALL_ROUTE_NAMES)]
                    start_point = get_point_on_route(start_route, random.uniform(0, 1))
                    sim = BodabodaSimulator(
                        vehicle_id=vehicle.get("vehicle_id"),
                        start_lat=start_point[0],
                        start_lng=start_point[1],
                        plate_number=vehicle.get("plate_number", "")
                    )
                    sim.current_route = start_route
                    sim.route_points = interpolate_points(start_route, 100)
                    simulators.append(sim)
        
        for sim in simulators:
            # Get telemetry data
            data = sim.get_telemetry_data()
            
            # Send to API
            success = send_telemetry(data)
            
            status = "OK" if success else "FAIL"
            print(f"[{iteration}] {sim.plate_number}: "
                  f"Route: {sim.current_route} ({sim.route_direction:+d}), "
                  f"Lat: {data['latitude']:.4f}, Lng: {data['longitude']:.4f}, "
                  f"Speed: {data['speed']:.1f} km/h {status}")
        
        # Wait before next iteration
        time.sleep(SIMULATION_INTERVAL)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MakFleet IoT Simulator")
    parser.add_argument("-n", "--num-vehicles", type=int, default=None,
                       help="Number of vehicles to simulate (default: fetch from API)")
    parser.add_argument("-u", "--url", type=str, default="http://localhost:8000",
                       help="API base URL")
    
    args = parser.parse_args()
    
    API_URL = args.url
    simulate_vehicles(args.num_vehicles)
