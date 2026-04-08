"""
Enhanced MakFleet IoT Simulator
Generates realistic campus spatio-temporal data with noise and semantic context
"""
import asyncio
import random
import math
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
import numpy as np
from dataclasses import dataclass


@dataclass
class CampusRoute:
    """Represents a campus route with waypoints"""
    route_id: str
    name: str
    waypoints: List[Dict[str, float]]
    difficulty_score: float
    common_usage_pattern: str  # peak_hours, off_peak, academic_only


@dataclass
class DriverBehavior:
    """Driver behavior profile for realistic simulation"""
    driver_id: str
    risk_profile: str  # conservative, normal, aggressive
    speed_preference: str  # slow, normal, fast
    route_preference: List[str]  # preferred routes
    peak_hour_multiplier: float  # how much more they drive during peak hours


class EnhancedIoTSimulator:
    """Enhanced IoT simulator with realistic campus behavior"""

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.is_running = False

        # Campus boundaries (Makerere University approximate)
        self.campus_bounds = {
            'north': 0.3400,
            'south': 0.3300,
            'east': 32.5700,
            'west': 32.5600
        }

        # Initialize campus routes
        self.routes = self._initialize_routes()

        # Initialize driver behaviors
        self.drivers = self._initialize_drivers()

        # Simulation state
        self.active_vehicles = {}
        self.weather_conditions = self._get_weather_conditions()

    def _initialize_routes(self) -> List[CampusRoute]:
        """Initialize realistic campus routes"""
        return [
            CampusRoute(
                route_id="route_main_gate_to_lib",
                name="Main Gate to Library",
                waypoints=[
                    {'lat': 0.3330, 'lon': 32.5650},  # Main Gate
                    {'lat': 0.3335, 'lon': 32.5655},  # Freedom Square approach
                    {'lat': 0.3342, 'lon': 32.5671},  # Freedom Square
                    {'lat': 0.3336, 'lon': 32.5656},  # Main Library
                ],
                difficulty_score=0.3,
                common_usage_pattern="peak_hours"
            ),
            CampusRoute(
                route_id="route_lib_to_engineering",
                name="Library to Engineering Block",
                waypoints=[
                    {'lat': 0.3336, 'lon': 32.5656},  # Main Library
                    {'lat': 0.3345, 'lon': 32.5662},  # Central Teaching Facility
                    {'lat': 0.3351, 'lon': 32.5634},  # Engineering Block
                ],
                difficulty_score=0.4,
                common_usage_pattern="academic_only"
            ),
            CampusRoute(
                route_id="route_food_court_loop",
                name="Food Court Loop",
                waypoints=[
                    {'lat': 0.3339, 'lon': 32.5685},  # Food Court
                    {'lat': 0.3328, 'lon': 32.5689},  # Mary Stuart Hall
                    {'lat': 0.3319, 'lon': 32.5698},  # Sports Complex
                    {'lat': 0.3339, 'lon': 32.5685},  # Back to Food Court
                ],
                difficulty_score=0.6,
                common_usage_pattern="off_peak"
            ),
            CampusRoute(
                route_id="route_shortcut_path",
                name="Informal Footpath Shortcut",
                waypoints=[
                    {'lat': 0.3342, 'lon': 32.5671},  # Freedom Square
                    {'lat': 0.3355, 'lon': 32.5645},  # Informal path
                    {'lat': 0.3351, 'lon': 32.5634},  # Engineering Block
                ],
                difficulty_score=0.8,
                common_usage_pattern="off_peak"
            )
        ]

    def _initialize_drivers(self) -> List[DriverBehavior]:
        """Initialize driver behavior profiles"""
        return [
            DriverBehavior(
                driver_id="DRV_001",
                risk_profile="conservative",
                speed_preference="slow",
                route_preference=["route_main_gate_to_lib"],
                peak_hour_multiplier=0.8
            ),
            DriverBehavior(
                driver_id="DRV_002",
                risk_profile="normal",
                speed_preference="normal",
                route_preference=["route_lib_to_engineering", "route_food_court_loop"],
                peak_hour_multiplier=1.2
            ),
            DriverBehavior(
                driver_id="DRV_003",
                risk_profile="aggressive",
                speed_preference="fast",
                route_preference=["route_shortcut_path"],
                peak_hour_multiplier=1.5
            ),
            DriverBehavior(
                driver_id="DRV_004",
                risk_profile="normal",
                speed_preference="normal",
                route_preference=["route_main_gate_to_lib", "route_lib_to_engineering"],
                peak_hour_multiplier=1.0
            ),
            DriverBehavior(
                driver_id="DRV_005",
                risk_profile="conservative",
                speed_preference="slow",
                route_preference=["route_food_court_loop"],
                peak_hour_multiplier=0.6
            )
        ]

    def _get_weather_conditions(self) -> Dict[str, Any]:
        """Get current weather conditions (simplified)"""
        conditions = ['sunny', 'cloudy', 'rainy', 'partly_cloudy']
        return {
            'condition': random.choice(conditions),
            'temperature': random.uniform(20, 32),  # Celsius
            'visibility': random.uniform(5, 15),  # km
            'wind_speed': random.uniform(0, 10)  # km/h
        }

    def _calculate_realistic_speed(self, driver: DriverBehavior, route: CampusRoute,
                                 position_index: int, hour_of_day: int,
                                 weather: Dict[str, Any]) -> float:
        """Calculate realistic speed based on multiple factors"""
        base_speed = 20.0  # km/h base speed

        # Driver preference modifier
        speed_modifier = {
            'slow': 0.7,
            'normal': 1.0,
            'fast': 1.4
        }[driver.speed_preference]

        # Route difficulty modifier
        route_modifier = 1.0 - (route.difficulty_score * 0.3)

        # Time of day modifier (slower during peak hours due to traffic)
        is_peak_hour = hour_of_day in [7, 8, 17, 18]
        time_modifier = 0.8 if is_peak_hour else 1.1

        # Weather modifier
        weather_modifier = {
            'sunny': 1.0,
            'cloudy': 0.95,
            'partly_cloudy': 0.98,
            'rainy': 0.7
        }.get(weather['condition'], 1.0)

        # Position on route modifier (slower at intersections)
        position_modifier = 0.9 if position_index in [0, len(route.waypoints) - 1] else 1.0

        speed = base_speed * speed_modifier * route_modifier * time_modifier * weather_modifier * position_modifier

        # Add realistic variation (±20%)
        speed *= random.uniform(0.8, 1.2)

        # Ensure reasonable bounds
        return max(5.0, min(60.0, speed))

    def _calculate_acceleration(self, current_speed: float, target_speed: float,
                              time_step: float) -> float:
        """Calculate realistic acceleration"""
        speed_diff = target_speed - current_speed
        if abs(speed_diff) < 1.0:  # Minimal change
            return random.uniform(-0.5, 0.5)

        # Calculate required acceleration (with some randomness)
        acceleration = speed_diff / time_step + random.uniform(-2.0, 2.0)

        # Add occasional harsh events
        if random.random() < 0.05:  # 5% chance
            acceleration += random.choice([-6.0, 6.0])  # Harsh braking/acceleration

        return acceleration

    def _add_gps_noise(self, lat: float, lon: float, accuracy: float = 10.0) -> Tuple[float, float, float]:
        """Add realistic GPS noise"""
        # GPS accuracy in meters affects noise level
        noise_level = accuracy / 10.0  # Scale noise with accuracy

        # Convert to coordinate noise (rough approximation)
        lat_noise = random.gauss(0, noise_level * 0.00001)
        lon_noise = random.gauss(0, noise_level * 0.00001)

        noisy_lat = lat + lat_noise
        noisy_lon = lon + lon_noise

        return noisy_lat, noisy_lon, accuracy

    def _generate_semantic_context(self, vehicle_data: Dict[str, Any],
                                 route: CampusRoute, position_index: int) -> Dict[str, Any]:
        """Generate semantic context for telemetry"""
        timestamp = datetime.fromisoformat(vehicle_data['timestamp'])
        hour_of_day = timestamp.hour

        context = {
            'timestamp': vehicle_data['timestamp'],
            'hour_of_day': hour_of_day,
            'day_of_week': timestamp.strftime('%A'),
            'is_peak_hour': hour_of_day in [7, 8, 17, 18],
            'is_class_time': 8 <= hour_of_day <= 18 and timestamp.weekday() < 5,
            'route_name': route.name,
            'route_difficulty': route.difficulty_score,
            'position_on_route': f"{position_index + 1}/{len(route.waypoints)}",
            'weather_condition': self.weather_conditions['condition'],
            'weather_visibility': self.weather_conditions['visibility'],
            'is_formal_path': 'formal' in route.name.lower() or 'road' in route.name.lower()
        }

        # Add speed category
        speed = vehicle_data.get('speed', 0)
        if speed < 10:
            context['speed_category'] = 'stopped'
        elif speed < 25:
            context['speed_category'] = 'slow'
        elif speed < 45:
            context['speed_category'] = 'normal'
        else:
            context['speed_category'] = 'fast'

        # Add acceleration category
        acceleration = vehicle_data.get('acceleration', 0)
        if acceleration < -4:
            context['acceleration_category'] = 'harsh_braking'
        elif acceleration < -2:
            context['acceleration_category'] = 'braking'
        elif acceleration < 2:
            context['acceleration_category'] = 'normal'
        elif acceleration < 4:
            context['acceleration_category'] = 'accelerating'
        else:
            context['acceleration_category'] = 'rapid_acceleration'

        return context

    async def start_simulation(self, num_vehicles: int = 3, duration_minutes: int = 60):
        """Start the enhanced simulation"""
        self.is_running = True
        print(f"🚀 Starting enhanced MakFleet simulation with {num_vehicles} vehicles for {duration_minutes} minutes")

        # Initialize vehicles
        for i in range(num_vehicles):
            vehicle_id = f"VHC_{i+1:03d}"
            driver = random.choice(self.drivers)

            # Select route based on driver preference and time
            current_hour = datetime.now().hour
            available_routes = [
                route for route in self.routes
                if route.route_id in driver.route_preference or random.random() < 0.3  # 30% chance for other routes
            ]
            route = random.choice(available_routes) if available_routes else random.choice(self.routes)

            self.active_vehicles[vehicle_id] = {
                'driver': driver,
                'route': route,
                'current_position_index': 0,
                'current_speed': 0.0,
                'last_update': datetime.now()
            }

        # Run simulation
        end_time = datetime.now() + timedelta(minutes=duration_minutes)

        while datetime.now() < end_time and self.is_running:
            await self._simulate_time_step()
            await asyncio.sleep(3)  # 3 second intervals

        print("🏁 Enhanced simulation completed")

    async def _simulate_time_step(self):
        """Simulate one time step for all vehicles"""
        current_time = datetime.now()

        for vehicle_id, vehicle_state in self.active_vehicles.items():
            await self._update_vehicle_position(vehicle_id, vehicle_state, current_time)

    async def _update_vehicle_position(self, vehicle_id: str, vehicle_state: Dict[str, Any],
                                     current_time: datetime):
        """Update vehicle position and send telemetry"""
        route = vehicle_state['route']
        position_index = vehicle_state['current_position_index']

        if position_index >= len(route.waypoints) - 1:
            # Route completed, select new route
            position_index = 0
            # 70% chance to continue with same route, 30% chance to change
            if random.random() < 0.3:
                available_routes = [r for r in self.routes if r != route]
                if available_routes:
                    route = random.choice(available_routes)
                    vehicle_state['route'] = route

        # Calculate movement
        current_waypoint = route.waypoints[position_index]
        next_waypoint = route.waypoints[position_index + 1]

        # Calculate distance to next waypoint
        distance = self._calculate_distance(
            current_waypoint['lat'], current_waypoint['lon'],
            next_waypoint['lat'], next_waypoint['lon']
        )

        # Calculate realistic speed
        speed = self._calculate_realistic_speed(
            vehicle_state['driver'], route, position_index,
            current_time.hour, self.weather_conditions
        )

        # Calculate time step (3 seconds)
        time_step = 3.0
        distance_covered = (speed * 1000 / 3600) * time_step  # Convert to meters

        # Move towards next waypoint
        if distance > distance_covered:
            # Not yet reached next waypoint
            ratio = distance_covered / distance
            lat = current_waypoint['lat'] + ratio * (next_waypoint['lat'] - current_waypoint['lat'])
            lon = current_waypoint['lon'] + ratio * (next_waypoint['lon'] - current_waypoint['lon'])
        else:
            # Reached next waypoint
            lat, lon = next_waypoint['lat'], next_waypoint['lon']
            position_index += 1
            vehicle_state['current_position_index'] = position_index

        # Calculate acceleration
        acceleration = self._calculate_acceleration(
            vehicle_state['current_speed'], speed, time_step
        )

        # Add GPS noise
        noisy_lat, noisy_lon, gps_accuracy = self._add_gps_noise(lat, lon)

        # Update vehicle state
        vehicle_state['current_speed'] = speed
        vehicle_state['last_update'] = current_time

        # Generate telemetry data
        telemetry = {
            'telemetry_id': f"tel_{vehicle_id}_{int(current_time.timestamp())}",
            'vehicle_id': vehicle_id,
            'latitude': noisy_lat,
            'longitude': noisy_lon,
            'speed': speed,
            'acceleration': acceleration,
            'timestamp': current_time.isoformat(),
            'gps_accuracy': gps_accuracy,
            'engine_temp': random.uniform(70, 95),  # Celsius
            'fuel_level': random.uniform(20, 100),  # Percentage
            'driver_id': vehicle_state['driver'].driver_id,
            'route_id': route.route_id
        }

        # Add semantic context
        telemetry['semantic_context'] = self._generate_semantic_context(
            telemetry, route, position_index
        )

        # Send to API
        await self._send_telemetry(telemetry)

    async def _send_telemetry(self, telemetry: Dict[str, Any]):
        """Send telemetry data to API"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}/api/semantic/process-telemetry-batch"
                payload = {"telemetry_data": [telemetry]}

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        print(f"📡 Sent telemetry for {telemetry['vehicle_id']}: {result.get('anomalies_detected', 0)} anomalies")
                    else:
                        print(f"❌ Failed to send telemetry: {response.status}")

        except Exception as e:
            print(f"❌ Error sending telemetry: {e}")

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters"""
        R = 6371000  # Earth radius in meters

        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def stop_simulation(self):
        """Stop the simulation"""
        self.is_running = False
        print("🛑 Simulation stopped")

    async def run_scenario(self, scenario: str):
        """Run specific simulation scenarios"""
        scenarios = {
            'peak_hour_rush': lambda: self._configure_peak_hour_scenario(),
            'rainy_weather_disruption': lambda: self._configure_rainy_weather_scenario(),
            'campus_event': lambda: self._configure_campus_event_scenario(),
            'normal_operations': lambda: self._configure_normal_scenario()
        }

        if scenario in scenarios:
            scenarios[scenario]()
            print(f"🎭 Running scenario: {scenario}")
        else:
            print(f"❌ Unknown scenario: {scenario}")

    def _configure_peak_hour_scenario(self):
        """Configure simulation for peak hour rush"""
        self.weather_conditions = {'condition': 'cloudy', 'temperature': 28, 'visibility': 10, 'wind_speed': 5}
        # Increase vehicle count and adjust behaviors
        for driver in self.drivers:
            driver.peak_hour_multiplier = 2.0

    def _configure_rainy_weather_scenario(self):
        """Configure simulation for rainy weather"""
        self.weather_conditions = {'condition': 'rainy', 'temperature': 24, 'visibility': 3, 'wind_speed': 15}

    def _configure_campus_event_scenario(self):
        """Configure simulation for campus event"""
        # Increase activity in central areas, more traffic
        for route in self.routes:
            if 'freedom' in route.name.lower() or 'central' in route.name.lower():
                route.difficulty_score *= 1.5  # More congestion

    def _configure_normal_scenario(self):
        """Configure normal operations"""
        self.weather_conditions = {'condition': 'sunny', 'temperature': 30, 'visibility': 12, 'wind_speed': 3}


async def main():
    """Main simulation function"""
    simulator = EnhancedIoTSimulator()

    print("🎮 Enhanced MakFleet IoT Simulator")
    print("Commands:")
    print("  start <num_vehicles> <duration_minutes> - Start simulation")
    print("  scenario <scenario_name> - Run specific scenario")
    print("  stop - Stop simulation")
    print("  quit - Exit")

    while True:
        try:
            cmd = input("simulator> ").strip().split()

            if not cmd:
                continue

            if cmd[0] == 'start':
                num_vehicles = int(cmd[1]) if len(cmd) > 1 else 3
                duration = int(cmd[2]) if len(cmd) > 2 else 60
                await simulator.start_simulation(num_vehicles, duration)

            elif cmd[0] == 'scenario':
                if len(cmd) > 1:
                    await simulator.run_scenario(cmd[1])
                else:
                    print("Usage: scenario <scenario_name>")

            elif cmd[0] == 'stop':
                simulator.stop_simulation()

            elif cmd[0] == 'quit':
                simulator.stop_simulation()
                break

            else:
                print(f"Unknown command: {cmd[0]}")

        except KeyboardInterrupt:
            simulator.stop_simulation()
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
