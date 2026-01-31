"""
Node Complex Configuration Settings
====================================
ROOT P: CONFIGURATION (NC1-095 → NC1-098)
Phase NC-1 | Core Data Layer

Nodes Implemented:
- NC1-095: CONFIG_DATABASE_URLS
- NC1-096: CONFIG_DATABASE_CREDENTIALS  
- NC1-097: CONFIG_CONNECTION_POOL_SIZE
- NC1-098: CONFIG_TIMEOUT_SETTINGS

STOIC Alignment:
- Stability: Validated ranges, type-safe configs
- Tunity: All settings adjustable via env vars
- Opportunity: Single source of truth for all config
"""

import os
from typing import Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# =============================================================================
# NC1-095: CONFIG_DATABASE_URLS
# =============================================================================

class Neo4jConfig(BaseModel):
    """Neo4j connection configuration."""
    
    uri: str = Field(
        default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        description="Neo4j Bolt URI"
    )
    username: str = Field(
        default_factory=lambda: os.getenv("NEO4J_USERNAME", "neo4j"),
        description="Neo4j username"
    )
    password: str = Field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", "nodecomplex123"),
        description="Neo4j password"
    )
    database: str = Field(
        default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"),
        description="Neo4j database name"
    )
    
    # NC1-097: CONNECTION_POOL_SIZE
    max_connection_pool_size: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Maximum connections in pool"
    )
    
    # NC1-098: TIMEOUT_SETTINGS
    connection_timeout: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Connection timeout in seconds"
    )
    query_timeout: float = Field(
        default=60.0,
        ge=10.0,
        le=300.0,
        description="Query timeout in seconds"
    )


class WeaviateConfig(BaseModel):
    """Weaviate connection configuration."""
    
    url: str = Field(
        default_factory=lambda: os.getenv("WEAVIATE_URL", "http://localhost:8080"),
        description="Weaviate REST API URL"
    )
    
    # NC1-097: CONNECTION_POOL_SIZE
    connection_pool_maxsize: int = Field(
        default=20,
        ge=5,
        le=100,
        description="HTTP connection pool size"
    )
    
    # NC1-098: TIMEOUT_SETTINGS
    timeout: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Request timeout in seconds"
    )
    
    # Vectorizer settings (text2vec-transformers)
    vectorizer_module: str = Field(
        default="text2vec-transformers",
        description="Weaviate vectorizer module"
    )
    
    # Schema class name
    node_class_name: str = Field(
        default="DevelopmentNode",
        description="Weaviate class for development nodes"
    )


# =============================================================================
# NC1-096: CONFIG_DATABASE_CREDENTIALS (Secure handling)
# =============================================================================

class DatabaseConfig(BaseModel):
    """Combined database configuration."""
    
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    weaviate: WeaviateConfig = Field(default_factory=WeaviateConfig)
    
    def get_neo4j_auth(self) -> tuple:
        """Return Neo4j auth tuple for driver."""
        return (self.neo4j.username, self.neo4j.password)
    
    def mask_credentials(self) -> dict:
        """Return config with masked passwords for logging."""
        return {
            "neo4j": {
                "uri": self.neo4j.uri,
                "username": self.neo4j.username,
                "password": "***MASKED***",
                "database": self.neo4j.database
            },
            "weaviate": {
                "url": self.weaviate.url,
                "vectorizer": self.weaviate.vectorizer_module
            }
        }


# =============================================================================
# GRAVITY CONFIGURATION (For NC-2 Physics Engine)
# =============================================================================

class GravityConfig(BaseModel):
    """
    Gravity settings for pyramid physics.
    Prepared here for NC-2, used by physics engine.
    Per Manifest Appendix A.
    """
    
    surface_gravity: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Pull toward base (Y=0)"
    )
    axis_gravity: float = Field(
        default=1.5,
        ge=1.0,
        le=3.0,
        description="Pull toward central axis"
    )
    apex_gravity: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="Weight-scaled pull toward apex"
    )
    repulsion_strength: float = Field(
        default=0.5,
        ge=0.1,
        le=1.0,
        description="Node separation force"
    )
    min_node_distance: float = Field(
        default=0.05,
        ge=0.02,
        le=0.10,
        description="Minimum spacing between nodes"
    )
    
    # Convergence settings
    convergence_threshold: float = Field(
        default=0.001,
        description="When to stop position iterations"
    )
    max_iterations: int = Field(
        default=1000,
        description="Safety limit on physics iterations"
    )


# =============================================================================
# MASTER CONFIGURATION
# =============================================================================

class NodeComplexConfig(BaseModel):
    """
    Master configuration for the entire Node Complex system.
    Single source of truth.
    """
    
    # Database configs
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # Physics configs
    gravity: GravityConfig = Field(default_factory=GravityConfig)
    
    # Flask integration
    flask_port: int = Field(
        default_factory=lambda: int(os.getenv("FLASK_PORT", "5000")),
        description="Flask server port"
    )
    
    # Helix defaults
    default_helix_spirals: int = Field(
        default=2,
        description="2 (dual) or 4 (quad) helix"
    )
    helix_rotation_per_level: float = Field(
        default=30.0,
        description="Degrees per Y-unit"
    )
    
    # Debug mode
    debug: bool = Field(
        default_factory=lambda: os.getenv("NODE_COMPLEX_DEBUG", "false").lower() == "true"
    )
    
    @validator('default_helix_spirals')
    def validate_helix_spirals(cls, v):
        if v not in (2, 4):
            raise ValueError("Helix spirals must be 2 (dual) or 4 (quad)")
        return v


# =============================================================================
# SINGLETON CONFIG GETTER
# =============================================================================

_config_instance: Optional[NodeComplexConfig] = None


def get_config() -> NodeComplexConfig:
    """
    Get or create the singleton config instance.
    Thread-safe lazy initialization.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = NodeComplexConfig()
    return _config_instance


def reset_config() -> None:
    """Reset config (useful for testing)."""
    global _config_instance
    _config_instance = None


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    config = get_config()
    print("=" * 60)
    print("NODE COMPLEX CONFIGURATION")
    print("=" * 60)
    print(f"\nNeo4j URI:     {config.database.neo4j.uri}")
    print(f"Weaviate URL:  {config.database.weaviate.url}")
    print(f"Flask Port:    {config.flask_port}")
    print(f"Helix Spirals: {config.default_helix_spirals}")
    print(f"Debug Mode:    {config.debug}")
    print("\nGravity Settings:")
    print(f"  Surface: {config.gravity.surface_gravity}")
    print(f"  Axis:    {config.gravity.axis_gravity}")
    print(f"  Apex:    {config.gravity.apex_gravity}")
    print(f"  Repulsion: {config.gravity.repulsion_strength}")
    print("\n✅ Configuration loaded successfully!")
