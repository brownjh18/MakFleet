/**
 * MakFleet Dashboard - Map Functions
 * Handles map visualization and vehicle markers
 */

// Global map instance (initialized in index.html)
let map;
let vehicleMarkers = {};
let eventMarkers = [];
let routePolylines = [];

/**
 * Find the nearest point on a route for a given position
 * @param {Array} position - [lat, lng] position
 * @param {Array} route - Array of [lat, lng] coordinates
 * @returns {Object} - {index, distance} of nearest point
 */
function findNearestPointOnRoute(position, route) {
    let minDistance = Infinity;
    let nearestIndex = 0;
    
    for (let i = 0; i < route.length; i++) {
        const point = route[i];
        const dist = Math.sqrt(
            Math.pow(position[0] - point[0], 2) + 
            Math.pow(position[1] - point[1], 2)
        );
        if (dist < minDistance) {
            minDistance = dist;
            nearestIndex = i;
        }
    }
    
    return { index: nearestIndex, distance: minDistance };
}

/**
 * Get the appropriate route for a vehicle based on its position
 * @param {Array} position - [lat, lng] position
 * @returns {Array|null} - Route coordinates or null if no match
 */
function getRouteForPosition(position) {
    let minDistance = Infinity;
    let nearestRoute = null;
    let nearestRouteName = null;
    
    for (const [routeName, routeCoords] of Object.entries(KAMPALA_ROUTES)) {
        const { distance } = findNearestPointOnRoute(position, routeCoords);
        if (distance < minDistance) {
            minDistance = distance;
            nearestRoute = routeCoords;
            nearestRouteName = routeName;
        }
    }
    
    // Only return route if within reasonable distance (0.002 degrees ~ 200m)
    return minDistance < 0.002 ? { route: nearestRoute, name: nearestRouteName } : null;
}

/**
 * Update vehicle path on the map to follow road routes
 * @param {string} vehicleId - Vehicle ID
 * @param {Array} position - Current [lat, lng] position
 * @param {string} color - Path color
 */
function updateVehiclePath(vehicleId, position, color = '#3b82f6') {
    // Get the route for this position
    const routeInfo = getRouteForPosition(position);
    
    if (routeInfo && routeInfo.route) {
        // Store the current route for this vehicle
        vehicleRoutes[vehicleId] = routeInfo;
        
        // Find the nearest point on the route
        const { index: currentIndex } = findNearestPointOnRoute(position, routeInfo.route);
        
        // Get the path from start to current position on the route
        const pathCoords = routeInfo.route.slice(0, currentIndex + 1);
        
        // Remove old path if exists
        if (vehiclePathPolylines[vehicleId]) {
            map.removeLayer(vehiclePathPolylines[vehicleId]);
        }
        
        // Draw new path along the route
        const pathPolyline = L.polyline(pathCoords, {
            color: color,
            weight: 4,
            opacity: 0.7,
            smoothFactor: 1
        }).bindPopup(`<strong>Vehicle Path</strong><br>Route: ${routeInfo.name.replace('_', ' ').toUpperCase()}`);
        
        pathPolyline.addTo(map);
        vehiclePathPolylines[vehicleId] = pathPolyline;
    }
}

/**
 * Clear vehicle path
 * @param {string} vehicleId - Vehicle ID
 */
function clearVehiclePath(vehicleId) {
    if (vehiclePathPolylines[vehicleId]) {
        map.removeLayer(vehiclePathPolylines[vehicleId]);
        delete vehiclePathPolylines[vehicleId];
    }
}

// Store current route for each vehicle
let vehicleRoutes = {};

// Store vehicle path polylines
let vehiclePathPolylines = {};

// Animation settings
const MARKER_ANIMATION_DURATION = 1800; // ms - slightly less than update interval
const MARKER_ANIMATION_FPS = 30;

// Kampala road routes for visualization
const KAMPALA_ROUTES = {
    "makerere_main": [
        [0.3336, 32.5671], [0.3350, 32.5680], [0.3365, 32.5690], [0.3380, 32.5700],
        [0.3395, 32.5710], [0.3410, 32.5720], [0.3425, 32.5730], [0.3440, 32.5740]
    ],
    "gayaza_road": [
        [0.3336, 32.5671], [0.3350, 32.5700], [0.3370, 32.5730], [0.3390, 32.5760],
        [0.3410, 32.5790], [0.3430, 32.5820], [0.3450, 32.5850]
    ],
    "bombo_road": [
        [0.3336, 32.5671], [0.3350, 32.5690], [0.3370, 32.5710], [0.3390, 32.5730],
        [0.3410, 32.5750], [0.3430, 32.5770], [0.3450, 32.5790]
    ],
    "ng_road": [
        [0.3476, 32.5825], [0.3460, 32.5810], [0.3445, 32.5795], [0.3430, 32.5780],
        [0.3415, 32.5765], [0.3400, 32.5750]
    ],
    "port_bell_road": [
        [0.3476, 32.5825], [0.3485, 32.5800], [0.3495, 32.5780], [0.3505, 32.5760]
    ],
    "entebbe_road": [
        [0.3476, 32.5825], [0.3500, 32.5850], [0.3525, 32.5880], [0.3550, 32.5910], [0.3575, 32.5940]
    ],
    "kubika_road": [
        [0.3336, 32.5671], [0.3345, 32.5685], [0.3355, 32.5700], [0.3365, 32.5715], [0.3375, 32.5730]
    ],
    "kyebando": [
        [0.3395, 32.5710], [0.3410, 32.5730], [0.3425, 32.5750], [0.3440, 32.5770], [0.3455, 32.5790]
    ],
    "nties": [
        [0.3336, 32.5671], [0.3345, 32.5690], [0.3355, 32.5710], [0.3365, 32.5730], [0.3375, 32.5750], [0.3385, 32.5770]
    ],
    "makerere_to_kikoni": [
        [0.3336, 32.5671], [0.3350, 32.5650], [0.3365, 32.5630], [0.3380, 32.5610], [0.3395, 32.5590]
    ]
};

