"""Quick test to see if cyto imports work from init2's context."""
import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(f"BASE_DIR: {BASE_DIR}")

# Test 1: Can we import cyto_routes?
print("\n--- Test 1: import cyto_routes ---")
try:
    from cyto_routes import register_cyto_routes
    print("  ✓ cyto_routes imported OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    traceback.print_exc()

# Test 2: Can we import cyto_simulator?
print("\n--- Test 2: import cyto_simulator ---")
try:
    from cyto_simulator import register_simulator_routes
    print("  ✓ cyto_simulator imported OK")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    traceback.print_exc()

# Test 3: Can we manually add #Cyto to path and import?
print("\n--- Test 3: direct #Cyto imports ---")
CYTO_DIR = os.path.join(BASE_DIR, '#Cyto')
print(f"  CYTO_DIR: {CYTO_DIR}")
print(f"  Exists: {os.path.exists(CYTO_DIR)}")

if CYTO_DIR not in sys.path:
    sys.path.insert(0, CYTO_DIR)

try:
    import cyto_schema
    print(f"  ✓ cyto_schema imported OK (DB: {cyto_schema.DB_PATH})")
except Exception as e:
    print(f"  ✗ cyto_schema FAILED: {e}")
    traceback.print_exc()

try:
    import cyto_manager
    print("  ✓ cyto_manager imported OK")
except Exception as e:
    print(f"  ✗ cyto_manager FAILED: {e}")
    traceback.print_exc()

try:
    import cyto_integration
    print("  ✓ cyto_integration imported OK")
except Exception as e:
    print(f"  ✗ cyto_integration FAILED: {e}")
    traceback.print_exc()

# Test 4: Can we actually init the DB and create a manager?
print("\n--- Test 4: functional test ---")
try:
    cyto_schema.init_db()
    print(f"  ✓ DB initialized at {cyto_schema.DB_PATH}")
    
    mgr = cyto_manager.CytoManager()
    print("  ✓ CytoManager created")
    
    ci = cyto_integration.get_cyto_integration()
    print("  ✓ CytoIntegration created")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    traceback.print_exc()

print("\n--- Done ---")
