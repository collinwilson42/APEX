"""
CYTO v3 - Trading Intelligence Manager
Handles all math, insertions, and queries for the CytoBase.

Key Functions:
- calc_theta_slot(timestamp) -> 0-287 slot index
- calc_radius(pnl, history) -> 0.618-1.618 percentile position
- calc_agreement(w_15m, w_1h) -> 0-1 alignment score
- calc_node_visuals(sentiment_data) -> size, hue, saturation
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
import statistics

from cyto_schema import (
    get_connection, 
    DB_PATH, 
    SLOT_COUNT, 
    SLOT_MINUTES, 
    CYCLE_HOURS,
    RADIUS_FLOOR,
    RADIUS_MEDIAN,
    RADIUS_CEILING,
    REFERENCE_EPOCH
)

# ============================================
# CYTO MANAGER CLASS
# ============================================

class CytoManager:
    """
    Manages the CytoBase trading intelligence database.
    
    Responsibilities:
    - Time → Slot calculations (288 slots per 72h cycle)
    - P/L → Radius calculations (percentile-based)
    - Sentiment → Visual encoding (size, hue, saturation)
    - CRUD operations for instances, nodes, trades
    """
    
    def __init__(self, db_path: str = None):
        """Initialize with optional custom database path."""
        self.db_path = db_path or DB_PATH
        self._pnl_history: Dict[str, List[float]] = {}  # instance_id -> list of PnLs
    
    # ========================================
    # TEMPORAL CALCULATIONS
    # ========================================
    
    def calc_theta_slot(self, timestamp: datetime) -> int:
        """
        Calculate the theta slot (0-287) for a given timestamp.
        
        1 slot = 15 minutes
        288 slots = 72 hours (one cycle)
        
        Args:
            timestamp: The datetime to convert
            
        Returns:
            Integer slot index (0-287)
        """
        elapsed = timestamp - REFERENCE_EPOCH
        total_minutes = elapsed.total_seconds() / 60
        slot = int(total_minutes / SLOT_MINUTES) % SLOT_COUNT
        return slot
    
    def calc_cycle_index(self, timestamp: datetime) -> int:
        """
        Calculate which 72-hour cycle this timestamp belongs to.
        
        Args:
            timestamp: The datetime to check
            
        Returns:
            Integer cycle index (0, 1, 2, ...)
        """
        elapsed = timestamp - REFERENCE_EPOCH
        total_hours = elapsed.total_seconds() / 3600
        cycle = int(total_hours / CYCLE_HOURS)
        return cycle
    
    def slot_to_angle(self, slot: int) -> float:
        """
        Convert slot index to rotation angle for visualization.
        
        Args:
            slot: Slot index (0-287)
            
        Returns:
            Angle in degrees (0-360)
        """
        return (slot / SLOT_COUNT) * 360
    
    def get_cycle_bounds(self, cycle_index: int) -> Tuple[datetime, datetime]:
        """
        Get the start and end timestamps for a given cycle.
        
        Args:
            cycle_index: The cycle number
            
        Returns:
            Tuple of (start_time, end_time)
        """
        start = REFERENCE_EPOCH + timedelta(hours=cycle_index * CYCLE_HOURS)
        end = start + timedelta(hours=CYCLE_HOURS)
        return start, end
    
    # ========================================
    # PERFORMANCE CALCULATIONS
    # ========================================
    
    def calc_radius(self, pnl: float, instance_id: str) -> float:
        """
        Calculate the radius (0.618-1.618) based on P/L percentile.
        
        Uses historical P/L data for the instance to determine percentile.
        
        Args:
            pnl: The P/L value for this trade
            instance_id: The instance to compare against
            
        Returns:
            Radius value (0.618 = bottom 10%, 1.0 = median, 1.618 = top 10%)
        """
        history = self._pnl_history.get(instance_id, [])
        
        if len(history) < 2:
            # Not enough history, place at median
            return RADIUS_MEDIAN
        
        # Calculate percentile
        sorted_history = sorted(history)
        count_below = sum(1 for h in sorted_history if h < pnl)
        percentile = count_below / len(sorted_history)  # 0.0 to 1.0
        
        # Map to radius range
        radius = RADIUS_FLOOR + (percentile * (RADIUS_CEILING - RADIUS_FLOOR))
        return round(radius, 4)
    
    def add_to_pnl_history(self, instance_id: str, pnl: float):
        """Track P/L for percentile calculations."""
        if instance_id not in self._pnl_history:
            self._pnl_history[instance_id] = []
        self._pnl_history[instance_id].append(pnl)
    
    def load_pnl_history(self, instance_id: str):
        """Load P/L history from database for an instance."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT raw_pnl FROM cyto_nodes 
            WHERE instance_id = ? AND has_trade = 1 AND raw_pnl IS NOT NULL
            ORDER BY timestamp
        """, (instance_id,))
        history = [row['raw_pnl'] for row in cursor.fetchall()]
        conn.close()
        self._pnl_history[instance_id] = history
    
    # ========================================
    # SENTIMENT CALCULATIONS
    # ========================================
    
    def calc_agreement(self, weighted_15m: float, weighted_1h: float) -> float:
        """
        Calculate agreement score between 15m and 1H weighted averages.
        
        High agreement (0.5-1.0): Same direction, similar magnitude
        Low agreement (0.0-0.5): Opposite directions or very different magnitudes
        
        Args:
            weighted_15m: 15-minute weighted sentiment (-1 to 1)
            weighted_1h: 1-hour weighted sentiment (-1 to 1)
            
        Returns:
            Agreement score (0.0 to 1.0)
        """
        if weighted_15m is None or weighted_1h is None:
            return 0.5  # Neutral if missing data
        
        # Check if same direction
        same_direction = (weighted_15m >= 0) == (weighted_1h >= 0)
        
        # Calculate magnitude similarity (0-1)
        mag_diff = abs(abs(weighted_15m) - abs(weighted_1h))
        mag_similarity = max(0, 1 - mag_diff)
        
        if same_direction:
            # Same direction: 0.5 to 1.0 based on magnitude similarity
            return 0.5 + (mag_similarity * 0.5)
        else:
            # Opposite direction: 0.0 to 0.5 based on magnitude similarity
            return mag_similarity * 0.5
    
    def calc_node_visuals(
        self, 
        weighted_final: float, 
        agreement_score: float,
        has_trade: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate visualization properties for a node.
        
        Args:
            weighted_final: Final weighted sentiment (-1 to 1)
            agreement_score: 15m/1H agreement (0 to 1)
            has_trade: Whether a trade closed on this bar
            
        Returns:
            Dict with 'size', 'hue', 'saturation'
        """
        # Size: 4px (weak) to 16px (strong conviction)
        magnitude = abs(weighted_final) if weighted_final else 0
        size = 4 + (magnitude * 12)  # 4-16px range
        
        # Hue: based on direction
        if weighted_final is None or abs(weighted_final) < 0.1:
            hue = 'neutral'
        elif weighted_final > 0:
            hue = 'bullish'
        else:
            hue = 'bearish'
        
        # Saturation: based on agreement (0.3 muted to 1.0 vivid)
        saturation = 0.3 + (agreement_score * 0.7)
        
        return {
            'node_size': round(size, 2),
            'node_hue': hue,
            'node_saturation': round(saturation, 3)
        }
    
    # ========================================
    # INSTANCE CRUD
    # ========================================
    
    def create_instance(
        self,
        instance_id: str,
        symbol: str,
        profile_name: str = None,
        config: Dict = None,
        notes: str = None
    ) -> str:
        """
        Create a new simulation instance.
        
        Args:
            instance_id: Unique identifier (e.g., "USOIL_SIM_001")
            symbol: Trading symbol
            profile_name: AI profile name
            config: Configuration dict (will be JSON serialized)
            notes: Optional notes
            
        Returns:
            The instance_id
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        config_json = json.dumps(config) if config else None
        
        cursor.execute("""
            INSERT INTO cyto_instances 
            (instance_id, symbol, profile_name, config_snapshot, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (instance_id, symbol, profile_name, config_json, notes))
        
        conn.commit()
        conn.close()
        
        # Initialize P/L history
        self._pnl_history[instance_id] = []
        
        print(f"✓ Instance created: {instance_id}")
        return instance_id
    
    def update_instance_status(
        self, 
        instance_id: str, 
        status: str,
        total_trades: int = None,
        total_pnl: float = None,
        win_rate: float = None
    ):
        """Update instance status and stats."""
        conn = get_connection()
        cursor = conn.cursor()
        
        updates = ["status = ?"]
        params = [status]
        
        if status == 'completed':
            updates.append("completed_at = ?")
            params.append(datetime.now().isoformat())
        
        if total_trades is not None:
            updates.append("total_trades = ?")
            params.append(total_trades)
        
        if total_pnl is not None:
            updates.append("total_pnl = ?")
            params.append(total_pnl)
        
        if win_rate is not None:
            updates.append("win_rate = ?")
            params.append(win_rate)
        
        params.append(instance_id)
        
        cursor.execute(f"""
            UPDATE cyto_instances 
            SET {', '.join(updates)}
            WHERE instance_id = ?
        """, params)
        
        conn.commit()
        conn.close()
    
    def get_instance(self, instance_id: str) -> Optional[Dict]:
        """Get instance by ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cyto_instances WHERE instance_id = ?", (instance_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_all_instances(self, status: str = None) -> List[Dict]:
        """Get all instances, optionally filtered by status."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM cyto_instances WHERE status = ? ORDER BY created_at DESC",
                (status,)
            )
        else:
            cursor.execute("SELECT * FROM cyto_instances ORDER BY created_at DESC")
        
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows
    
    # ========================================
    # NODE CRUD
    # ========================================
    
    def add_node(
        self,
        instance_id: str,
        timestamp: datetime,
        vectors_15m: Dict[str, float] = None,
        weighted_15m: float = None,
        weighted_1h: float = None,
        weighted_final: float = None,
        trade_data: Dict = None
    ) -> int:
        """
        Add a node (15m bar) to the database.
        
        Args:
            instance_id: The instance this node belongs to
            timestamp: Bar timestamp
            vectors_15m: Dict of 6 sentiment vectors {"v1": 0.8, "v2": -0.3, ...}
            weighted_15m: 15-minute weighted average
            weighted_1h: 1-hour weighted average (sticky)
            weighted_final: Final blended average
            trade_data: Optional dict with trade details if trade closed this bar
            
        Returns:
            The node_id
        """
        # Calculate temporal position
        theta_slot = self.calc_theta_slot(timestamp)
        cycle_index = self.calc_cycle_index(timestamp)
        
        # Calculate agreement
        agreement_score = self.calc_agreement(weighted_15m, weighted_1h)
        
        # Process trade data
        has_trade = trade_data is not None
        raw_pnl = None
        pnl_normalized = None
        radius = None
        trade_direction = None
        
        if trade_data:
            raw_pnl = trade_data.get('pnl_raw')
            pnl_normalized = trade_data.get('pnl_normalized', raw_pnl)
            trade_direction = trade_data.get('direction')
            
            # Add to history and calculate radius
            if raw_pnl is not None:
                self.add_to_pnl_history(instance_id, raw_pnl)
                radius = self.calc_radius(raw_pnl, instance_id)
        
        # Calculate visuals
        visuals = self.calc_node_visuals(weighted_final, agreement_score, has_trade)
        
        # Insert
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cyto_nodes (
                instance_id, cycle_index, theta_slot, timestamp,
                vectors_15m, weighted_15m, weighted_1h, weighted_final, agreement_score,
                has_trade, raw_pnl, pnl_normalized, radius, trade_direction,
                node_size, node_hue, node_saturation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instance_id, cycle_index, theta_slot, timestamp.isoformat(),
            json.dumps(vectors_15m) if vectors_15m else None,
            weighted_15m, weighted_1h, weighted_final, agreement_score,
            1 if has_trade else 0, raw_pnl, pnl_normalized, radius, trade_direction,
            visuals['node_size'], visuals['node_hue'], visuals['node_saturation']
        ))
        
        node_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return node_id
    
    def get_epoch_nodes(
        self, 
        instance_id: str, 
        cycle_index: int
    ) -> List[Dict]:
        """
        Get all nodes for a specific epoch (72h cycle).
        
        Args:
            instance_id: The instance to query
            cycle_index: The epoch number
            
        Returns:
            List of node dicts
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM cyto_nodes 
            WHERE instance_id = ? AND cycle_index = ?
            ORDER BY theta_slot
        """, (instance_id, cycle_index))
        
        nodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return nodes
    
    def get_nodes_with_trades(
        self, 
        instance_id: str, 
        cycle_index: int = None
    ) -> List[Dict]:
        """Get only nodes where trades closed."""
        conn = get_connection()
        cursor = conn.cursor()
        
        if cycle_index is not None:
            cursor.execute("""
                SELECT * FROM cyto_nodes 
                WHERE instance_id = ? AND cycle_index = ? AND has_trade = 1
                ORDER BY theta_slot
            """, (instance_id, cycle_index))
        else:
            cursor.execute("""
                SELECT * FROM cyto_nodes 
                WHERE instance_id = ? AND has_trade = 1
                ORDER BY timestamp
            """, (instance_id,))
        
        nodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return nodes
    
    # ========================================
    # TRADE CRUD
    # ========================================
    
    def add_trade(
        self,
        node_id: int,
        instance_id: str,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        exit_price: float,
        lots: float,
        direction: str,
        pnl_raw: float,
        pnl_normalized: float,
        entry_vectors: Dict = None,
        exit_vectors: Dict = None,
        entry_weighted: float = None,
        exit_weighted: float = None,
        pnl_pips: float = None
    ) -> int:
        """Add a detailed trade record linked to a node."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO cyto_trades (
                node_id, instance_id,
                entry_time, exit_time, entry_price, exit_price,
                lots, direction, pnl_raw, pnl_normalized, pnl_pips,
                entry_vectors, entry_weighted, exit_vectors, exit_weighted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            node_id, instance_id,
            entry_time.isoformat(), exit_time.isoformat(),
            entry_price, exit_price,
            lots, direction, pnl_raw, pnl_normalized, pnl_pips,
            json.dumps(entry_vectors) if entry_vectors else None,
            entry_weighted,
            json.dumps(exit_vectors) if exit_vectors else None,
            exit_weighted
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def get_trades_for_node(self, node_id: int) -> List[Dict]:
        """Get all trades linked to a specific node."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cyto_trades WHERE node_id = ?", (node_id,))
        trades = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return trades
    
    # ========================================
    # QUERY HELPERS
    # ========================================
    
    def get_current_cycle(self) -> int:
        """Get the current cycle index based on now."""
        return self.calc_cycle_index(datetime.now())
    
    def get_instance_cycles(self, instance_id: str) -> List[int]:
        """Get list of all cycle indices that have data for an instance."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cycle_index FROM cyto_nodes 
            WHERE instance_id = ?
            ORDER BY cycle_index
        """, (instance_id,))
        cycles = [row['cycle_index'] for row in cursor.fetchall()]
        conn.close()
        return cycles
    
    def get_instance_stats(self, instance_id: str) -> Dict:
        """Get aggregated stats for an instance."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_nodes,
                SUM(has_trade) as total_trades,
                SUM(CASE WHEN raw_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(raw_pnl) as total_pnl,
                AVG(weighted_final) as avg_sentiment,
                AVG(agreement_score) as avg_agreement,
                MIN(timestamp) as first_bar,
                MAX(timestamp) as last_bar
            FROM cyto_nodes
            WHERE instance_id = ?
        """, (instance_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        stats = dict(row)
        if stats['total_trades'] and stats['total_trades'] > 0:
            stats['win_rate'] = stats['winning_trades'] / stats['total_trades']
        else:
            stats['win_rate'] = None
        
        return stats


# ============================================
# MAIN - Testing
# ============================================

if __name__ == '__main__':
    from cyto_schema import init_db
    
    print("\n" + "=" * 50)
    print("CytoManager Test Suite")
    print("=" * 50)
    
    # Initialize database
    init_db()
    
    # Create manager
    mgr = CytoManager()
    
    # Test 1: Temporal calculations
    print("\n📐 Testing temporal calculations...")
    
    test_times = [
        REFERENCE_EPOCH,  # Slot 0
        REFERENCE_EPOCH + timedelta(minutes=15),  # Slot 1
        REFERENCE_EPOCH + timedelta(hours=18),  # Slot 72
        REFERENCE_EPOCH + timedelta(hours=36),  # Slot 144
        REFERENCE_EPOCH + timedelta(hours=72),  # Slot 0 (next cycle)
    ]
    
    for t in test_times:
        slot = mgr.calc_theta_slot(t)
        cycle = mgr.calc_cycle_index(t)
        angle = mgr.slot_to_angle(slot)
        print(f"   {t} → Slot {slot:3d} (Cycle {cycle}) → {angle:.1f}°")
    
    # Test 2: Agreement calculation
    print("\n🤝 Testing agreement calculation...")
    
    test_agreements = [
        (0.8, 0.7, "Both bullish, similar magnitude"),
        (0.8, -0.3, "Opposite directions"),
        (-0.5, -0.6, "Both bearish, similar"),
        (0.1, 0.9, "Both bullish, different magnitude"),
    ]
    
    for w15, w1h, desc in test_agreements:
        agreement = mgr.calc_agreement(w15, w1h)
        print(f"   {w15:+.1f} vs {w1h:+.1f} → {agreement:.3f} ({desc})")
    
    # Test 3: Visual encoding
    print("\n🎨 Testing visual encoding...")
    
    test_visuals = [
        (0.9, 0.95, False, "Strong bullish, high agreement"),
        (-0.7, 0.3, True, "Bearish, low agreement, has trade"),
        (0.05, 0.5, False, "Neutral"),
    ]
    
    for wf, ag, ht, desc in test_visuals:
        vis = mgr.calc_node_visuals(wf, ag, ht)
        print(f"   {desc}:")
        print(f"      Size: {vis['node_size']:.1f}px, Hue: {vis['node_hue']}, Sat: {vis['node_saturation']:.2f}")
    
    # Test 4: Create test instance and nodes
    print("\n📊 Testing CRUD operations...")
    
    test_instance_id = f"TEST_{datetime.now().strftime('%H%M%S')}"
    
    # Create instance
    mgr.create_instance(
        instance_id=test_instance_id,
        symbol="USOIL",
        profile_name="GCLOUD_FLASH_2.0",
        config={"version": "2.0", "risk": 0.02},
        notes="Test instance"
    )
    
    # Add some nodes
    base_time = datetime.now()
    for i in range(5):
        node_time = base_time + timedelta(minutes=15 * i)
        
        # Simulate trade on every other bar
        trade_data = None
        if i % 2 == 1:
            pnl = 50 if i == 1 else -30
            trade_data = {
                'pnl_raw': pnl,
                'pnl_normalized': pnl,
                'direction': 'long'
            }
        
        node_id = mgr.add_node(
            instance_id=test_instance_id,
            timestamp=node_time,
            vectors_15m={"v1": 0.5 + i*0.1, "v2": -0.2, "v3": 0.3, "v4": 0.1, "v5": -0.1, "v6": 0.4},
            weighted_15m=0.3 + i*0.1,
            weighted_1h=0.4,
            weighted_final=0.35 + i*0.05,
            trade_data=trade_data
        )
        print(f"   Node {node_id} created at slot {mgr.calc_theta_slot(node_time)}")
    
    # Get stats
    stats = mgr.get_instance_stats(test_instance_id)
    print(f"\n📈 Instance stats:")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total trades: {stats['total_trades']}")
    print(f"   Total P/L: ${stats['total_pnl']:.2f}")
    print(f"   Avg sentiment: {stats['avg_sentiment']:.3f}")
    
    print("\n" + "=" * 50)
    print("✓ All tests passed")
    print("=" * 50 + "\n")