/**
 * Initialize the map centered on Makerere University campus
 */
function initMap() {
    // Makerere University center coordinates
    const center = [0.3336, 32.5671];
    
    // Create map instance
    map = L.map('campus-map').setView(center, 16);
    
    // Add Stamen Toner tiles for Google Maps-like clean appearance
    L.tileLayer('http://stamen-tiles-{s}.a.ssl.fastly.net/toner/{z}/{x}/{y}.png', {
        attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> — Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        subdomains: 'a,b,c,d',
        maxZoom: 18
    }).addTo(map);
    
    // Add campus landmarks
    addCampusLandmarks();
    
    // Add map controls
    addMapControls();
}

/**
 * Add campus landmarks as markers
 */
function addCampusLandmarks() {
    const landmarks = [
        { name: 'Main Library', lat: 0.3336, lng: 32.5656, type: 'library' },
        { name: 'Freedom Square', lat: 0.3342, lng: 32.5671, type: 'square' },
        { name: 'Engineering Block', lat: 0.3351, lng: 32.5634, type: 'building' },
        { name: 'Mary Stuart Hall', lat: 0.3328, lng: 32.5689, type: 'building' },
        { name: 'Central Teaching Facility', lat: 0.3345, lng: 32.5662, type: 'building' },
        { name: 'Food Court', lat: 0.3339, lng: 32.5685, type: 'food' },
        { name: 'Sports Complex', lat: 0.3319, lng: 32.5698, type: 'sports' },
        { name: 'Medical School', lat: 0.3362, lng: 32.5645, type: 'building' }
    ];
    
    landmarks.forEach(landmark => {
        const marker = L.marker([landmark.lat, landmark.lng])
            .bindPopup(`
                <div style="text-align: center;">
                    <strong>${landmark.name}</strong><br>
                    <span style="color: #666;">${landmark.type}</span>
                </div>
            `);
        marker.addTo(map);
    });
}

/**
 * Add map controls (zoom, layers, etc.)
 */
function addMapControls() {
    // Add scale control
    L.control.scale({
        imperial: false,
        metric: true
    }).addTo(map);
}

/**
 * Animate marker smoothly from current position to new position
 * @param {L.Marker} marker - The Leaflet marker
 * @param {Array} newPosition - [lat, lng] new position
 */
function animateMarkerTo(marker, newPosition) {
    const startPos = marker.getLatLng();
    const endPos = L.latLng(newPosition[0], newPosition[1]);
    
    // If distance is very small, just move directly
    if (startPos.distanceTo(endPos) < 0.5) {
        marker.setLatLng(endPos);
        return;
    }
    
    // Animate using requestAnimationFrame
    const startTime = performance.now();
    
    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / MARKER_ANIMATION_DURATION, 1);
        
        // Use ease-out function for smooth animation
        const easeProgress = 1 - Math.pow(1 - progress, 3);
        
        const lat = startPos.lat + (endPos.lat - startPos.lat) * easeProgress;
        const lng = startPos.lng + (endPos.lng - startPos.lng) * easeProgress;
        
        marker.setLatLng([lat, lng]);
        
        if (progress < 1) {
            requestAnimationFrame(animate);
        }
    }
    
    requestAnimationFrame(animate);
}

/**
 * Update vehicle markers on the map with smooth animation
 * @param {Array} vehicles - Array of vehicle telemetry data
 */
