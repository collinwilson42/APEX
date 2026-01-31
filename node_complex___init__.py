"""
Node Complex - 3D/4D Development Visualization System
======================================================

A STOIC-governed pyramid visualization for phased development.

Phase NC-1: Core Data Layer
- Neo4j for graph relationships
- Weaviate for vector embeddings
- Pydantic models for validation

Usage:
    from node_complex import get_config, Neo4jClient, WeaviateClient
    
    config = get_config()
    neo4j = Neo4jClient()
    weaviate = WeaviateClient()
"""

__version__ = "0.1.0"
__phase__ = "NC-1"

# Configuration
from .config import (
    get_config,
    NodeComplexConfig,
    Neo4jConfig,
    WeaviateConfig,
    GravityConfig
)

# Data layer
from .data import (
    Neo4jClient,
    WeaviateClient,
    Node, NodeCreate, NodeUpdate,
    Phase, PhaseCreate, PhaseUpdate,
    Manifest, ManifestCreate,
    Thread, ThreadCreate,
    NodeStatus, NodeType, ThreadType
)

__all__ = [
    # Version info
    '__version__',
    '__phase__',
    
    # Config
    'get_config',
    'NodeComplexConfig',
    'Neo4jConfig',
    'WeaviateConfig',
    'GravityConfig',
    
    # Clients
    'Neo4jClient',
    'WeaviateClient',
    
    # Schemas
    'Node', 'NodeCreate', 'NodeUpdate',
    'Phase', 'PhaseCreate', 'PhaseUpdate',
    'Manifest', 'ManifestCreate',
    'Thread', 'ThreadCreate',
    'NodeStatus', 'NodeType', 'ThreadType'
]
