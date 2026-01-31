"""
Quick Start - Neo4j Nodebase Setup
Handles installation and initial configuration
"""

import subprocess
import sys
import os
from pathlib import Path


def check_python_version():
    """Ensure Python 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("✗ Python 3.8+ required")
        print(f"  Current: Python {version.major}.{version.minor}")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install required packages"""
    print("\n--- Installing Dependencies ---")
    
    packages = [
        'neo4j',
        'python-dotenv'
    ]
    
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', package, '-q'
            ])
            print(f"✓ {package} installed")
        except subprocess.CalledProcessError:
            print(f"✗ Failed to install {package}")
            return False
    
    return True


def check_neo4j_running():
    """Check if Neo4j is accessible"""
    print("\n--- Checking Neo4j Connection ---")
    
    try:
        from neo4j import GraphDatabase
        
        # Try to connect
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "neo4j"),
            encrypted=False
        )
        driver.verify_connectivity()
        driver.close()
        print("✓ Neo4j is running on bolt://localhost:7687")
        return True
        
    except Exception as e:
        print("✗ Cannot connect to Neo4j")
        print("\nPossible issues:")
        print("1. Neo4j is not installed")
        print("   → Download: https://neo4j.com/download/")
        print("2. Neo4j is not running")
        print("   → Start with: neo4j start")
        print("   → Or use Neo4j Desktop")
        print("3. Wrong credentials")
        print("   → Default: neo4j/neo4j")
        print("   → Update .env after first login")
        return False


def check_env_file():
    """Verify .env configuration"""
    print("\n--- Checking .env Configuration ---")
    
    env_path = Path(".env")
    
    if not env_path.exists():
        print("✗ .env file not found")
        return False
    
    with open(env_path, 'r') as f:
        content = f.read()
    
    required = ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD']
    missing = [key for key in required if key not in content]
    
    if missing:
        print(f"✗ Missing in .env: {', '.join(missing)}")
        return False
    
    print("✓ .env file configured")
    return True


def run_test():
    """Run connection test"""
    print("\n--- Running Connection Test ---")
    
    try:
        import neo4j_config
        neo4j_config.test_connection()
        return True
    except Exception as e:
        print(f"✗ Test failed: {str(e)}")
        return False


def main():
    """Main setup workflow"""
    
    print("\n" + "="*60)
    print("NEO4J NODEBASE - QUICK START")
    print("="*60)
    
    # Step 1: Check Python
    if not check_python_version():
        return
    
    # Step 2: Install dependencies
    if not install_dependencies():
        print("\n✗ Setup failed: Could not install dependencies")
        return
    
    # Step 3: Check .env
    if not check_env_file():
        print("\n✗ Setup failed: .env configuration incomplete")
        print("\nManual setup required:")
        print("1. Make sure .env exists in V11 folder")
        print("2. Add Neo4j credentials:")
        print("   NEO4J_URI=bolt://localhost:7687")
        print("   NEO4J_USER=neo4j")
        print("   NEO4J_PASSWORD=your_password")
        return
    
    # Step 4: Check Neo4j
    if not check_neo4j_running():
        print("\n✗ Setup failed: Neo4j not accessible")
        print("\nNext steps:")
        print("1. Install Neo4j: https://neo4j.com/download/")
        print("2. Start Neo4j service")
        print("3. Run this script again")
        return
    
    # Step 5: Run test
    print("\n--- Final Verification ---")
    if run_test():
        print("\n" + "="*60)
        print("✓ SETUP COMPLETE - NODEBASE READY")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python neo4j_config.py")
        print("2. Run: python strategy_node_mapper.py")
        print("3. Start building your node-code tree!")
    else:
        print("\n✗ Setup incomplete - see errors above")


if __name__ == "__main__":
    main()
