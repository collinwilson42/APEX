#!/usr/bin/env python3
"""
HEXADIC STORAGE MANAGER
CRUD operations for inline anchors, decision paths, and circulation events

Usage:
    from hexadic_storage import HexadicStorage
    
    storage = HexadicStorage()
    anchor_id = storage.create_anchor('v1.5 r5 d.RODIN a8 c8 t.BREAKTHROUGH')
    decision_id = storage.record_decision('Build TorusField?', [1,2,4], 1, anchor_id)
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = 'metatron_hexadic.db'


class HexadicStorage:
    """Manager for hexadic database operations"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========================================================================
    # INLINE ANCHOR OPERATIONS
    # ========================================================================
    
    def create_anchor(
        self,
        anchor_string: str,
        sync_node_id: Optional[str] = None
    ) -> int:
        """
        Create new inline anchor from string
        
        Args:
            anchor_string: e.g., 'v1.5 r5 d.RODIN a8 c8 t.BREAKTHROUGH'
            sync_node_id: Optional sync node reference
            
        Returns:
            anchor_id
        """
        # Parse anchor string
        parts = anchor_string.split()
        parsed = {}
        
        for part in parts:
            if part.startswith('v'):
                version = part[1:].split('.')
                parsed['version_major'] = int(version[0])
                parsed['version_minor'] = int(version[1]) if len(version) > 1 else 1
            elif part.startswith('r'):
                parsed['resonance_station'] = int(part[1:])
            elif part.startswith('d.'):
                parsed['domain'] = part[2:]
            elif part.startswith('a'):
                parsed['alignment_station'] = int(part[1:])
            elif part.startswith('c'):
                parsed['confidence_station'] = int(part[1:])
            elif part.startswith('t.'):
                parsed['temporal_marker'] = part[2:]
        
        # Validate hexadic constraints
        for station_key in ['resonance_station', 'alignment_station', 'confidence_station']:
            if station_key in parsed and parsed[station_key] not in [1, 2, 4, 5, 7, 8]:
                raise ValueError(f"{station_key} must be 1,2,4,5,7,8 (skip 3,6,9)")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO hexadic_anchors 
                (version_major, version_minor, resonance_station, domain,
                 alignment_station, confidence_station, temporal_marker,
                 anchor_string, sync_node_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                parsed.get('version_major', 1),
                parsed.get('version_minor', 1),
                parsed.get('resonance_station', 2),
                parsed.get('domain', 'UNKNOWN'),
                parsed.get('alignment_station', 2),
                parsed.get('confidence_station', 4),
                parsed.get('temporal_marker', 'NOW'),
                anchor_string,
                sync_node_id
            ))
            
            anchor_id = cursor.lastrowid
            conn.commit()
            return anchor_id
            
        finally:
            conn.close()
    
    def get_anchor(self, anchor_id: int) -> Optional[Dict]:
        """Get anchor by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM hexadic_anchors WHERE anchor_id = ?", (anchor_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_anchor_by_string(self, anchor_string: str) -> Optional[Dict]:
        """Get anchor by string"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM hexadic_anchors WHERE anchor_string = ?", (anchor_string,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def search_anchors(
        self,
        domain: Optional[str] = None,
        resonance: Optional[int] = None,
        version_minor: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Search anchors with filters"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM hexadic_anchors WHERE 1=1"
        params = []
        
        if domain:
            query += " AND domain LIKE ?"
            params.append(f"%{domain}%")
        if resonance:
            query += " AND resonance_station = ?"
            params.append(resonance)
        if version_minor:
            query += " AND version_minor = ?"
            params.append(version_minor)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        try:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ========================================================================
    # DECISION PATH OPERATIONS
    # ========================================================================
    
    def record_decision(
        self,
        prompt: str,
        stations_offered: List[int],
        station_chosen: int,
        anchor_id: int,
        decision_type: str = 'ROUTINE',
        magnetic_convergence: Optional[int] = None
    ) -> int:
        """
        Record a decision path choice
        
        Args:
            prompt: The decision question
            stations_offered: List of hexadic stations presented
            station_chosen: Which station user chose
            anchor_id: Current inline anchor
            decision_type: ROUTINE, EDGE_CASE, COMPLEX, HIGH_RISK
            magnetic_convergence: 3, 6, or 9 if converged
            
        Returns:
            decision_id
        """
        if station_chosen not in [1, 2, 4, 5, 7, 8]:
            raise ValueError("station_chosen must be 1,2,4,5,7,8")
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO decision_paths
                (decision_prompt, decision_type, stations_offered,
                 station_chosen, magnetic_convergence, anchor_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                prompt,
                decision_type,
                json.dumps(stations_offered),
                station_chosen,
                magnetic_convergence,
                anchor_id
            ))
            
            decision_id = cursor.lastrowid
            conn.commit()
            return decision_id
            
        finally:
            conn.close()
    
    def update_decision_outcome(
        self,
        decision_id: int,
        success: bool,
        notes: Optional[str] = None
    ):
        """Update decision outcome"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE decision_paths
                SET outcome_success = ?,
                    outcome_notes = ?,
                    resolved_at = CURRENT_TIMESTAMP
                WHERE decision_id = ?
            """, (success, notes, decision_id))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_decision_stats(self) -> Dict:
        """Get decision statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # Count by station
            cursor.execute("""
                SELECT station_chosen, COUNT(*) as count
                FROM decision_paths
                GROUP BY station_chosen
                ORDER BY count DESC
            """)
            
            station_counts = {row['station_chosen']: row['count'] for row in cursor.fetchall()}
            
            # Success rate by station
            cursor.execute("""
                SELECT station_chosen,
                       AVG(CASE WHEN outcome_success = 1 THEN 1.0 ELSE 0.0 END) as success_rate
                FROM decision_paths
                WHERE outcome_success IS NOT NULL
                GROUP BY station_chosen
            """)
            
            success_rates = {row['station_chosen']: row['success_rate'] for row in cursor.fetchall()}
            
            return {
                'station_counts': station_counts,
                'success_rates': success_rates
            }
        finally:
            conn.close()
    
    # ========================================================================
    # CIRCULATION EVENT OPERATIONS
    # ========================================================================
    
    def log_circulation_event(
        self,
        event_type: str,
        theta: float,
        ring: float,
        station: Optional[int] = None,
        anchor_id: Optional[int] = None,
        z_offset: float = 0,
        w_layer: int = 0,
        axis_point: Optional[int] = None,
        event_data: Optional[Dict] = None
    ) -> int:
        """
        Log a toroidal circulation event
        
        Args:
            event_type: NODE_CREATED, QUERY_EXECUTED, COLLAPSE, SYNTHESIS
            theta: Angular position (0-360)
            ring: Ring position (0.382, 0.500, 0.618, 0.786)
            station: Hexadic station (1,2,4,5,7,8)
            anchor_id: Current inline anchor
            z_offset: Vertical offset
            w_layer: Temporal layer
            axis_point: Magnetic axis (3, 6, or 9)
            event_data: Additional JSON data
            
        Returns:
            event_id
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO circulation_events
                (event_type, theta_position, ring_position, z_offset, w_layer,
                 station, axis_point, anchor_id, event_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                theta,
                ring,
                z_offset,
                w_layer,
                station,
                axis_point,
                anchor_id,
                json.dumps(event_data) if event_data else None
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            return event_id
            
        finally:
            conn.close()
    
    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """Get recent circulation events"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT ce.*, ha.anchor_string, ha.domain
                FROM circulation_events ce
                LEFT JOIN hexadic_anchors ha ON ce.anchor_id = ha.anchor_id
                ORDER BY ce.created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_events_for_visualization(self, limit: int = 200) -> Dict:
        """Get events formatted for torus visualization"""
        events = self.get_recent_events(limit)
        
        # Group by type
        by_type = {}
        for event in events:
            event_type = event['event_type']
            if event_type not in by_type:
                by_type[event_type] = []
            by_type[event_type].append({
                'theta': event['theta_position'],
                'ring': event['ring_position'],
                'z': event['z_offset'],
                'station': event['station'],
                'axis': event['axis_point'],
                'anchor': event.get('anchor_string'),
                'timestamp': event['created_at']
            })
        
        return {
            'events_by_type': by_type,
            'total_events': len(events),
            'active_stations': list(set(e['station'] for e in events if e['station']))
        }
    
    # ========================================================================
    # SYNC NODE OPERATIONS (Enhanced)
    # ========================================================================
    
    def create_sync_node(
        self,
        node_id: str,
        tree_id: str,
        label: str,
        theta: float,
        ring: float,
        node_type: str,
        station: Optional[int] = None,
        anchor_id: Optional[int] = None,
        decision_path_id: Optional[int] = None,
        z_offset: float = 0,
        w_layer: int = 0
    ) -> str:
        """Create sync node with hexadic metadata"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO sync_nodes
                (node_id, tree_id, label, theta_position, ring_position,
                 z_offset, w_layer, node_type, station, anchor_id, decision_path_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id, tree_id, label, theta, ring,
                z_offset, w_layer, node_type, station, anchor_id, decision_path_id
            ))
            
            conn.commit()
            return node_id
            
        finally:
            conn.close()
    
    def get_all_nodes_with_anchors(self) -> List[Dict]:
        """Get all sync nodes with their inline anchor data"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT sn.*, ha.anchor_string, ha.domain, ha.resonance_station
                FROM sync_nodes sn
                LEFT JOIN hexadic_anchors ha ON sn.anchor_id = ha.anchor_id
                ORDER BY sn.created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def quick_anchor(anchor_string: str) -> int:
    """Quick create anchor"""
    storage = HexadicStorage()
    return storage.create_anchor(anchor_string)

def quick_decision(prompt: str, stations: List[int], chosen: int, anchor_id: int) -> int:
    """Quick record decision"""
    storage = HexadicStorage()
    return storage.record_decision(prompt, stations, chosen, anchor_id)

def quick_event(event_type: str, theta: float, ring: float, station: int, anchor_id: int) -> int:
    """Quick log event"""
    storage = HexadicStorage()
    return storage.log_circulation_event(event_type, theta, ring, station, anchor_id)


if __name__ == '__main__':
    # Test the storage system
    print("\n" + "="*70)
    print("HEXADIC STORAGE TEST")
    print("="*70)
    
    storage = HexadicStorage()
    
    # Create anchor
    anchor_id = storage.create_anchor('v1.5 r5 d.TEST a7 c8 t.NOW')
    print(f"\n✓ Created anchor: {anchor_id}")
    
    # Record decision
    decision_id = storage.record_decision(
        prompt="Test decision?",
        stations_offered=[1, 2, 4],
        station_chosen=1,
        anchor_id=anchor_id
    )
    print(f"✓ Recorded decision: {decision_id}")
    
    # Log event
    event_id = storage.log_circulation_event(
        event_type='TEST_EVENT',
        theta=90,
        ring=0.618,
        station=5,
        anchor_id=anchor_id
    )
    print(f"✓ Logged event: {event_id}")
    
    # Get recent
    events = storage.get_recent_events(5)
    print(f"\n✓ Recent events: {len(events)}")
    
    print("\n" + "="*70)
    print("TEST COMPLETE - Storage system operational!")
    print("="*70 + "\n")
