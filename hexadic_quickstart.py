#!/usr/bin/env python3
"""
HEXADIC QUICK START
Initializes database, creates test data, and shows status

Run this: python hexadic_quickstart.py
"""

import sys
import os

print("\n" + "="*70)
print("HEXADIC SYSTEM QUICK START")
print("="*70)

# Check if database exists
db_exists = os.path.exists('metatron_hexadic.db')
print(f"\n✓ Database exists: {db_exists}")

if not db_exists:
    print("\n[STEP 1] Creating hexadic database schema...")
    try:
        from create_hexadic_tables import create_hexadic_schema
        create_hexadic_schema()
    except Exception as e:
        print(f"✗ Failed: {e}")
        sys.exit(1)
else:
    print("\n[STEP 1] Database already exists - skipping creation")

# Test storage system
print("\n[STEP 2] Testing hexadic storage...")
try:
    from hexadic_storage import HexadicStorage
    
    storage = HexadicStorage()
    
    # Create test anchor
    anchor_id = storage.create_anchor('v1.5 r5 d.QUICKSTART a8 c8 t.NOW')
    print(f"  ✓ Created test anchor: {anchor_id}")
    
    # Record test decision
    decision_id = storage.record_decision(
        prompt="Initialize hexadic system?",
        stations_offered=[1, 2, 4],
        station_chosen=1,
        anchor_id=anchor_id,
        decision_type='ROUTINE'
    )
    print(f"  ✓ Recorded test decision: {decision_id}")
    
    # Log test event
    event_id = storage.log_circulation_event(
        event_type='SYSTEM_INIT',
        theta=0,
        ring=0.500,
        station=1,
        anchor_id=anchor_id
    )
    print(f"  ✓ Logged test event: {event_id}")
    
    # Create test sync node
    node_id = storage.create_sync_node(
        node_id='0.0',
        tree_id='0',
        label='Hexadic System Root',
        theta=0,
        ring=0.382,
        node_type='sync',
        station=1,
        anchor_id=anchor_id
    )
    print(f"  ✓ Created test node: {node_id}")
    
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Show status
print("\n[STEP 3] Hexadic system status...")
try:
    # Get counts
    anchors = storage.search_anchors(limit=100)
    events = storage.get_recent_events(limit=100)
    nodes = storage.get_all_nodes_with_anchors()
    stats = storage.get_decision_stats()
    
    print(f"\n  📊 DATABASE STATISTICS:")
    print(f"  - Anchors: {len(anchors)}")
    print(f"  - Events: {len(events)}")
    print(f"  - Nodes: {len(nodes)}")
    print(f"  - Decisions: {sum(stats['station_counts'].values()) if stats['station_counts'] else 0}")
    
    if stats['station_counts']:
        print(f"\n  🎯 STATION USAGE:")
        for station, count in sorted(stats['station_counts'].items()):
            print(f"  - Station {station}: {count} decisions")
    
    if events:
        print(f"\n  🌀 RECENT EVENTS:")
        for event in events[-5:]:
            print(f"  - {event['event_type']} @ θ={event['theta_position']}, r={event['ring_position']}")
    
except Exception as e:
    print(f"⚠ Status check failed: {e}")

# Final instructions
print("\n" + "="*70)
print("✓ HEXADIC SYSTEM OPERATIONAL!")
print("="*70)
print("\nQUICK TEST:")
print("  python -c \"from hexadic_storage import HexadicStorage; s=HexadicStorage(); print(f'Anchors: {len(s.search_anchors())}')\"")
print("\nDATABASE: metatron_hexadic.db")
print("STORAGE: hexadic_storage.py")
print("="*70 + "\n")
