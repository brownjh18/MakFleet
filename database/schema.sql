-- MakFleet Spatio-Temporal Data Warehouse Prototype
-- Database Schema (Updated with AI System Extensions)

-- Enable PostGIS extension for spatial data
CREATE EXTENSION IF NOT EXISTS postgis;

-- Drop tables if they exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS vehicle_maintenance CASCADE;
DROP TABLE IF EXISTS driver_performance CASCADE;
DROP TABLE IF EXISTS time_dimension CASCADE;
DROP TABLE IF EXISTS trips CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS weather CASCADE;
DROP TABLE IF EXISTS data_provenance CASCADE;
DROP TABLE IF EXISTS evaluation_results CASCADE;
DROP TABLE IF EXISTS anomalies CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS telemetry CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS drivers CASCADE;
DROP TABLE IF EXISTS locations CASCADE;

-- ============================================
-- CORE TABLES (Enhanced with AI/Semantic columns)
-- ============================================

-- Drivers table
CREATE TABLE drivers (
    driver_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    license_number VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Privacy extensions
    anonymized_id VARCHAR(32) UNIQUE,
    license_hash VARCHAR(64),
    privacy_consent BOOLEAN DEFAULT FALSE,
    data_retention_days INTEGER DEFAULT 30
);

-- Vehicles table
CREATE TABLE vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    plate_number VARCHAR(20) UNIQUE NOT NULL,
    driver_id INT REFERENCES drivers(driver_id),
    model VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Privacy extensions
    plate_number_hash VARCHAR(64),
    model_category VARCHAR(50)
);

-- Telemetry data table (stores raw IoT sensor data with semantic extensions)
CREATE TABLE telemetry (
    telemetry_id SERIAL PRIMARY KEY,
    vehicle_id INT REFERENCES vehicles(vehicle_id) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    speed FLOAT NOT NULL,
    acceleration FLOAT,
    engine_temp FLOAT,
    fuel_level FLOAT,
    timestamp TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Semantic extensions
    gps_accuracy FLOAT DEFAULT 10.0,
    data_quality_score FLOAT DEFAULT 0.8,
    is_validated BOOLEAN DEFAULT FALSE,
    semantic_context TEXT,
    map_matched BOOLEAN DEFAULT FALSE,
    matched_location_id VARCHAR(32),
    match_confidence FLOAT,
    provenance_id VARCHAR(64)
);

-- Events table (stores detected events with AI extensions)
CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    vehicle_id INT REFERENCES vehicles(vehicle_id) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    speed FLOAT,
    acceleration FLOAT,
    timestamp TIMESTAMP NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- AI/Explainability extensions
    confidence_score FLOAT DEFAULT 0.8,
    explanation TEXT,
    causal_factors TEXT,
    ai_detected BOOLEAN DEFAULT FALSE
);

-- Locations table (for campus zones with semantic attributes)
CREATE TABLE locations (
    location_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    zone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Semantic extensions
    zone_type VARCHAR(50),
    is_formal_path BOOLEAN DEFAULT TRUE,
    safety_score FLOAT DEFAULT 0.8,
    capacity INTEGER,
    operating_hours TEXT
);

-- ============================================
-- NEW TABLES FOR AI SYSTEM
-- ============================================

