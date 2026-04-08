// MakFleet Spatio-Temporal Knowledge Graph Schema
// Neo4j Cypher Schema for Semantic AI System

// ============================================
// NODE TYPES (Entities)
// ============================================

// Driver node with privacy attributes
CREATE (d:Driver {
    driver_id: STRING,
    anonymized_id: STRING,  // Privacy: pseudonymized identifier
    license_hash: STRING,   // Privacy: hashed license for verification
    created_at: DATETIME,
    privacy_consent: BOOLEAN,
    data_retention_days: INTEGER
});

// Vehicle node
CREATE (v:Vehicle {
    vehicle_id: STRING,
    plate_number: STRING,
    model: STRING,
    status: STRING,
    created_at: DATETIME
});

// Telemetry node (high-frequency IoT data)
CREATE (t:Telemetry {
    telemetry_id: STRING,
    timestamp: DATETIME,
    latitude: FLOAT,
    longitude: FLOAT,
    speed: FLOAT,
    acceleration: FLOAT,
    engine_temp: FLOAT,
    fuel_level: FLOAT,
    gps_accuracy: FLOAT,      // GPS noise indicator
    data_quality_score: FLOAT, // Semantic: data trustworthiness
    is_validated: BOOLEAN
});

// Event node (detected incidents)
CREATE (e:Event {
    event_id: STRING,
    event_type: STRING,       // HARSH_BRAKING, OVERSPEED, etc.
    timestamp: DATETIME,
    severity: STRING,
    confidence_score: FLOAT,  // AI model confidence
    explanation: STRING,      // Explainable AI: why this event occurred
    causal_factors: LIST       // Explainable AI: contributing factors
});

// Location node (campus zones and paths)
CREATE (loc:Location {
    location_id: STRING,
    name: STRING,
    latitude: FLOAT,
    longitude: FLOAT,
    zone_type: STRING,        // Academic, Residential, Commercial, etc.
    is_formal_path: BOOLEAN,  // Distinguishes roads from footpaths
    safety_score: FLOAT
});

// Route node (semantic route representation)
CREATE (r:Route {
    route_id: STRING,
    start_location: STRING,
    end_location: STRING,
    distance_km: FLOAT,
    estimated_time_min: FLOAT,
    difficulty_score: FLOAT,
    is_common_route: BOOLEAN
});

// Time node (temporal dimension)
CREATE (t:Time {
    time_id: STRING,
    timestamp: DATETIME,
    hour_of_day: INTEGER,
    day_of_week: STRING,
    is_peak_hour: BOOLEAN,
    is_class_time: BOOLEAN  // University-specific context
});

// Weather node (contextual factor)
CREATE (w:Weather {
    weather_id: STRING,
    timestamp: DATETIME,
    condition: STRING,        // sunny, rainy, etc.
    temperature: FLOAT,
    visibility: FLOAT
});

// Anomaly node (AI-detected patterns)
CREATE (a:Anomaly {
    anomaly_id: STRING,
    timestamp: DATETIME,
    anomaly_type: STRING,
    severity_score: FLOAT,
    detection_model: STRING,
    explanation: STRING
});

// ============================================
// RELATIONSHIP TYPES (Semantic Connections)
// ============================================

// Driver-Vehicle relationships
CREATE (d)-[:DRIVES {
    start_date: DATE,
    end_date: DATE,
    is_primary: BOOLEAN
}]->(v);

// Vehicle-Telemetry relationships
CREATE (v)-[:HAS_TELEMETRY {
    sequence_number: INTEGER
}]->(t);

// Telemetry-Event relationships
CREATE (t)-[:TRIGGERED_EVENT {
    detection_method: STRING,  // rule-based, ML-based
    confidence: FLOAT
}]->(e);

// Telemetry-Location relationships (spatial)
CREATE (t)-[:LOCATED_AT {
    distance_meters: FLOAT,
    map_matched: BOOLEAN,     // GPS noise handling
    match_confidence: FLOAT
}]->(loc);

// Event-Location relationships
CREATE (e)-[:OCCURRED_AT {
    exact_location: BOOLEAN
}]->(loc);

// Driver-Event relationships
CREATE (d)-[:INVOLVED_IN {
    responsibility_score: FLOAT
}]->(e);

