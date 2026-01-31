"""
Node Complex Health Check & Quick Start
========================================

Run this to verify your Node Complex installation:
    python -m node_complex.health_check

Or from the V11 directory:
    python node_complex/health_check.py
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the Node Complex banner."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     ███╗   ██╗ ██████╗ ██████╗ ███████╗                         ║
║     ████╗  ██║██╔═══██╗██╔══██╗██╔════╝                         ║
║     ██╔██╗ ██║██║   ██║██║  ██║█████╗                           ║
║     ██║╚██╗██║██║   ██║██║  ██║██╔══╝                           ║
║     ██║ ╚████║╚██████╔╝██████╔╝███████╗                         ║
║     ╚═╝  ╚═══╝ ╚═════╝ ╚═════╝ ╚══════╝                         ║
║                                                                  ║
║      ██████╗ ██████╗ ███╗   ███╗██████╗ ██╗     ███████╗██╗  ██╗║
║     ██╔════╝██╔═══██╗████╗ ████║██╔══██╗██║     ██╔════╝╚██╗██╔╝║
║     ██║     ██║   ██║██╔████╔██║██████╔╝██║     █████╗   ╚███╔╝ ║
║     ██║     ██║   ██║██║╚██╔╝██║██╔═══╝ ██║     ██╔══╝   ██╔██╗ ║
║     ╚██████╗╚██████╔╝██║ ╚═╝ ██║██║     ███████╗███████╗██╔╝ ██╗║
║      ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝║
║                                                                  ║
║     Phase NC-1: Core Data Layer                                  ║
║     STOIC-Governed Development Visualization                     ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
    """)


def check_config():
    """Check configuration loading."""
    print("\n" + "=" * 60)
    print("📋 CONFIGURATION CHECK")
    print("=" * 60)
    
    try:
        from node_complex.config import get_config
        config = get_config()
        
        print(f"\n  Neo4j URI:      {config.database.neo4j.uri}")
        print(f"  Weaviate URL:   {config.database.weaviate.url}")
        print(f"  Flask Port:     {config.flask_port}")
        print(f"  Helix Spirals:  {config.default_helix_spirals}")
        print(f"  Debug Mode:     {config.debug}")
        
        print("\n  Gravity Settings:")
        print(f"    Surface:    {config.gravity.surface_gravity}")
        print(f"    Axis:       {config.gravity.axis_gravity}")
        print(f"    Apex:       {config.gravity.apex_gravity}")
        print(f"    Repulsion:  {config.gravity.repulsion_strength}")
        
        print("\n  ✅ Configuration loaded successfully")
        return True
        
    except Exception as e:
        print(f"\n  ❌ Configuration error: {e}")
        return False


def check_neo4j():
    """Check Neo4j connectivity."""
    print("\n" + "=" * 60)
    print("🔷 NEO4J CHECK")
    print("=" * 60)
    
    try:
        from node_complex.data.neo4j_client import Neo4jClient
        
        client = Neo4jClient()
        health = client.health_check()
        
        if health["healthy"]:
            print(f"\n  Status:   ✅ Connected")
            print(f"  URI:      {health['details']['uri']}")
            print(f"  Database: {health['details']['database']}")
            
            # Initialize schema
            print("\n  Initializing schema...")
            client.initialize_schema()
            
            # Get schema info
            schema = client.get_schema_info()
            print(f"  Constraints: {len(schema['constraints'])}")
            print(f"  Indexes:     {len(schema['indexes'])}")
            
            client.close()
            return True
        else:
            print(f"\n  Status: ❌ Not available")
            print(f"  Error:  {health['message']}")
            print("\n  💡 Start Neo4j with:")
            print("     docker start neo4j-nodecomplex")
            return False
            
    except Exception as e:
        print(f"\n  ❌ Neo4j error: {e}")
        print("\n  💡 Start Neo4j with:")
        print("     docker run -d --name neo4j-nodecomplex -p 7474:7474 -p 7687:7687 \\")
        print("       -e NEO4J_AUTH=neo4j/nodecomplex123 neo4j:latest")
        return False


