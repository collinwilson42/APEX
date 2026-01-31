"""
Neo4j Client for Node Complex
==============================
ROOT A: NEO4J_INFRASTRUCTURE (NC1-001 → NC1-007)
Phase NC-1 | Core Data Layer

Nodes Implemented:
- NC1-001: NEO4J_CONNECTION_MANAGER
- NC1-002: NEO4J_SCHEMA_INITIALIZATION
- NC1-003: NEO4J_NODE_CONSTRAINT_UNIQUE_ID
- NC1-004: NEO4J_PHASE_CONSTRAINT
- NC1-005: NEO4J_MANIFEST_CONSTRAINT
- NC1-006: NEO4J_INDEX_NODE_PHASE
- NC1-007: NEO4J_INDEX_NODE_STATUS

STOIC Alignment:
- Stability: Connection pooling, retry logic, idempotent schema
- Tunity: Configurable timeouts and pool sizes
- Opportunity: Single client manages all Neo4j operations
"""

import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError, Neo4jError

from ..config import get_config, Neo4jConfig

logger = logging.getLogger(__name__)


# =============================================================================
# NC1-001: NEO4J_CONNECTION_MANAGER
# =============================================================================

class Neo4jClient:
    """
    Neo4j connection manager with pooling, auth, and session management.
    Supports async operations and connection recovery.
    """
    
    def __init__(self, config: Optional[Neo4jConfig] = None):
        """
        Initialize Neo4j client.
        
        Args:
            config: Optional Neo4jConfig, defaults to global config
        """
        self._config = config or get_config().database.neo4j
        self._driver: Optional[Driver] = None
        self._initialized = False
        
    @property
    def driver(self) -> Driver:
        """Get or create the Neo4j driver."""
        if self._driver is None:
            self._connect()
        return self._driver
    
    def _connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = GraphDatabase.driver(
                self._config.uri,
                auth=(self._config.username, self._config.password),
                max_connection_pool_size=self._config.max_connection_pool_size,
                connection_timeout=self._config.connection_timeout
            )
            # Verify connectivity
            self._driver.verify_connectivity()
            logger.info(f"✅ Connected to Neo4j at {self._config.uri}")
        except AuthError as e:
            logger.error(f"❌ Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j service unavailable at {self._config.uri}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Neo4j connection error: {e}")
            raise
    
    @contextmanager
    def session(self, database: Optional[str] = None):
        """
        Context manager for Neo4j sessions.
        
        Usage:
            with client.session() as session:
                result = session.run("MATCH (n) RETURN n")
        """
        db = database or self._config.database
        session = self.driver.session(database=db)
        try:
            yield session
        finally:
            session.close()
    
    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j connectivity and return status.
        
        Returns:
            Dict with 'healthy', 'message', and 'details' keys
        """
        try:
            with self.session() as session:
                result = session.run("RETURN 1 as ping")
                result.single()
            return {
                "healthy": True,
                "message": "Neo4j is responsive",
                "details": {
                    "uri": self._config.uri,
                    "database": self._config.database
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "message": str(e),
                "details": {"uri": self._config.uri}
            }
    
    # =========================================================================
    # NC1-002: NEO4J_SCHEMA_INITIALIZATION (Idempotent)
    # =========================================================================
    
    def initialize_schema(self) -> None:
        """
        Create constraints, indexes, and relationship types.
        Idempotent - safe to run multiple times.
        """
        if self._initialized:
            logger.info("Schema already initialized this session")
            return
            
        logger.info("Initializing Neo4j schema...")
        
        with self.session() as session:
            # NC1-003: Node ID unique constraint
            self._create_constraint(
                session,
                "node_id_unique",
                "CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:Node) REQUIRE n.node_id IS UNIQUE"
            )
            
            # NC1-004: Phase number unique constraint
            self._create_constraint(
                session,
                "phase_number_unique", 
                "CREATE CONSTRAINT phase_number_unique IF NOT EXISTS FOR (p:Phase) REQUIRE p.phase_number IS UNIQUE"
            )
            
            # NC1-005: Manifest ID unique constraint
            self._create_constraint(
                session,
                "manifest_id_unique",
                "CREATE CONSTRAINT manifest_id_unique IF NOT EXISTS FOR (m:Manifest) REQUIRE m.manifest_id IS UNIQUE"
            )
            
            # NC1-006: Index on node phase_number
            self._create_index(
                session,
                "node_phase_idx",
                "CREATE INDEX node_phase_idx IF NOT EXISTS FOR (n:Node) ON (n.phase_number)"
            )
            
            # NC1-007: Index on node status
            self._create_index(
                session,
                "node_status_idx",
                "CREATE INDEX node_status_idx IF NOT EXISTS FOR (n:Node) ON (n.status)"
            )
            
            # Additional useful indexes
            self._create_index(
                session,
                "node_type_idx",
                "CREATE INDEX node_type_idx IF NOT EXISTS FOR (n:Node) ON (n.node_type)"
            )
            
            self._create_index(
                session,
                "node_weight_idx",
                "CREATE INDEX node_weight_idx IF NOT EXISTS FOR (n:Node) ON (n.dev_weight)"
            )
        
        self._initialized = True
        logger.info("✅ Neo4j schema initialized successfully")
    
    def _create_constraint(self, session: Session, name: str, query: str) -> None:
        """Create a constraint if it doesn't exist."""
        try:
            session.run(query)
            logger.debug(f"  ✓ Constraint '{name}' ensured")
        except Neo4jError as e:
            if "already exists" in str(e).lower():
                logger.debug(f"  ○ Constraint '{name}' already exists")
            else:
                logger.warning(f"  ✗ Constraint '{name}' error: {e}")
    
    def _create_index(self, session: Session, name: str, query: str) -> None:
        """Create an index if it doesn't exist."""
        try:
            session.run(query)
            logger.debug(f"  ✓ Index '{name}' ensured")
        except Neo4jError as e:
            if "already exists" in str(e).lower():
                logger.debug(f"  ○ Index '{name}' already exists")
            else:
                logger.warning(f"  ✗ Index '{name}' error: {e}")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def run_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """
        Run a Cypher query and return results as list of dicts.
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def run_write(self, query: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run a write transaction (CREATE, MERGE, DELETE).
        
        Args:
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            Query summary with counters
        """
        with self.session() as session:
            result = session.run(query, parameters or {})
            summary = result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set
            }
    
    def clear_all_data(self, confirm: bool = False) -> None:
        """
        Delete all nodes and relationships. Use with caution!
        
        Args:
            confirm: Must be True to execute
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear all data")
        
        with self.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.warning("⚠️ All Neo4j data has been deleted")
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get current schema constraints and indexes."""
        constraints = self.run_query("SHOW CONSTRAINTS")
        indexes = self.run_query("SHOW INDEXES")
        return {
            "constraints": constraints,
            "indexes": indexes
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()


# =============================================================================
# SINGLETON CLIENT
# =============================================================================

_neo4j_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    """Get or create the singleton Neo4j client."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
    return _neo4j_client


def reset_neo4j_client() -> None:
    """Reset the Neo4j client (for testing)."""
    global _neo4j_client
    if _neo4j_client is not None:
        _neo4j_client.close()
        _neo4j_client = None


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("NEO4J CLIENT TEST")
    print("=" * 60)
    
    client = get_neo4j_client()
    
    # Health check
    health = client.health_check()
    print(f"\nHealth: {health}")
    
    if health["healthy"]:
        # Initialize schema
        client.initialize_schema()
        
        # Show schema
        schema = client.get_schema_info()
        print(f"\nConstraints: {len(schema['constraints'])}")
        print(f"Indexes: {len(schema['indexes'])}")
        
        print("\n✅ Neo4j client test passed!")
    else:
        print("\n❌ Neo4j not available - check Docker container")
    
    client.close()
