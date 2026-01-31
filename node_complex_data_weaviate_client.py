"""
Weaviate Client for Node Complex
=================================
ROOT B: WEAVIATE_INFRASTRUCTURE (NC1-008 → NC1-019)
Phase NC-1 | Core Data Layer

Nodes Implemented:
- NC1-008: WEAVIATE_CONNECTION_MANAGER
- NC1-009: WEAVIATE_SCHEMA_INITIALIZATION
- NC1-010: WEAVIATE_VECTORIZER_CONFIG
- NC1-011 → NC1-019: Property definitions

STOIC Alignment:
- Stability: Health checks, schema verification
- Tunity: Configurable vectorizer, timeouts
- Opportunity: Semantic search foundation
"""

import logging
from typing import Optional, List, Dict, Any

import weaviate
from weaviate.exceptions import WeaviateBaseError

from ..config import get_config, WeaviateConfig

logger = logging.getLogger(__name__)


# =============================================================================
# NC1-008: WEAVIATE_CONNECTION_MANAGER
# =============================================================================

class WeaviateClient:
    """
    Weaviate connection manager with health checks and schema verification.
    Supports both local and cloud endpoints.
    """
    
    def __init__(self, config: Optional[WeaviateConfig] = None):
        """
        Initialize Weaviate client.
        
        Args:
            config: Optional WeaviateConfig, defaults to global config
        """
        self._config = config or get_config().database.weaviate
        self._client: Optional[weaviate.Client] = None
        self._initialized = False
    
    @property
    def client(self) -> weaviate.Client:
        """Get or create the Weaviate client."""
        if self._client is None:
            self._connect()
        return self._client
    
    def _connect(self) -> None:
        """Establish connection to Weaviate."""
        try:
            self._client = weaviate.Client(
                url=self._config.url,
                timeout_config=(self._config.timeout, self._config.timeout)
            )
            # Verify connectivity
            if self._client.is_ready():
                logger.info(f"✅ Connected to Weaviate at {self._config.url}")
            else:
                raise ConnectionError("Weaviate not ready")
        except Exception as e:
            logger.error(f"❌ Weaviate connection error: {e}")
            raise
    
    def close(self) -> None:
        """Close the Weaviate client connection."""
        # Weaviate Python client doesn't require explicit close
        self._client = None
        logger.info("Weaviate connection closed")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Weaviate connectivity and return status.
        
        Returns:
            Dict with 'healthy', 'message', and 'details' keys
        """
        try:
            if self.client.is_ready():
                meta = self.client.get_meta()
                return {
                    "healthy": True,
                    "message": "Weaviate is responsive",
                    "details": {
                        "url": self._config.url,
                        "version": meta.get("version", "unknown"),
                        "modules": list(meta.get("modules", {}).keys())
                    }
                }
            else:
                return {
                    "healthy": False,
                    "message": "Weaviate not ready",
                    "details": {"url": self._config.url}
                }
        except Exception as e:
            return {
                "healthy": False,
                "message": str(e),
                "details": {"url": self._config.url}
            }
    
    # =========================================================================
    # NC1-009: WEAVIATE_SCHEMA_INITIALIZATION
    # NC1-010: WEAVIATE_VECTORIZER_CONFIG
    # NC1-011 → NC1-019: Property definitions
    # =========================================================================
    
    def initialize_schema(self) -> None:
        """
        Create DevelopmentNode class with vectorizer config.
        Handles schema evolution gracefully (idempotent).
        """
        if self._initialized:
            logger.info("Schema already initialized this session")
            return
        
        class_name = self._config.node_class_name
        
        # Check if class exists
        if self.client.schema.exists(class_name):
            logger.info(f"  ○ Class '{class_name}' already exists")
            self._initialized = True
            return
        
        logger.info(f"Creating Weaviate schema for '{class_name}'...")
        
        # NC1-010: Vectorizer config (text2vec-transformers)
        # NC1-011 → NC1-019: Property definitions
        class_schema = {
            "class": class_name,
            "description": "A code-node or tree-node in the development pyramid",
            "vectorizer": self._config.vectorizer_module,
            "moduleConfig": {
                self._config.vectorizer_module: {
                    "vectorizeClassName": False
                }
            },
            "properties": [
                # NC1-011: node_id
                {
                    "name": "node_id",
                    "dataType": ["text"],
                    "description": "Unique identifier (e.g., NC1-001, P4-023)",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": True  # Don't vectorize IDs
                        }
                    }
                },
                # NC1-012: title
                {
                    "name": "title",
                    "dataType": ["text"],
                    "description": "ALL_CAPS_TITLE format",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": False  # Vectorize titles
                        }
                    }
                },
                # NC1-013: dev_spec (vectorized for semantic search)
                {
                    "name": "dev_spec",
                    "dataType": ["text"],
                    "description": "Development specification - primary vectorized content",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": False  # Primary semantic content
                        }
                    }
                },
                # NC1-014: dev_weight
                {
                    "name": "dev_weight",
                    "dataType": ["number"],
                    "description": "Friction weight (-0.999 to -0.001)"
                },
                # NC1-015: phase_number
                {
                    "name": "phase_number",
                    "dataType": ["int"],
                    "description": "Which phase this node belongs to"
                },
                # NC1-016: parent_id
                {
                    "name": "parent_id",
                    "dataType": ["text"],
                    "description": "Parent node ID (null for roots)",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": True
                        }
                    }
                },
                # NC1-017: node_type
                {
                    "name": "node_type",
                    "dataType": ["text"],
                    "description": "root | branch | leaf | orphan",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": True
                        }
                    }
                },
                # NC1-018: status
                {
                    "name": "status",
                    "dataType": ["text"],
                    "description": "draft | active | complete | archived",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": True
                        }
                    }
                },
                # NC1-019: full_content (for vision model)
                {
                    "name": "full_content",
                    "dataType": ["text"],
                    "description": "Complete node content for vision model exposure",
                    "moduleConfig": {
                        self._config.vectorizer_module: {
                            "skip": False  # Vectorize for deep search
                        }
                    }
                },
                # Additional properties for positioning
                {
                    "name": "position_x",
                    "dataType": ["number"],
                    "description": "X coordinate in 3D space"
                },
                {
                    "name": "position_y",
                    "dataType": ["number"],
                    "description": "Y coordinate (depth/height)"
                },
                {
                    "name": "position_z",
                    "dataType": ["number"],
                    "description": "Z coordinate in 3D space"
                },
                {
                    "name": "layer",
                    "dataType": ["int"],
                    "description": "Tree layer (0-6 based on weight)"
                },
                {
                    "name": "family_weight",
                    "dataType": ["number"],
                    "description": "Aggregate weight of root + children"
                }
            ]
        }
        
        try:
            self.client.schema.create_class(class_schema)
            logger.info(f"  ✓ Class '{class_name}' created successfully")
            self._initialized = True
        except WeaviateBaseError as e:
            if "already exists" in str(e).lower():
                logger.info(f"  ○ Class '{class_name}' already exists")
                self._initialized = True
            else:
                logger.error(f"  ✗ Schema creation error: {e}")
                raise
    
    # =========================================================================
    # CRUD OPERATIONS (Foundation for ROOT D-G in next stage)
    # =========================================================================
    
    def add_node(self, node_data: Dict[str, Any]) -> str:
        """
        Add a node to Weaviate.
        
        Args:
            node_data: Dictionary with node properties
            
        Returns:
            Weaviate UUID of created object
        """
        class_name = self._config.node_class_name
        uuid = self.client.data_object.create(
            data_object=node_data,
            class_name=class_name
        )
        logger.debug(f"Created node in Weaviate: {node_data.get('node_id')}")
        return uuid
    
    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by its node_id.
        
        Args:
            node_id: The node identifier (e.g., "NC1-001")
            
        Returns:
            Node data dict or None if not found
        """
        result = (
            self.client.query
            .get(self._config.node_class_name, ["node_id", "title", "dev_spec", "dev_weight", 
                                                  "phase_number", "parent_id", "node_type", 
                                                  "status", "full_content", "position_x",
                                                  "position_y", "position_z", "layer", "family_weight"])
            .with_where({
                "path": ["node_id"],
                "operator": "Equal",
                "valueText": node_id
            })
            .do()
        )
        
        nodes = result.get("data", {}).get("Get", {}).get(self._config.node_class_name, [])
        return nodes[0] if nodes else None
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a node's properties.
        
        Args:
            node_id: The node identifier
            updates: Dictionary of properties to update
            
        Returns:
            True if updated, False if not found
        """
        # First find the Weaviate UUID
        result = (
            self.client.query
            .get(self._config.node_class_name, ["node_id"])
            .with_where({
                "path": ["node_id"],
                "operator": "Equal",
                "valueText": node_id
            })
            .with_additional(["id"])
            .do()
        )
        
        nodes = result.get("data", {}).get("Get", {}).get(self._config.node_class_name, [])
        if not nodes:
            return False
        
        uuid = nodes[0]["_additional"]["id"]
        self.client.data_object.update(
            uuid=uuid,
            class_name=self._config.node_class_name,
            data_object=updates
        )
        logger.debug(f"Updated node in Weaviate: {node_id}")
        return True
    
    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node by its node_id.
        
        Args:
            node_id: The node identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Find UUID first
        result = (
            self.client.query
            .get(self._config.node_class_name, ["node_id"])
            .with_where({
                "path": ["node_id"],
                "operator": "Equal",
                "valueText": node_id
            })
            .with_additional(["id"])
            .do()
        )
        
        nodes = result.get("data", {}).get("Get", {}).get(self._config.node_class_name, [])
        if not nodes:
            return False
        
        uuid = nodes[0]["_additional"]["id"]
        self.client.data_object.delete(
            uuid=uuid,
            class_name=self._config.node_class_name
        )
        logger.debug(f"Deleted node from Weaviate: {node_id}")
        return True
    
    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Semantic search across nodes.
        
        Args:
            query: Natural language search query
            limit: Maximum results to return
            
        Returns:
            List of matching nodes with similarity scores
        """
        result = (
            self.client.query
            .get(self._config.node_class_name, 
                 ["node_id", "title", "dev_spec", "dev_weight", "phase_number", "status"])
            .with_near_text({"concepts": [query]})
            .with_limit(limit)
            .with_additional(["certainty", "distance"])
            .do()
        )
        
        nodes = result.get("data", {}).get("Get", {}).get(self._config.node_class_name, [])
        return nodes
    
    def get_nodes_by_phase(self, phase_number: int) -> List[Dict[str, Any]]:
        """
        Get all nodes in a phase.
        
        Args:
            phase_number: The phase number
            
        Returns:
            List of nodes in that phase
        """
        result = (
            self.client.query
            .get(self._config.node_class_name, 
                 ["node_id", "title", "dev_spec", "dev_weight", "parent_id", 
                  "node_type", "status", "position_x", "position_y", "position_z"])
            .with_where({
                "path": ["phase_number"],
                "operator": "Equal",
                "valueInt": phase_number
            })
            .do()
        )
        
        return result.get("data", {}).get("Get", {}).get(self._config.node_class_name, [])
    
    def clear_all_data(self, confirm: bool = False) -> None:
        """
        Delete the entire class and all data. Use with caution!
        
        Args:
            confirm: Must be True to execute
        """
        if not confirm:
            raise ValueError("Must pass confirm=True to clear all data")
        
        class_name = self._config.node_class_name
        if self.client.schema.exists(class_name):
            self.client.schema.delete_class(class_name)
            logger.warning(f"⚠️ Weaviate class '{class_name}' deleted")
        
        self._initialized = False
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get current schema information."""
        schema = self.client.schema.get()
        return schema
    
    def get_node_count(self) -> int:
        """Get total number of nodes in Weaviate."""
        result = (
            self.client.query
            .aggregate(self._config.node_class_name)
            .with_meta_count()
            .do()
        )
        
        agg = result.get("data", {}).get("Aggregate", {}).get(self._config.node_class_name, [])
        if agg:
            return agg[0].get("meta", {}).get("count", 0)
        return 0
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# =============================================================================
# SINGLETON CLIENT
# =============================================================================

_weaviate_client: Optional[WeaviateClient] = None


def get_weaviate_client() -> WeaviateClient:
    """Get or create the singleton Weaviate client."""
    global _weaviate_client
    if _weaviate_client is None:
        _weaviate_client = WeaviateClient()
    return _weaviate_client


def reset_weaviate_client() -> None:
    """Reset the Weaviate client (for testing)."""
    global _weaviate_client
    if _weaviate_client is not None:
        _weaviate_client.close()
        _weaviate_client = None


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print("=" * 60)
    print("WEAVIATE CLIENT TEST")
    print("=" * 60)
    
    client = get_weaviate_client()
    
    # Health check
    health = client.health_check()
    print(f"\nHealth: {health}")
    
    if health["healthy"]:
        # Initialize schema
        client.initialize_schema()
        
        # Show schema
        schema = client.get_schema_info()
        classes = schema.get("classes", [])
        print(f"\nClasses: {[c['class'] for c in classes]}")
        
        # Node count
        count = client.get_node_count()
        print(f"Node count: {count}")
        
        print("\n✅ Weaviate client test passed!")
    else:
        print("\n❌ Weaviate not available - check Docker containers")
    
    client.close()