function updateVehicleMarkers(vehicles) {
    vehicles.forEach(vehicle => {
        const position = [vehicle.latitude, vehicle.longitude];
        
        // Determine marker color based on speed
        let markerColor = 'blue';
        if (vehicle.speed > 70) {
            markerColor = 'red';
        } else if (vehicle.speed > 50) {
            markerColor = 'orange';
        }
        
        // Create custom icon
        const vehicleIcon = L.divIcon({
            className: 'vehicle-marker',
            html: `<div style="
                background-color: ${markerColor};
                width: 24px;
                height: 24px;
                border-radius: 50%;
                border: 2px solid white;
                box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
            ">🚴</div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });
        
        if (vehicleMarkers[vehicle.vehicle_id]) {
            // Animate to new position smoothly
            animateMarkerTo(vehicleMarkers[vehicle.vehicle_id], position);
            vehicleMarkers[vehicle.vehicle_id].setIcon(vehicleIcon);
            
            // Update vehicle path to follow road routes
            updateVehiclePath(vehicle.vehicle_id, position, markerColor === 'red' ? '#ef4444' : markerColor === 'orange' ? '#f59e0b' : '#3b82f6');
            
            vehicleMarkers[vehicle.vehicle_id].getPopup().setContent(`
                <div style="min-width: 150px;">
                    <strong>${vehicle.plate_number}</strong><br>
                    <hr style="margin: 5px 0; border: none; border-top: 1px solid #eee;">
                    Driver: ${vehicle.driver_name}<br>
                    Speed: ${vehicle.speed.toFixed(1)} km/h<br>
                    Time: ${new Date(vehicle.timestamp).toLocaleTimeString()}
                </div>
            `);
        } else {
            // Create new marker
            const marker = L.marker(position, { icon: vehicleIcon })
                .bindPopup(`
                    <div style="min-width: 150px;">
                        <strong>${vehicle.plate_number}</strong><br>
                        <hr style="margin: 5px 0; border: none; border-top: 1px solid #eee;">
                        Driver: ${vehicle.driver_name}<br>
                        Speed: ${vehicle.speed.toFixed(1)} km/h<br>
                        Time: ${new Date(vehicle.timestamp).toLocaleTimeString()}
                    </div>
                `);
            marker.addTo(map);
            vehicleMarkers[vehicle.vehicle_id] = marker;
        }
    });
}

/**
 * Update event markers on the map
 * @param {Array} events - Array of event data
 */
function updateEventMarkers(events) {
    // Remove old event markers
    eventMarkers.forEach(marker => map.removeLayer(marker));
    eventMarkers = [];
    
    // Event type colors
    const eventColors = {
        'HARSH_BRAKING': '#ef4444',
        'OVERSPEED': '#f59e0b',
        'RAPID_ACCELERATION': '#8b5cf6',
        'IDLING': '#6b7280'
    };
    
    // Add new event markers
    events.forEach(event => {
        const color = eventColors[event.event_type] || '#6b7280';
        
        const marker = L.circleMarker([event.latitude, event.longitude], {
            radius: 10,
            fillColor: color,
            color: '#fff',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.8
        }).bindPopup(`
            <div style="min-width: 180px;">
                <strong style="color: ${color};">${event.event_type.replace('_', ' ')}</strong><br>
                <hr style="margin: 5px 0; border: none; border-top: 1px solid #eee;">
                <strong>Vehicle:</strong> ${event.plate_number}<br>
                <strong>Driver:</strong> ${event.driver_name}<br>
                <strong>Speed:</strong> ${event.speed ? event.speed.toFixed(1) + ' km/h' : 'N/A'}<br>
                <strong>Severity:</strong> <span style="color: ${event.severity === 'high' ? 'red' : event.severity === 'medium' ? 'orange' : 'green'};">${event.severity}</span><br>
                <strong>Time:</strong> ${new Date(event.timestamp).toLocaleString()}
            </div>
        `);
        
        marker.addTo(map);
        eventMarkers.push(marker);
    });
}

/**
 * Draw all road routes on the map
 */
function drawRoadRoutes() {
    const routeColors = {
        "makerere_main": '#1e3c72',
        "gayaza_road": '#2ecc71',
        "bombo_road": '#e74c3c',
        "ng_road": '#9b59b6',
        "port_bell_road": '#3498db',
        "entebbe_road": '#f39c12',
        "kubika_road": '#1abc9c',
        "kyebando": '#e67e22',
        "nties": '#34495e',
        "makerere_to_kikoni": '#95a5a6'
    };
    
    Object.keys(KAMPALA_ROUTES).forEach(routeName => {
        const coordinates = KAMPALA_ROUTES[routeName];
        const color = routeColors[routeName] || '#666';
        
        const polyline = L.polyline(coordinates, {
            color: color,
            weight: 4,
            opacity: 0.8,
            dashArray: '5, 10'
        }).bindPopup(`<strong>${routeName.replace('_', ' ').toUpperCase()}</strong>`);
        
        polyline.addTo(map);
        routePolylines.push(polyline);
    });
}

/**
 * Clear all route polylines
 */
function clearRoutes() {
    routePolylines.forEach(polyline => map.removeLayer(polyline));
    routePolylines = [];
}

/**
 * Fit map to show all markers
 */
function fitMapToMarkers() {
    const allLatLngs = [];
    
    // Get all vehicle marker positions
    Object.values(vehicleMarkers).forEach(marker => {
        allLatLngs.push(marker.getLatLng());
    });
    
    // Get all event marker positions
    eventMarkers.forEach(marker => {
        allLatLngs.push(marker.getLatLng());
    });
    
    if (allLatLngs.length > 0) {
        const bounds = L.latLngBounds(allLatLngs);
        map.fitBounds(bounds, { padding: [50, 50] });
    }
}

/**
 * Center map on campus
 */
function centerOnCampus() {
    map.setView([0.3336, 32.5671], 16);
}