// Location-Location relationships (spatial connectivity)
CREATE (loc1)-[:CONNECTED_TO {
    distance_km: FLOAT,
    travel_time_min: FLOAT,
    path_type: STRING,        // road, footpath, shortcut
    safety_rating: FLOAT
}]->(loc2);

// Route-Location relationships
CREATE (r)-[:INCLUDES {
    sequence_order: INTEGER
}]->(loc);

// Telemetry-Time relationships (temporal)
CREATE (t)-[:RECORDED_AT]->(time);

// Event-Time relationships
CREATE (e)-[:HAPPENED_AT]->(time);

// Vehicle-Route relationships
CREATE (v)-[:TRAVELED_ROUTE {
    start_time: DATETIME,
    end_time: DATETIME,
    completion_percentage: FLOAT
}]->(r);

// Anomaly-Telemetry relationships
CREATE (a)-[:DETECTED_IN {
    anomaly_score: FLOAT
}]->(t);

// Anomaly-Event relationships
CREATE (a)-[:RELATED_TO {
    relationship_type: STRING
}]->(e);

// Weather-Event relationships (contextual)
CREATE (w)-[:INFLUENCED {
    influence_score: FLOAT
}]->(e);

// ============================================
// INDEXES FOR PERFORMANCE
// ============================================

// Spatial indexes
CREATE INDEX ON :Telemetry(latitude, longitude);
CREATE INDEX ON :Location(latitude, longitude);
CREATE INDEX ON :Event(latitude, longitude);

// Temporal indexes
CREATE INDEX ON :Telemetry(timestamp);
CREATE INDEX ON :Event(timestamp);
CREATE INDEX ON :Time(timestamp);

// Entity indexes
CREATE INDEX ON :Driver(driver_id);
CREATE INDEX ON :Vehicle(vehicle_id);
CREATE INDEX ON :Event(event_type);

// Composite indexes for common queries
CREATE INDEX ON :Telemetry(vehicle_id, timestamp);
CREATE INDEX ON :Event(vehicle_id, event_type, timestamp);

// ============================================
// SEMANTIC CONSTRAINTS
// ============================================

// Ensure unique identifiers
CREATE CONSTRAINT ON (d:Driver) ASSERT d.driver_id IS UNIQUE;
CREATE CONSTRAINT ON (v:Vehicle) ASSERT v.vehicle_id IS UNIQUE;
CREATE CONSTRAINT ON (loc:Location) ASSERT loc.location_id IS UNIQUE;
CREATE CONSTRAINT ON (r:Route) ASSERT r.route_id IS UNIQUE;

// ============================================
// SAMPLE DATA FOR MAKERERE CONTEXT
// ============================================

// Create campus locations with semantic attributes
CREATE (lib:Location {
    location_id: 'LOC001',
    name: 'Main Library',
    latitude: 0.3336,
    longitude: 32.5656,
    zone_type: 'Academic',
    is_formal_path: true,
    safety_score: 0.9
});

CREATE (fs:Location {
    location_id: 'LOC002',
    name: 'Freedom Square',
    latitude: 0.3342,
    longitude: 32.5671,
    zone_type: 'Central',
    is_formal_path: true,
    safety_score: 0.85
});

CREATE (eng:Location {
    location_id: 'LOC003',
    name: 'Engineering Block',
    latitude: 0.3351,
    longitude: 32.5634,
    zone_type: 'Academic',
    is_formal_path: true,
    safety_score: 0.88
});

// Create spatial connections between locations
CREATE (lib)-[:CONNECTED_TO {
    distance_km: 0.3,
    travel_time_min: 2,
    path_type: 'road',
    safety_rating: 0.9
}]->(fs);

CREATE (fs)-[:CONNECTED_TO {
    distance_km: 0.5,
    travel_time_min: 3,
    path_type: 'road',
    safety_rating: 0.85
}]->(eng);

// Create time nodes for temporal analysis
CREATE (morning:Time {
    time_id: 'TIME_MORNING',
    hour_of_day: 8,
    day_of_week: 'Monday',
    is_peak_hour: true,
    is_class_time: true
});

CREATE (afternoon:Time {
    time_id: 'TIME_AFTERNOON',
    hour_of_day: 14,
    day_of_week: 'Monday',
    is_peak_hour: false,
    is_class_time: true
});