def check_weaviate():
    """Check Weaviate connectivity."""
    print("\n" + "=" * 60)
    print("🔶 WEAVIATE CHECK")
    print("=" * 60)
    
    try:
        from node_complex.data.weaviate_client import WeaviateClient
        
        client = WeaviateClient()
        health = client.health_check()
        
        if health["healthy"]:
            print(f"\n  Status:     ✅ Connected")
            print(f"  URL:        {health['details']['url']}")
            print(f"  Version:    {health['details'].get('version', 'unknown')}")
            print(f"  Modules:    {', '.join(health['details'].get('modules', []))}")
            
            # Initialize schema
            print("\n  Initializing schema...")
            client.initialize_schema()
            
            # Get node count
            count = client.get_node_count()
            print(f"  Node count: {count}")
            
            client.close()
            return True
        else:
            print(f"\n  Status: ❌ Not available")
            print(f"  Error:  {health['message']}")
            print("\n  💡 Start Weaviate with Docker (see install docs)")
            return False
            
    except Exception as e:
        print(f"\n  ❌ Weaviate error: {e}")
        print("\n  💡 Weaviate may still be starting up. Wait 30 seconds and retry.")
        return False


def check_schemas():
    """Validate Pydantic schemas."""
    print("\n" + "=" * 60)
    print("📦 SCHEMA VALIDATION")
    print("=" * 60)
    
    try:
        from node_complex.data.schemas import (
            Node, NodeCreate, NodeStatus, NodeType,
            Phase, PhaseCreate,
            Manifest, ManifestCreate,
            Thread, ThreadType, get_thread_color
        )
        
        # Test node creation
        node = NodeCreate(
            node_id="NC1-001",
            title="DATABASE_FOUNDATION",
            dev_weight=-0.345,
            dev_spec="Core database setup",
            phase_number=1
        )
        print(f"\n  ✅ NodeCreate: {node.node_id}")
        
        # Test full node with layer calculation
        full_node = Node(
            node_id="NC1-075",
            title="TRANSACTION_MANAGER",
            dev_weight=-0.423,
            phase_number=1,
            status=NodeStatus.ACTIVE
        )
        print(f"  ✅ Node layer calc: weight {full_node.dev_weight} → layer {full_node.layer}")
        
        # Test phase
        phase = PhaseCreate(title="Core Data Layer")
        print(f"  ✅ PhaseCreate: {phase.title}")
        
        # Test manifest
        manifest = ManifestCreate(
            manifest_id="node-complex",
            title="Node Complex Manifest"
        )
        print(f"  ✅ ManifestCreate: {manifest.manifest_id}")
        
        # Test thread colors
        color = get_thread_color(ThreadType.PARENT_CHILD, parent_depth=2)
        print(f"  ✅ Thread color (depth 2): {color}")
        
        return True
        
    except Exception as e:
        print(f"\n  ❌ Schema error: {e}")
        return False


def run_health_check():
    """Run complete health check."""
    print_banner()
    print(f"\n🕐 Health Check Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "config": check_config(),
        "schemas": check_schemas(),
        "neo4j": check_neo4j(),
        "weaviate": check_weaviate()
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {component.upper():12} {status}")
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL SYSTEMS OPERATIONAL - Node Complex is ready!")
        print("\n  Next steps:")
        print("  1. Run: python startapp.py")
        print("  2. Open: http://localhost:5000")
        print("=" * 60)
        return 0
    else:
        print("⚠️  SOME SYSTEMS OFFLINE - Check Docker containers")
        print("\n  Required containers:")
        print("  - neo4j-nodecomplex (port 7687)")
        print("  - weaviate-nodecomplex (port 8080)")
        print("  - t2v-transformers (port 8081)")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(run_health_check())
