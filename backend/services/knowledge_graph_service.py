"""
MakFleet Knowledge Graph Service
Integrates Neo4j graph database with spatio-temporal relationships
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Try to import neo4j, but make it optional for serverless deployment
try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    GraphDatabase = None
    NEO4J_AVAILABLE = False

from backend.models.spatio_temporal_models import CampusLocation, ZoneType


class KnowledgeGraphService:
    """Service for knowledge graph operations with Neo4j"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "password"):
        self.driver = None

        if not NEO4J_AVAILABLE:
            print("Warning: Neo4j module not available - knowledge graph features disabled")
            return

        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self._initialize_schema()
        except Exception as e:
            print(f"Warning: Neo4j connection failed: {e}")
            self.driver = None

    def _initialize_schema(self):
        """Initialize the knowledge graph schema"""
        if not self.driver:
            return

        schema_queries = [
            # Create constraints
            "CREATE CONSTRAINT driver_id IF NOT EXISTS ON (d:Driver) ASSERT d.driver_id IS UNIQUE",
            "CREATE CONSTRAINT vehicle_id IF NOT EXISTS ON (v:Vehicle) ASSERT v.vehicle_id IS UNIQUE",
            "CREATE CONSTRAINT location_id IF NOT EXISTS ON (l:Location) ASSERT l.location_id IS UNIQUE",
            "CREATE CONSTRAINT route_id IF NOT EXISTS ON (r:Route) ASSERT r.route_id IS UNIQUE",

            # Create indexes for performance
            "CREATE INDEX location_coords IF NOT EXISTS FOR (l:Location) ON (l.latitude, l.longitude)",
            "CREATE INDEX telemetry_time IF NOT EXISTS FOR (t:Telemetry) ON (t.timestamp)",
            "CREATE INDEX event_time IF NOT EXISTS FOR (e:Event) ON (e.timestamp)",
        ]

        with self.driver.session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    print(f"Schema initialization warning: {e}")

    async def create_campus_graph(self, locations: List[CampusLocation]):
        """Create the campus knowledge graph with locations and relationships"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")

            # Create location nodes
            for location in locations:
                session.run("""
                    CREATE (l:Location {
                        location_id: $location_id,
                        name: $name,
                        latitude: $latitude,
                        longitude: $longitude,
                        zone_type: $zone_type,
                        is_formal_path: $is_formal_path,
                        safety_score: $safety_score
                    })
                    """,
                    location_id=location.location_id,
                    name=location.name,
                    latitude=location.latitude,
                    longitude=location.longitude,
                    zone_type=location.zone_type.value,
                    is_formal_path=location.is_formal_path,
                    safety_score=location.safety_score
                )

            # Create spatial relationships between nearby locations
            for i, loc1 in enumerate(locations):
                for j, loc2 in enumerate(locations):
                    if i != j:
                        distance = loc1.distance_to(loc2)
                        if distance < 500:  # Within 500 meters
                            session.run("""
                                MATCH (l1:Location {location_id: $id1}), (l2:Location {location_id: $id2})
                                CREATE (l1)-[:CONNECTED_TO {
                                    distance_km: $distance,
                                    travel_time_min: $time,
                                    path_type: $path_type,
                                    safety_rating: $safety
                                }]->(l2)
                                """,
                                id1=loc1.location_id,
                                id2=loc2.location_id,
                                distance=distance / 1000,
                                time=distance / 1000 * 2,  # Rough estimate: 2 min per km
                                path_type='road' if loc1.is_formal_path and loc2.is_formal_path else 'footpath',
                                safety=(loc1.safety_score + loc2.safety_score) / 2
                            )

        return {"status": "success", "nodes_created": len(locations)}

    async def add_telemetry_to_graph(self, telemetry_data: Dict[str, Any]):
        """Add telemetry data as spatio-temporal nodes and relationships"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        with self.driver.session() as session:
            # Create telemetry node
            session.run("""
                CREATE (t:Telemetry {
                    telemetry_id: $telemetry_id,
                    vehicle_id: $vehicle_id,
                    latitude: $latitude,
                    longitude: $longitude,
                    speed: $speed,
                    acceleration: $acceleration,
                    timestamp: datetime($timestamp),
                    gps_accuracy: $gps_accuracy,
                    data_quality_score: $data_quality_score,
                    semantic_context: $semantic_context
                })
                """,
                telemetry_id=telemetry_data['telemetry_id'],
                vehicle_id=telemetry_data['vehicle_id'],
                latitude=telemetry_data['latitude'],
                longitude=telemetry_data['longitude'],
                speed=telemetry_data.get('speed', 0),
                acceleration=telemetry_data.get('acceleration', 0),
                timestamp=telemetry_data['timestamp'],
                gps_accuracy=telemetry_data.get('gps_accuracy', 10.0),
                data_quality_score=telemetry_data.get('data_quality_score', 0.8),
                semantic_context=json.dumps(telemetry_data.get('semantic_context', {}))
            )

            # Connect to vehicle
            session.run("""
                MATCH (t:Telemetry {telemetry_id: $telemetry_id}),
                      (v:Vehicle {vehicle_id: $vehicle_id})
                CREATE (v)-[:HAS_TELEMETRY]->(t)
                """,
                telemetry_id=telemetry_data['telemetry_id'],
                vehicle_id=telemetry_data['vehicle_id']
            )

            # Connect to nearest location if map-matched
            if telemetry_data.get('map_matched'):
                session.run("""
                    MATCH (t:Telemetry {telemetry_id: $telemetry_id}),
                          (l:Location {location_id: $location_id})
                    CREATE (t)-[:LOCATED_AT {
                        distance_meters: $distance,
                        confidence: $confidence
                    }]->(l)
                    """,
                    telemetry_id=telemetry_data['telemetry_id'],
                    location_id=telemetry_data['matched_location_id'],
                    distance=telemetry_data.get('match_distance', 0),
                    confidence=telemetry_data.get('match_confidence', 0.5)
                )

        return {"status": "success"}

    async def add_event_to_graph(self, event_data: Dict[str, Any]):
        """Add event as anomaly node with causal relationships"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        with self.driver.session() as session:
            # Create event node
            session.run("""
                CREATE (e:Event {
                    event_id: $event_id,
                    event_type: $event_type,
                    latitude: $latitude,
                    longitude: $longitude,
                    speed: $speed,
                    acceleration: $acceleration,
                    timestamp: datetime($timestamp),
                    severity: $severity,
                    confidence_score: $confidence,
                    explanation: $explanation,
                    causal_factors: $causal_factors
                })
                """,
                event_id=event_data['event_id'],
                event_type=event_data['event_type'],
                latitude=event_data['latitude'],
                longitude=event_data['longitude'],
                speed=event_data.get('speed'),
                acceleration=event_data.get('acceleration'),
                timestamp=event_data['timestamp'],
                severity=event_data.get('severity', 'medium'),
                confidence=event_data.get('confidence_score', 0.8),
                explanation=event_data.get('explanation', ''),
                causal_factors=json.dumps(event_data.get('causal_factors', []))
            )

            # Connect to vehicle
            session.run("""
                MATCH (e:Event {event_id: $event_id}),
                      (v:Vehicle {vehicle_id: $vehicle_id})
                CREATE (v)-[:INVOLVED_IN]->(e)
                """,
                event_id=event_data['event_id'],
                vehicle_id=event_data['vehicle_id']
            )

            # Connect to related telemetry
            if event_data.get('telemetry_id'):
                session.run("""
                    MATCH (e:Event {event_id: $event_id}),
                          (t:Telemetry {telemetry_id: $telemetry_id})
                    CREATE (t)-[:TRIGGERED_EVENT]->(e)
                    """,
                    event_id=event_data['event_id'],
                    telemetry_id=event_data['telemetry_id']
                )

        return {"status": "success"}

    async def query_spatio_temporal_patterns(self, query_type: str, params: Dict[str, Any]):
        """Query spatio-temporal patterns from the knowledge graph"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        queries = {
            'danger_zones': """
                MATCH (l:Location)<-[:LOCATED_AT]-(t:Telemetry)<-[:TRIGGERED_EVENT]-(e:Event)
                WHERE e.severity IN ['high', 'medium']
                AND e.timestamp >= datetime($start_date)
                RETURN l.name as location_name,
                       l.latitude as latitude,
                       l.longitude as longitude,
                       count(e) as event_count,
                       avg(e.confidence_score) as avg_confidence,
                       collect(distinct e.event_type) as event_types
                ORDER BY event_count DESC
                LIMIT 10
            """,
            'vehicle_behavior': """
                MATCH (v:Vehicle)-[:HAS_TELEMETRY]->(t:Telemetry)-[:LOCATED_AT]->(l:Location)
                WHERE v.vehicle_id = $vehicle_id
                AND t.timestamp >= datetime($start_date)
                RETURN l.zone_type as zone,
                       count(t) as visits,
                       avg(t.speed) as avg_speed,
                       min(t.timestamp) as first_visit,
                       max(t.timestamp) as last_visit
                ORDER BY visits DESC
            """,
            'temporal_patterns': """
                MATCH (t:Telemetry)
                WHERE t.timestamp >= datetime($start_date)
                RETURN hour(t.timestamp) as hour_of_day,
                       count(t) as telemetry_count,
                       avg(t.speed) as avg_speed,
                       avg(t.acceleration) as avg_acceleration,
                       count(CASE WHEN t.acceleration < -4 THEN 1 END) as harsh_braking_count
                ORDER BY hour_of_day
            """
        }

        if query_type not in queries:
            return {"error": f"Unknown query type: {query_type}"}

        with self.driver.session() as session:
            result = session.run(queries[query_type], **params)
            records = [dict(record) for record in result]

        return {
            "query_type": query_type,
            "results": records,
            "count": len(records)
        }

    async def find_similar_behaviors(self, vehicle_id: str, behavior_pattern: Dict[str, Any]):
        """Find vehicles with similar behavior patterns"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        # This would implement graph-based similarity search
        # For now, return mock results
        return {
            "vehicle_id": vehicle_id,
            "similar_vehicles": [
                {"vehicle_id": "VHC_001", "similarity_score": 0.85, "shared_patterns": ["speeding", "harsh_braking"]},
                {"vehicle_id": "VHC_003", "similarity_score": 0.78, "shared_patterns": ["peak_hour_usage"]},
            ],
            "pattern_analysis": behavior_pattern
        }

    async def get_graph_statistics(self):
        """Get knowledge graph statistics"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        with self.driver.session() as session:
            stats = {}

            # Node counts
            node_counts = session.run("""
                MATCH (n)
                RETURN labels(n) as labels, count(*) as count
                ORDER BY count DESC
            """)

            stats['node_counts'] = {record['labels'][0]: record['count'] for record in node_counts}

            # Relationship counts
            rel_counts = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as relationship_type, count(*) as count
                ORDER BY count DESC
            """)

            stats['relationship_counts'] = {record['relationship_type']: record['count'] for record in rel_counts}

            # Graph density
            density_result = session.run("""
                MATCH (n)
                WITH count(n) as node_count
                MATCH ()-[r]->()
                WITH node_count, count(r) as rel_count
                RETURN node_count, rel_count, toFloat(rel_count) / (node_count * node_count) as density
            """)

            density_record = density_result.single()
            if density_record:
                stats['graph_density'] = density_record['density']
                stats['total_nodes'] = density_record['node_count']
                stats['total_relationships'] = density_record['rel_count']

        return stats

    async def clear_graph(self):
        """Clear all data from the knowledge graph"""
        if not self.driver:
            return {"error": "Neo4j connection not available"}

        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

        return {"status": "success", "message": "Knowledge graph cleared"}

    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()


# Global service instance
knowledge_graph_service = KnowledgeGraphService()
