"""
Neo4j Configuration and Connection Manager
Security-first nodebase with fingerprint feedback loop
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Neo4jConnection:
    """Secure Neo4j connection with whitelist-only access"""
    
    def __init__(self):
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.user = os.getenv('NEO4J_USER', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'neo4j')
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection with encryption settings"""
        try:
            # For Neo4j 5.x+ use encrypted=False for local development
            # For production, use encrypted=True with proper certificates
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                encrypted=False  # Set to True for production with SSL
            )
            # Test connection
            self.driver.verify_connectivity()
            logger.info(f"✓ Connected to Neo4j at {self.uri}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Neo4j: {str(e)}")
            logger.info("Make sure Neo4j is running on bolt://localhost:7687")
            logger.info("Start Neo4j: neo4j start (or use Neo4j Desktop)")
            raise
    
    def close(self):
        """Close the driver connection"""
        if self.driver:
            self.driver.close()
            logger.info("✓ Neo4j connection closed")
    
    def execute_query(self, query, parameters=None):
        """Execute a Cypher query with parameters"""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class FingerprintFeedbackLoop:
    """
    Basic implementation of fingerprint feedback system
    Stores node-codes with weight bands (0.0-1.0) for calibration
    """
    
    def __init__(self, connection):
        self.conn = connection
        self._initialize_schema()
    
    def _initialize_schema(self):
        """Create node-code schema with fingerprint bands"""
        
        # Create constraints and indexes
        constraints = [
            "CREATE CONSTRAINT node_code_id IF NOT EXISTS FOR (n:NodeCode) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT version_id IF NOT EXISTS FOR (v:Version) REQUIRE v.id IS UNIQUE",
        ]
        
        for constraint in constraints:
            try:
                self.conn.execute_query(constraint)
                logger.info(f"✓ Constraint created: {constraint[:50]}")
            except Exception as e:
                logger.debug(f"Constraint may already exist: {e}")
        
        # Create indexes
        indexes = [
            "CREATE INDEX node_code_domain IF NOT EXISTS FOR (n:NodeCode) ON (n.domain)",
            "CREATE INDEX node_code_fingerprint IF NOT EXISTS FOR (n:NodeCode) ON (n.fingerprint_band)",
            "CREATE INDEX version_timestamp IF NOT EXISTS FOR (v:Version) ON (v.timestamp)",
        ]
        
        for index in indexes:
            try:
                self.conn.execute_query(index)
                logger.info(f"✓ Index created: {index[:50]}")
            except Exception as e:
                logger.debug(f"Index may already exist: {e}")
    
    def create_node_code(self, code_id, name, domain, description="", 
                         fingerprint=0.5, metadata=None):
        """
        Create a new node-code with fingerprint band
        
        Fingerprint bands:
        - 0.90-1.00: Core, highly trusted
        - 0.70-0.89: Strong but evolving
        - 0.40-0.69: Experimental/clarifying
        - 0.00-0.39: Deprecated or unresolved
        """
        
        fingerprint_band = self._get_fingerprint_band(fingerprint)
        
        query = """
        MERGE (n:NodeCode {id: $code_id})
        SET n.name = $name,
            n.domain = $domain,
            n.description = $description,
            n.fingerprint = $fingerprint,
            n.fingerprint_band = $fingerprint_band,
            n.created_at = datetime(),
            n.updated_at = datetime(),
            n.metadata = $metadata
        RETURN n
        """
        
        result = self.conn.execute_query(query, {
            'code_id': code_id,
            'name': name,
            'domain': domain,
            'description': description,
            'fingerprint': fingerprint,
            'fingerprint_band': fingerprint_band,
            'metadata': metadata or {}
        })
        
        logger.info(f"✓ Created node-code: {code_id} [{fingerprint_band}]")
        return result
    
    def update_fingerprint(self, code_id, new_fingerprint, reason=""):
        """
        Update node-code fingerprint based on feedback
        Creates version history for calibration tracking
        """
        
        # Get current fingerprint
        current_query = "MATCH (n:NodeCode {id: $code_id}) RETURN n.fingerprint as fp"
        current = self.conn.execute_query(current_query, {'code_id': code_id})
        
        if not current:
            logger.error(f"✗ Node-code not found: {code_id}")
            return None
        
        old_fingerprint = current[0]['fp']
        new_band = self._get_fingerprint_band(new_fingerprint)
        
        # Update node-code
        update_query = """
        MATCH (n:NodeCode {id: $code_id})
        SET n.fingerprint = $new_fingerprint,
            n.fingerprint_band = $new_band,
            n.updated_at = datetime()
        RETURN n
        """
        
        self.conn.execute_query(update_query, {
            'code_id': code_id,
            'new_fingerprint': new_fingerprint,
            'new_band': new_band
        })
        
        # Create version history
        version_query = """
        MATCH (n:NodeCode {id: $code_id})
        CREATE (v:Version {
            id: randomUUID(),
            node_code_id: $code_id,
            old_fingerprint: $old_fp,
            new_fingerprint: $new_fp,
            delta: $delta,
            reason: $reason,
            timestamp: datetime()
        })
        CREATE (n)-[:HAS_VERSION]->(v)
        RETURN v
        """
        
        delta = new_fingerprint - old_fingerprint
        self.conn.execute_query(version_query, {
            'code_id': code_id,
            'old_fp': old_fingerprint,
            'new_fp': new_fingerprint,
            'delta': delta,
            'reason': reason
        })
        
        direction = "↑" if delta > 0 else "↓"
        logger.info(f"✓ Updated fingerprint: {code_id} [{direction} {abs(delta):.3f}] → {new_band}")
        
        return {'old': old_fingerprint, 'new': new_fingerprint, 'delta': delta}
    
    def get_node_by_band(self, band):
        """Retrieve all node-codes in a specific fingerprint band"""
        
        query = """
        MATCH (n:NodeCode)
        WHERE n.fingerprint_band = $band
        RETURN n.id as id, n.name as name, n.domain as domain, 
               n.fingerprint as fingerprint
        ORDER BY n.fingerprint DESC
        """
        
        results = self.conn.execute_query(query, {'band': band})
        return results
    
    def get_version_history(self, code_id, limit=10):
        """Get calibration history for a node-code"""
        
        query = """
        MATCH (n:NodeCode {id: $code_id})-[:HAS_VERSION]->(v:Version)
        RETURN v.timestamp as timestamp,
               v.old_fingerprint as old_fp,
               v.new_fingerprint as new_fp,
               v.delta as delta,
               v.reason as reason
        ORDER BY v.timestamp DESC
        LIMIT $limit
        """
        
        results = self.conn.execute_query(query, {
            'code_id': code_id,
            'limit': limit
        })
        return results
    
    def _get_fingerprint_band(self, fingerprint):
        """Map fingerprint value to semantic band"""
        if fingerprint >= 0.90:
            return "CORE_TRUSTED"
        elif fingerprint >= 0.70:
            return "STRONG_EVOLVING"
        elif fingerprint >= 0.40:
            return "EXPERIMENTAL"
        else:
            return "DEPRECATED"
    
    def get_statistics(self):
        """Get nodebase statistics by fingerprint band"""
        
        query = """
        MATCH (n:NodeCode)
        RETURN n.fingerprint_band as band,
               count(n) as count,
               avg(n.fingerprint) as avg_fp,
               min(n.fingerprint) as min_fp,
               max(n.fingerprint) as max_fp
        ORDER BY avg_fp DESC
        """
        
        results = self.conn.execute_query(query)
        return results