-- Weather data table
CREATE TABLE weather (
    weather_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    precipitation FLOAT,
    wind_speed FLOAT,
    wind_direction VARCHAR(10),
    conditions VARCHAR(50),  -- sunny, rainy, cloudy, etc.
    visibility FLOAT,
    source VARCHAR(50) DEFAULT 'OpenWeatherMap',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Routes table
CREATE TABLE routes (
    route_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    start_location_id INT REFERENCES locations(location_id),
    end_location_id INT REFERENCES locations(location_id),
    distance_km FLOAT,
    estimated_duration_min FLOAT,
    is_common_route BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    safety_score FLOAT DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trips table (tracks individual trips)
CREATE TABLE trips (
    trip_id SERIAL PRIMARY KEY,
    vehicle_id INT REFERENCES vehicles(vehicle_id) NOT NULL,
    driver_id INT REFERENCES drivers(driver_id) NOT NULL,
    route_id INT REFERENCES routes(route_id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    start_location_id INT REFERENCES locations(location_id),
    end_location_id INT REFERENCES locations(location_id),
    distance_km FLOAT,
    duration_min FLOAT,
    avg_speed FLOAT,
    max_speed FLOAT,
    status VARCHAR(20) DEFAULT 'in_progress',  -- in_progress, completed, cancelled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Time dimension table (for temporal analysis)
CREATE TABLE time_dimension (
    time_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL UNIQUE,
    date DATE NOT NULL,
    time VARCHAR(8) NOT NULL,
    hour INTEGER NOT NULL,
    minute INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,  -- 0=Sunday, 6=Saturday
    day_name VARCHAR(10) NOT NULL,
    day_of_month INTEGER NOT NULL,
    day_of_year INTEGER NOT NULL,
    week_of_year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(10) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN DEFAULT FALSE,
    is_peak_hour BOOLEAN DEFAULT FALSE,
    peak_period VARCHAR(20),  -- morning_peak, evening_peak, off_peak
    is_class_time BOOLEAN DEFAULT FALSE,  -- During class hours
    semester_period VARCHAR(20)  -- semester, break, exam
);

-- Driver performance table
CREATE TABLE driver_performance (
    performance_id SERIAL PRIMARY KEY,
    driver_id INT REFERENCES drivers(driver_id) NOT NULL,
    date DATE NOT NULL,
    total_trips INTEGER DEFAULT 0,
    total_distance_km FLOAT DEFAULT 0,
    total_duration_min FLOAT DEFAULT 0,
    avg_speed FLOAT,
    max_speed FLOAT,
    harsh_braking_count INTEGER DEFAULT 0,
    overspeed_count INTEGER DEFAULT 0,
    rapid_acceleration_count INTEGER DEFAULT 0,
    risk_score FLOAT DEFAULT 0,  -- 0-100, lower is better
    safety_score FLOAT DEFAULT 1.0,  -- 0-1, higher is better
    efficiency_score FLOAT DEFAULT 0.8,
    incidents_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(driver_id, date)
);

-- Vehicle maintenance table
CREATE TABLE vehicle_maintenance (
    maintenance_id SERIAL PRIMARY KEY,
    vehicle_id INT REFERENCES vehicles(vehicle_id) NOT NULL,
    maintenance_type VARCHAR(50) NOT NULL,  -- routine, repair, inspection
    description TEXT,
    scheduled_date DATE,
    completed_date DATE,
    cost FLOAT,
    mileage_at_service FLOAT,
    next_service_due DATE,
    next_service_mileage FLOAT,
    service_provider VARCHAR(100),
    status VARCHAR(20) DEFAULT 'scheduled',  -- scheduled, in_progress, completed, overdue
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data provenance table
CREATE TABLE data_provenance (
    provenance_id VARCHAR(64) PRIMARY KEY,
    source_system VARCHAR(50) NOT NULL,
    source_version VARCHAR(20),
    extraction_timestamp TIMESTAMP NOT NULL,
    processing_timestamp TIMESTAMP,
    pipeline_version VARCHAR(20),
    transformations_applied TEXT,  -- JSON array of transformations
    data_quality_score FLOAT DEFAULT 0.8,
    validation_status VARCHAR(20) DEFAULT 'pending',  -- pending, passed, failed
    validation_errors TEXT,
    record_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Anomalies table (AI-detected)
CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id VARCHAR(64) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    severity_score FLOAT NOT NULL,
    detection_model VARCHAR(50),
    confidence FLOAT,
    explanation TEXT,
    causal_factors TEXT,
    affected_entities TEXT,
    recommended_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Evaluation results table
CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    dataset VARCHAR(100) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    auc_roc FLOAT,
    mse FLOAT,
    mae FLOAT,
    rmse FLOAT,
    inference_time_ms FLOAT,
    memory_usage_mb FLOAT,
    model_size_mb FLOAT,
    spatial_accuracy FLOAT,
    temporal_consistency FLOAT,
    anomaly_detection_rate FLOAT,
    business_value_score FLOAT
);

-- Model metrics table (for tracking trained model performance)
CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) DEFAULT '1.0',
    accuracy DECIMAL(5,2),
    precision DECIMAL(5,2),
    recall DECIMAL(5,2),
    f1_score DECIMAL(5,2),
    auc_roc DECIMAL(5,2),
    ade DECIMAL(5,2),  -- Average Displacement Error
    fde DECIMAL(5,2),  -- Final Displacement Error
    training_samples INTEGER,
    validation_samples INTEGER,
    epochs INTEGER,
    batch_size INTEGER,
    learning_rate DECIMAL(10,6),
    training_duration_sec FLOAT,
    trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Training history table (for tracking training progression)
CREATE TABLE IF NOT EXISTS training_history (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    epoch INTEGER NOT NULL,
    loss DECIMAL(10,6) NOT NULL,
    val_loss DECIMAL(10,6),
    accuracy DECIMAL(5,2),
    val_accuracy DECIMAL(5,2),
    learning_rate DECIMAL(10,6),
    duration_sec FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily analytics summary table
CREATE TABLE IF NOT EXISTS daily_analytics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    total_vehicles INTEGER DEFAULT 0,
    active_vehicles INTEGER DEFAULT 0,
    total_trips INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    anomalies_detected INTEGER DEFAULT 0,
    data_quality_score DECIMAL(5,2) DEFAULT 0,
    avg_accuracy DECIMAL(5,2) DEFAULT 0,
    avg_speed DECIMAL(5,2),
    max_speed DECIMAL(5,2),
    harsh_braking_count INTEGER DEFAULT 0,
    overspeed_count INTEGER DEFAULT 0,
    rapid_acceleration_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System performance metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    response_time_ms INTEGER,
    inference_time_ms INTEGER,
    active_connections INTEGER,
    requests_per_minute INTEGER,
    error_rate DECIMAL(5,2)
);

-- ============================================
-- CREATE INDEXES
-- ============================================

-- Core table indexes
CREATE INDEX idx_telemetry_vehicle_id ON telemetry(vehicle_id);
CREATE INDEX idx_telemetry_timestamp ON telemetry(timestamp);
CREATE INDEX idx_telemetry_map_matched ON telemetry(map_matched);
CREATE INDEX idx_events_vehicle_id ON events(vehicle_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_ai_detected ON events(ai_detected);

-- Spatial indexes
CREATE INDEX idx_telemetry_geom ON telemetry USING GIST (ST_MakePoint(longitude, latitude));
CREATE INDEX idx_events_geom ON events USING GIST (ST_MakePoint(longitude, latitude));
CREATE INDEX idx_locations_geom ON locations USING GIST (ST_MakePoint(longitude, latitude));

-- New table indexes
CREATE INDEX idx_weather_timestamp ON weather(timestamp);
CREATE INDEX idx_weather_conditions ON weather(conditions);
CREATE INDEX idx_routes_start_end ON routes(start_location_id, end_location_id);
CREATE INDEX idx_trips_vehicle_id ON trips(vehicle_id);
CREATE INDEX idx_trips_driver_id ON trips(driver_id);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_time_range ON trips(start_time, end_time);
CREATE INDEX idx_time_dimension_date ON time_dimension(date);
CREATE INDEX idx_time_dimension_timestamp ON time_dimension(timestamp);
CREATE INDEX idx_driver_performance_driver_id ON driver_performance(driver_id);
CREATE INDEX idx_driver_performance_date ON driver_performance(date);
CREATE INDEX idx_vehicle_maintenance_vehicle_id ON vehicle_maintenance(vehicle_id);
CREATE INDEX idx_vehicle_maintenance_status ON vehicle_maintenance(status);
CREATE INDEX idx_data_provenance_source ON data_provenance(source_system);
CREATE INDEX idx_data_provenance_timestamp ON data_provenance(extraction_timestamp);
CREATE INDEX idx_anomalies_timestamp ON anomalies(timestamp);
CREATE INDEX idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX idx_evaluation_model ON evaluation_results(model_name);
CREATE INDEX idx_evaluation_timestamp ON evaluation_results(timestamp);

-- ============================================
-- INSERT SAMPLE DATA
-- ============================================

-- Insert sample drivers
INSERT INTO drivers (name, phone, license_number, anonymized_id, privacy_consent) VALUES
    ('John Kato', '+256701234567', 'DL/2020/001', 'DRV_ANON_001', TRUE),
    ('Robert Ssali', '+256702345678', 'DL/2020/002', 'DRV_ANON_002', TRUE),
    ('David Musoke', '+256703456789', 'DL/2020/003', 'DRV_ANON_003', TRUE),
    ('Francis Musinguzi', '+256704567890', 'DL/2020/004', 'DRV_ANON_004', TRUE),
    ('Michael Okello', '+256705678901', 'DL/2020/005', 'DRV_ANON_005', TRUE);

-- Insert sample vehicles
INSERT INTO vehicles (plate_number, driver_id, model, status, model_category) VALUES
    ('UBE 001', 1, 'Yamaha NMAX', 'active', 'scooter_standard'),
    ('UBE 002', 2, 'Honda PCX', 'active', 'scooter_premium'),
    ('UBE 003', 3, 'Yamaha Aerox', 'active', 'scooter_sport'),
    ('UBE 004', 4, 'Suzuki Burgman', 'active', 'scooter_cruiser'),
    ('UBE 005', 5, 'Kymco Like', 'active', 'scooter_classic');

-- Insert sample campus locations
INSERT INTO locations (name, latitude, longitude, zone, zone_type, safety_score, capacity) VALUES
    ('Main Library', 0.3336, 32.5656, 'Academic', 'academic', 0.9, 100),
    ('Freedom Square', 0.3342, 32.5671, 'Central', 'central', 0.85, 500),
    ('Engineering Block', 0.3351, 32.5634, 'Academic', 'academic', 0.88, 150),
    ('Mary Stuart Hall', 0.3328, 32.5689, 'Residential', 'residential', 0.92, 200),
    ('Central Teaching Facility', 0.3345, 32.5662, 'Academic', 'academic', 0.9, 300),
    ('Food Court', 0.3339, 32.5685, 'Commercial', 'commercial', 0.82, 100),
    ('Sports Complex', 0.3319, 32.5698, 'Recreation', 'recreation', 0.95, 500),
    ('Medical School', 0.3362, 32.5645, 'Academic', 'academic', 0.91, 200);

-- Insert sample routes
INSERT INTO routes (name, description, start_location_id, end_location_id, distance_km, estimated_duration_min, is_common_route, safety_score) VALUES
    ('Main Gate to Library', 'Primary route from main entrance to library', 1, 1, 0.8, 5, TRUE, 0.9),
    ('Engineering to Food Court', 'Route from engineering block to food court', 3, 6, 0.5, 3, TRUE, 0.85),
    ('Hall to Medical School', 'Route from Mary Stuart Hall to Medical School', 4, 8, 0.7, 4, TRUE, 0.88),
    ('Campus Circuit', 'Full circuit around main campus', 2, 2, 2.5, 15, FALSE, 0.87);

-- ============================================
-- VIEWS
-- ============================================

-- View to get telemetry with vehicle info
CREATE OR REPLACE VIEW telemetry_with_vehicle AS
SELECT 
    t.telemetry_id,
    t.vehicle_id,
    v.plate_number,
    d.name AS driver_name,
    t.latitude,
    t.longitude,
    t.speed,
    t.acceleration,
    t.engine_temp,
    t.timestamp,
    t.gps_accuracy,
    t.data_quality_score,
    t.is_validated
FROM telemetry t
JOIN vehicles v ON t.vehicle_id = v.vehicle_id
JOIN drivers d ON v.driver_id = d.driver_id;

-- View to get events with vehicle and driver info
CREATE OR REPLACE VIEW events_with_vehicle AS
SELECT
    e.event_id,
    e.vehicle_id,
    v.plate_number,
    d.name AS driver_name,
    e.event_type,
    e.latitude,
    e.longitude,
    e.speed,
    e.acceleration,
    e.timestamp,
    e.severity,
    e.confidence_score,
    e.ai_detected
FROM events e
JOIN vehicles v ON e.vehicle_id = v.vehicle_id
JOIN drivers d ON v.driver_id = d.driver_id;

-- View for telemetry with semantic context (FIXED - columns now exist in table)
CREATE OR REPLACE VIEW telemetry_with_semantic AS
SELECT
    t.telemetry_id,
    t.vehicle_id,
    v.plate_number,
    d.anonymized_id AS driver_anonymized_id,
    t.latitude,
    t.longitude,
    t.speed,
    t.acceleration,
    t.timestamp,
    t.gps_accuracy,
    t.data_quality_score,
    t.is_validated,
    t.semantic_context,
    t.map_matched,
    t.matched_location_id,
    t.match_confidence,
    t.provenance_id
FROM telemetry t
JOIN vehicles v ON t.vehicle_id = v.vehicle_id
LEFT JOIN drivers d ON v.driver_id = d.driver_id;

-- View for events with AI enhancements (FIXED - columns now exist in table)
CREATE OR REPLACE VIEW events_with_ai AS
SELECT
    e.event_id,
    e.vehicle_id,
    v.plate_number,
    d.anonymized_id AS driver_anonymized_id,
    e.event_type,
    e.latitude,
    e.longitude,
    e.speed,
    e.acceleration,
    e.timestamp,
    e.severity,
    e.confidence_score,
    e.explanation,
    e.causal_factors,
    e.ai_detected
FROM events e
JOIN vehicles v ON e.vehicle_id = v.vehicle_id
LEFT JOIN drivers d ON v.driver_id = d.driver_id;

-- View for active trips
CREATE OR REPLACE VIEW active_trips AS
SELECT
    t.trip_id,
    t.vehicle_id,
    v.plate_number,
    t.driver_id,
    d.anonymized_id AS driver_anonymized_id,
    t.route_id,
    r.name AS route_name,
    t.start_time,
    t.start_location_id,
    sl.name AS start_location_name,
    t.status
FROM trips t
JOIN vehicles v ON t.vehicle_id = v.vehicle_id
JOIN drivers d ON t.driver_id = d.driver_id
LEFT JOIN routes r ON t.route_id = r.route_id
LEFT JOIN locations sl ON t.start_location_id = sl.location_id
WHERE t.status = 'in_progress';

-- View for driver performance summary
CREATE OR REPLACE VIEW driver_performance_summary AS
SELECT
    dp.driver_id,
    d.anonymized_id,
    dp.date,
    dp.total_trips,
    dp.total_distance_km,
    dp.risk_score,
    dp.safety_score,
    dp.efficiency_score,
    dp.harsh_braking_count,
    dp.overspeed_count,
    dp.rapid_acceleration_count,
    dp.incidents_count
FROM driver_performance dp
JOIN drivers d ON dp.driver_id = d.driver_id
ORDER BY dp.date DESC, dp.risk_score ASC;

-- View for vehicle maintenance status
CREATE OR REPLACE VIEW vehicle_maintenance_status AS
SELECT
    vm.maintenance_id,
    vm.vehicle_id,
    v.plate_number,
    vm.maintenance_type,
    vm.scheduled_date,
    vm.completed_date,
    vm.status,
    vm.cost,
    vm.next_service_due,
    CASE 
        WHEN vm.status = 'overdue' THEN 'URGENT'
        WHEN vm.next_service_due IS NOT NULL AND vm.next_service_due < CURRENT_DATE THEN 'DUE SOON'
        ELSE 'OK'
    END AS urgency
FROM vehicle_maintenance vm
JOIN vehicles v ON vm.vehicle_id = v.vehicle_id
ORDER BY 
    CASE vm.status 
        WHEN 'overdue' THEN 1 
        WHEN 'in_progress' THEN 2 
        WHEN 'scheduled' THEN 3 
        ELSE 4 
    END;

-- View for weather impact analysis
CREATE OR REPLACE VIEW weather_event_correlation AS
SELECT
    DATE_TRUNC('hour', w.timestamp) AS hour_bucket,
    w.conditions,
    w.precipitation,
    w.wind_speed,
    COUNT(e.event_id) AS event_count,
    AVG(CASE WHEN e.severity = 'high' THEN 1 ELSE 0 END) AS high_severity_ratio,
    COUNT(DISTINCT e.vehicle_id) AS affected_vehicles
FROM weather w
LEFT JOIN events e ON DATE_TRUNC('hour', e.timestamp) = DATE_TRUNC('hour', w.timestamp)
GROUP BY DATE_TRUNC('hour', w.timestamp), w.conditions, w.precipitation, w.wind_speed
ORDER BY hour_bucket DESC;

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to populate time dimension table
CREATE OR REPLACE FUNCTION populate_time_dimension(start_date DATE, end_date DATE)
RETURNS VOID AS $$
DECLARE
    current_date DATE := start_date;
    current_timestamp TIMESTAMP;
    hour_int INTEGER;
    is_weekend_bool BOOLEAN;
    is_peak_bool BOOLEAN;
    peak_period_str VARCHAR(20);
    is_class_bool BOOLEAN;
BEGIN
    WHILE current_date <= end_date LOOP
        FOR hour_int IN 0..23 LOOP
            current_timestamp := current_date + (hour_int || ' hours')::INTERVAL;
            is_weekend_bool := EXTRACT(DOW FROM current_date) IN (0, 6);
            
            -- Peak hours: 7-9 AM and 4-6 PM on weekdays
            is_peak_bool := (
                (hour_int BETWEEN 7 AND 9) OR (hour_int BETWEEN 16 AND 18)
            ) AND NOT is_weekend_bool;
            
            peak_period_str := CASE 
                WHEN hour_int BETWEEN 7 AND 9 THEN 'morning_peak'
                WHEN hour_int BETWEEN 16 AND 18 THEN 'evening_peak'
                ELSE 'off_peak'
            END;
            
            -- Class time: 8 AM - 5 PM on weekdays during semester
            is_class_bool := (
                hour_int BETWEEN 8 AND 17
            ) AND NOT is_weekend_bool;
            
            INSERT INTO time_dimension (
                timestamp, date, time, hour, minute, day_of_week, day_name,
                day_of_month, day_of_year, week_of_year, month, month_name,
                quarter, year, is_weekend, is_peak_hour, peak_period, is_class_time
            ) VALUES (
                current_timestamp,
                current_date,
                LPAD(hour_int::TEXT, 2, '0') || ':00:00',
                hour_int,
                0,
                EXTRACT(DOW FROM current_date)::INTEGER,
                TO_CHAR(current_date, 'Day'),
                EXTRACT(DAY FROM current_date)::INTEGER,
                EXTRACT(DOY FROM current_date)::INTEGER,
                EXTRACT(WEEK FROM current_date)::INTEGER,
                EXTRACT(MONTH FROM current_date)::INTEGER,
                TO_CHAR(current_date, 'Month'),
                EXTRACT(QUARTER FROM current_date)::INTEGER,
                EXTRACT(YEAR FROM current_date)::INTEGER,
                is_weekend_bool,
                is_peak_bool,
                peak_period_str,
                is_class_bool
            ) ON CONFLICT (timestamp) DO NOTHING;
        END LOOP;
        current_date := current_date + INTERVAL '1 day';
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate driver risk score
CREATE OR REPLACE FUNCTION calculate_driver_risk_score(
    p_driver_id INTEGER,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    driver_id INTEGER,
    risk_score FLOAT,
    safety_score FLOAT,
    total_events INTEGER,
    harsh_braking INTEGER,
    overspeed INTEGER,
    rapid_acceleration INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.driver_id,
        COALESCE(
            (COUNT(CASE WHEN e.event_type = 'harsh_braking' THEN 1 END) * 2.0 +
             COUNT(CASE WHEN e.event_type = 'overspeed' THEN 1 END) * 1.5 +
             COUNT(CASE WHEN e.event_type = 'rapid_acceleration' THEN 1 END) * 1.0) /
            NULLIF(COUNT(DISTINCT DATE(e.timestamp)), 0),
            0.0
        )::FLOAT AS risk_score,
        GREATEST(0, 1.0 - (
            (COUNT(CASE WHEN e.event_type = 'harsh_braking' THEN 1 END) * 0.1 +
             COUNT(CASE WHEN e.event_type = 'overspeed' THEN 1 END) * 0.08 +
             COUNT(CASE WHEN e.event_type = 'rapid_acceleration' THEN 1 END) * 0.05) /
            NULLIF(COUNT(DISTINCT DATE(e.timestamp)), 0)
        ))::FLOAT AS safety_score,
        COUNT(e.event_id)::INTEGER AS total_events,
        COUNT(CASE WHEN e.event_type = 'harsh_braking' THEN 1 END)::INTEGER AS harsh_braking,
        COUNT(CASE WHEN e.event_type = 'overspeed' THEN 1 END)::INTEGER AS overspeed,
        COUNT(CASE WHEN e.event_type = 'rapid_acceleration' THEN 1 END)::INTEGER AS rapid_acceleration
    FROM drivers d
    LEFT JOIN vehicles v ON d.driver_id = v.driver_id
    LEFT JOIN events e ON v.vehicle_id = e.vehicle_id 
        AND e.timestamp >= p_start_date 
        AND e.timestamp <= p_end_date + INTERVAL '1 day'
    WHERE d.driver_id = p_driver_id
    GROUP BY d.driver_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- INITIALIZE TIME DIMENSION (2024-2026)
-- ============================================
SELECT populate_time_dimension('2024-01-01'::DATE, '2026-12-31'::DATE);