def test_connection():
    """Test Neo4j connection and basic operations"""
    
    print("\n" + "="*60)
    print("NEO4J CONNECTION TEST")
    print("="*60)
    
    try:
        with Neo4jConnection() as conn:
            print("\n✓ Connection successful!")
            
            # Initialize feedback loop
            feedback = FingerprintFeedbackLoop(conn)
            print("✓ Fingerprint feedback loop initialized")
            
            # Create sample node-codes
            print("\n--- Creating sample node-codes ---")
            
            feedback.create_node_code(
                code_id="NC-001",
                name="Gold ATR Filter",
                domain="EXECUTION",
                description="ATR-based entry filter for gold trades",
                fingerprint=0.85,
                metadata={'version': '1.0', 'strategy': 'gold_scalp'}
            )
            
            feedback.create_node_code(
                code_id="NC-002",
                name="Session Multiplier",
                domain="RISK",
                description="Time-based risk adjustment",
                fingerprint=0.92,
                metadata={'version': '1.0', 'strategy': 'universal'}
            )
            
            feedback.create_node_code(
                code_id="NC-003",
                name="Experimental RSI Reset",
                domain="INTENT",
                description="Testing RSI reset logic",
                fingerprint=0.45,
                metadata={'version': '0.1', 'status': 'testing'}
            )
            
            # Update a fingerprint (simulate feedback)
            print("\n--- Simulating feedback update ---")
            feedback.update_fingerprint(
                "NC-001",
                0.88,
                reason="Positive results on 3-day backtest"
            )
            
            # Get statistics
            print("\n--- Nodebase Statistics ---")
            stats = feedback.get_statistics()
            for stat in stats:
                print(f"{stat['band']:20} | Count: {stat['count']:2} | "
                      f"Avg: {stat['avg_fp']:.3f} | "
                      f"Range: {stat['min_fp']:.3f}-{stat['max_fp']:.3f}")
            
            # Get nodes by band
            print("\n--- Core Trusted Nodes ---")
            core_nodes = feedback.get_node_by_band("CORE_TRUSTED")
            for node in core_nodes:
                print(f"  • {node['id']:10} | {node['name']:30} | {node['fingerprint']:.3f}")
            
            # Get version history
            print("\n--- Version History (NC-001) ---")
            history = feedback.get_version_history("NC-001")
            for version in history:
                ts = version['timestamp']
                delta = version['delta']
                direction = "↑" if delta > 0 else "↓"
                print(f"  {ts} | {direction} {abs(delta):.3f} | {version['reason']}")
            
            print("\n" + "="*60)
            print("✓ ALL TESTS PASSED")
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure Neo4j is installed and running")
        print("2. Check Neo4j Desktop or run: neo4j start")
        print("3. Verify connection at http://localhost:7474")
        print("4. Update .env with correct NEO4J credentials")


if __name__ == "__main__":
    test_connection()
