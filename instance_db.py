"""
APEX Instance Database Manager
==============================
Manages per-instance tables for algorithm trading:
- Positions (with pyramiding support)
- Sentiment readings
- State transitions
- Markov matrices

Each algorithm instance gets its own set of tables.
Unified tables track all instances and profiles.
"""

import os
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from contextlib import contextmanager


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

DB_PATH = os.getenv("APEX_DB_PATH", "apex_trading.db")

# Matrix bias states
MATRIX_BIAS = {
    -2: "Strong Bearish",
    -1: "Bearish",
    0: "Neutral",
    1: "Bullish",
    2: "Strong Bullish"
}

def score_to_bias(score: float) -> tuple:
    """Convert composite score (-1 to +1) to matrix bias state"""
    if score <= -0.6:
        return -2, "Strong Bearish"
    elif score <= -0.2:
        return -1, "Bearish"
    elif score <= 0.2:
        return 0, "Neutral"
    elif score <= 0.6:
        return 1, "Bullish"
    else:
        return 2, "Strong Bullish"


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE CONNECTION
# ═══════════════════════════════════════════════════════════════════════════

@contextmanager
def get_db(db_path: str = DB_PATH):
    """Context manager for database connections"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# UNIFIED TABLES (created once)
# ═══════════════════════════════════════════════════════════════════════════

def init_unified_tables(db_path: str = DB_PATH):
    """Initialize the unified tables for profiles and instances"""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # ═══════════════════════════════════════════════════════════════════
        # PROFILES TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                
                -- Sentiment Config
                sentiment_weights TEXT,
                sentiment_model TEXT DEFAULT 'claude-sonnet-4',
                sentiment_threshold REAL DEFAULT 0.3,
                
                -- Position Config
                position_sizing TEXT,
                risk_config TEXT,
                entry_rules TEXT,
                exit_rules TEXT,
                
                -- Pyramiding Config
                pyramid_enabled INTEGER DEFAULT 0,
                pyramid_max_levels INTEGER DEFAULT 3,
                pyramid_config TEXT,
                
                -- Running Analytics
                total_trades INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0.0,
                win_rate REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_signal_at TEXT
            )
        """)
        
        # ═══════════════════════════════════════════════════════════════════
        # ALGORITHM INSTANCES TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS algorithm_instances (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                account_type TEXT DEFAULT 'SIM',
                profile_id TEXT,
                status TEXT DEFAULT 'ACTIVE',
                
                -- Table Names (for reference)
                positions_table TEXT,
                sentiment_table TEXT,
                transitions_table TEXT,
                matrices_table TEXT,
                
                -- Lifecycle
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                archived_at TEXT,
                last_activity_at TEXT,
                
                notes TEXT,
                
                FOREIGN KEY (profile_id) REFERENCES profiles(id)
            )
        """)
        
        # Indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_instances_symbol 
            ON algorithm_instances(symbol, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_instances_status 
            ON algorithm_instances(status, archived_at DESC)
        """)
        
        print("[DB] Unified tables initialized")


# ═══════════════════════════════════════════════════════════════════════════
# INSTANCE TABLE CREATION
# ═══════════════════════════════════════════════════════════════════════════

def create_instance_tables(instance_id: str, db_path: str = DB_PATH):
    """Create all tables for a new algorithm instance"""
    
    # Sanitize instance_id for table names
    safe_id = instance_id.replace("-", "_").lower()
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # ═══════════════════════════════════════════════════════════════════
        # POSITIONS TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS positions_{safe_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                
                -- Pyramiding
                pyramid_level INTEGER DEFAULT 1,
                parent_position_id INTEGER,
                trade_group_id TEXT,
                
                -- Entry
                entry_price REAL,
                entry_time TEXT,
                entry_ticket INTEGER,
                
                -- Exit
                exit_price REAL,
                exit_time TEXT,
                exit_reason TEXT,
                
                -- Sizing
                lots REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                
                -- P&L
                unrealized_pnl REAL DEFAULT 0.0,
                realized_pnl REAL,
                commission REAL DEFAULT 0.0,
                swap REAL DEFAULT 0.0,
                slippage REAL,
                fill_latency_ms INTEGER,
                
                -- Analytics
                max_favorable REAL,
                max_adverse REAL,
                
                -- Signal Source
                signal_source TEXT,
                signal_data TEXT,
                market_conditions TEXT,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ═══════════════════════════════════════════════════════════════════
        # SENTIMENT TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS sentiment_{safe_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                
                -- Category 1: Price Action
                price_action_text TEXT,
                price_action_score REAL,
                
                -- Category 2: Key Levels
                key_levels_text TEXT,
                key_levels_score REAL,
                
                -- Category 3: Momentum
                momentum_text TEXT,
                momentum_score REAL,
                
                -- Category 4: Volume
                volume_text TEXT,
                volume_score REAL,
                
                -- Category 5: Structure
                structure_text TEXT,
                structure_score REAL,
                
                -- Composite
                summary TEXT,
                composite_score REAL,
                matrix_bias INTEGER,
                matrix_bias_label TEXT,
                
                -- Source
                source_model TEXT,
                source_type TEXT DEFAULT 'API',
                raw_response TEXT,
                processing_time_ms INTEGER,
                tokens_used INTEGER,
                confidence REAL,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ═══════════════════════════════════════════════════════════════════
        # STATE TRANSITIONS TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS transitions_{safe_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                
                -- State Change
                from_state INTEGER NOT NULL,
                to_state INTEGER NOT NULL,
                from_state_label TEXT,
                to_state_label TEXT,
                
                -- Trigger
                trigger_source TEXT,
                trigger_id INTEGER,
                trigger_data TEXT,
                
                -- Scores at Transition
                composite_score REAL,
                price_action_score REAL,
                key_levels_score REAL,
                momentum_score REAL,
                volume_score REAL,
                structure_score REAL,
                
                -- Market Context
                price_at_transition REAL,
                atr_at_transition REAL,
                volume_at_transition REAL,
                
                session TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ═══════════════════════════════════════════════════════════════════
        # MARKOV MATRICES TABLE
        # ═══════════════════════════════════════════════════════════════════
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS matrices_{safe_id} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT,
                timeframe TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                -- 5x5 Matrix
                matrix_data TEXT NOT NULL,
                
                -- Stats
                total_transitions INTEGER DEFAULT 0,
                stability_score REAL,
                trend_bias REAL,
                
                lookback_periods INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for all tables
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_positions_{safe_id}_status 
            ON positions_{safe_id}(status, created_at DESC)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_sentiment_{safe_id}_tf_ts 
            ON sentiment_{safe_id}(timeframe, timestamp DESC)
        """)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_transitions_{safe_id}_tf_ts 
            ON transitions_{safe_id}(timeframe, timestamp DESC)
        """)
        
        print(f"[DB] Instance tables created for: {instance_id}")
        
        return {
            "positions_table": f"positions_{safe_id}",
            "sentiment_table": f"sentiment_{safe_id}",
            "transitions_table": f"transitions_{safe_id}",
            "matrices_table": f"matrices_{safe_id}"
        }


# ═══════════════════════════════════════════════════════════════════════════
# INSTANCE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def create_instance(
    symbol: str,
    display_name: str = None,
    account_type: str = "SIM",
    profile_id: str = None,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Create a new algorithm instance with all tables"""
    
    instance_id = f"{symbol.lower()}_{account_type.lower()}_{uuid.uuid4().hex[:8]}"
    
    if not display_name:
        display_name = f"{symbol}.{account_type.lower()}"
    
    # Create the instance tables
    tables = create_instance_tables(instance_id, db_path)
    
    # Register in unified table
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO algorithm_instances (
                id, display_name, symbol, account_type, profile_id, status,
                positions_table, sentiment_table, transitions_table, matrices_table,
                created_at, last_activity_at
            ) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?)
        """, (
            instance_id, display_name, symbol, account_type, profile_id,
            tables["positions_table"], tables["sentiment_table"],
            tables["transitions_table"], tables["matrices_table"],
            datetime.utcnow().isoformat(), datetime.utcnow().isoformat()
        ))
    
    return {
        "id": instance_id,
        "display_name": display_name,
        "symbol": symbol,
        "account_type": account_type,
        "profile_id": profile_id,
        "status": "ACTIVE",
        **tables
    }


def archive_instance(instance_id: str, db_path: str = DB_PATH) -> bool:
    """Archive an instance (soft delete)"""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE algorithm_instances 
            SET status = 'ARCHIVED', archived_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), instance_id))
        return cursor.rowcount > 0


def get_instances(
    symbol: str = None,
    status: str = None,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Get algorithm instances, optionally filtered"""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM algorithm_instances WHERE 1=1"
        params = []
        
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END, archived_at DESC, created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]


def get_instance(instance_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """Get a single instance by ID"""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM algorithm_instances WHERE id = ?", (instance_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

def create_profile(
    name: str,
    symbol: str,
    sentiment_weights: dict = None,
    db_path: str = DB_PATH
) -> str:
    """Create a new profile"""
    profile_id = f"profile_{uuid.uuid4().hex[:8]}"
    
    default_weights = {
        "price_action": 0.25,
        "key_levels": 0.20,
        "momentum": 0.20,
        "volume": 0.15,
        "structure": 0.20
    }
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO profiles (id, name, symbol, sentiment_weights)
            VALUES (?, ?, ?, ?)
        """, (
            profile_id, name, symbol,
            json.dumps(sentiment_weights or default_weights)
        ))
    
    return profile_id


def get_profiles(symbol: str = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Get profiles, optionally filtered by symbol"""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute(
                "SELECT * FROM profiles WHERE symbol = ? ORDER BY name",
                (symbol,)
            )
        else:
            cursor.execute("SELECT * FROM profiles ORDER BY symbol, name")
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════════════════
# DATA ACCESS HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_positions(
    instance_id: str,
    status: str = None,
    limit: int = 100,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Get positions for an instance"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        return []
    
    table = instance["positions_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += f" ORDER BY created_at DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_sentiment_readings(
    instance_id: str,
    timeframe: str = None,
    limit: int = 100,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Get sentiment readings for an instance"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        return []
    
    table = instance["sentiment_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_transitions(
    instance_id: str,
    timeframe: str = None,
    limit: int = 100,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """Get state transitions for an instance"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        return []
    
    table = instance["transitions_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        query = f"SELECT * FROM {table} WHERE 1=1"
        params = []
        
        if timeframe:
            query += " AND timeframe = ?"
            params.append(timeframe)
        
        query += f" ORDER BY timestamp DESC LIMIT {limit}"
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_latest_matrix(
    instance_id: str,
    timeframe: str,
    db_path: str = DB_PATH
) -> Optional[Dict[str, Any]]:
    """Get the most recent cached matrix for an instance/timeframe"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        return None
    
    table = instance["matrices_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT * FROM {table} 
            WHERE timeframe = ? 
            ORDER BY updated_at DESC LIMIT 1
        """, (timeframe,))
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            result["matrix_data"] = json.loads(result["matrix_data"])
            return result
        return None


# ═══════════════════════════════════════════════════════════════════════════
# DATA WRITE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def insert_sentiment(
    instance_id: str,
    data: Dict[str, Any],
    db_path: str = DB_PATH
) -> int:
    """Insert a sentiment reading and check for state transition"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        raise ValueError(f"Instance not found: {instance_id}")
    
    table = instance["sentiment_table"]
    
    # Calculate composite score and matrix bias
    weights = {"price_action": 0.25, "key_levels": 0.20, "momentum": 0.20, "volume": 0.15, "structure": 0.20}
    
    composite = 0.0
    for key, weight in weights.items():
        score_key = f"{key}_score"
        if score_key in data and data[score_key] is not None:
            composite += data[score_key] * weight
    
    bias_value, bias_label = score_to_bias(composite)
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute(f"""
            INSERT INTO {table} (
                profile_id, symbol, timeframe, timestamp,
                price_action_text, price_action_score,
                key_levels_text, key_levels_score,
                momentum_text, momentum_score,
                volume_text, volume_score,
                structure_text, structure_score,
                summary, composite_score, matrix_bias, matrix_bias_label,
                source_model, source_type, raw_response, processing_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("profile_id"),
            data.get("symbol"),
            data.get("timeframe"),
            data.get("timestamp"),
            data.get("price_action_text"),
            data.get("price_action_score"),
            data.get("key_levels_text"),
            data.get("key_levels_score"),
            data.get("momentum_text"),
            data.get("momentum_score"),
            data.get("volume_text"),
            data.get("volume_score"),
            data.get("structure_text"),
            data.get("structure_score"),
            data.get("summary"),
            composite,
            bias_value,
            bias_label,
            data.get("source_model"),
            data.get("source_type", "API"),
            data.get("raw_response"),
            data.get("processing_time_ms")
        ))
        
        sentiment_id = cursor.lastrowid
        
        # Check for state transition
        _check_and_record_transition(
            cursor, instance, data.get("timeframe"), 
            bias_value, bias_label, sentiment_id, data, composite
        )
        
        return sentiment_id


def _check_and_record_transition(
    cursor, instance: dict, timeframe: str,
    new_bias: int, new_bias_label: str,
    trigger_id: int, data: dict, composite_score: float
):
    """Check if state changed and record transition"""
    sentiment_table = instance["sentiment_table"]
    transitions_table = instance["transitions_table"]
    
    # Get previous state
    cursor.execute(f"""
        SELECT matrix_bias, matrix_bias_label FROM {sentiment_table}
        WHERE timeframe = ? AND id != ?
        ORDER BY timestamp DESC LIMIT 1
    """, (timeframe, trigger_id))
    
    prev = cursor.fetchone()
    
    if prev is None:
        # First reading, no transition
        return
    
    prev_bias = prev["matrix_bias"]
    prev_bias_label = prev["matrix_bias_label"]
    
    if prev_bias == new_bias:
        # No state change
        return
    
    # Record transition
    cursor.execute(f"""
        INSERT INTO {transitions_table} (
            profile_id, symbol, timeframe, timestamp,
            from_state, to_state, from_state_label, to_state_label,
            trigger_source, trigger_id, trigger_data,
            composite_score, price_action_score, key_levels_score,
            momentum_score, volume_score, structure_score,
            price_at_transition
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("profile_id"),
        data.get("symbol"),
        timeframe,
        data.get("timestamp"),
        prev_bias,
        new_bias,
        prev_bias_label,
        new_bias_label,
        "SENTIMENT",
        trigger_id,
        json.dumps({"composite": composite_score}),
        composite_score,
        data.get("price_action_score"),
        data.get("key_levels_score"),
        data.get("momentum_score"),
        data.get("volume_score"),
        data.get("structure_score"),
        data.get("price_at_transition")
    ))


def insert_position(
    instance_id: str,
    data: Dict[str, Any],
    db_path: str = DB_PATH
) -> int:
    """Insert a new position"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        raise ValueError(f"Instance not found: {instance_id}")
    
    table = instance["positions_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute(f"""
            INSERT INTO {table} (
                profile_id, symbol, direction, status,
                pyramid_level, parent_position_id, trade_group_id,
                lots, stop_loss, take_profit,
                signal_source, signal_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("profile_id"),
            data.get("symbol"),
            data.get("direction"),
            data.get("status", "PENDING"),
            data.get("pyramid_level", 1),
            data.get("parent_position_id"),
            data.get("trade_group_id"),
            data.get("lots"),
            data.get("stop_loss"),
            data.get("take_profit"),
            data.get("signal_source"),
            json.dumps(data.get("signal_data")) if data.get("signal_data") else None
        ))
        
        return cursor.lastrowid


# ═══════════════════════════════════════════════════════════════════════════
# MATRIX COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

def compute_and_cache_matrix(
    instance_id: str,
    timeframe: str,
    lookback: int = 1000,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Compute transition matrix from history and cache it"""
    instance = get_instance(instance_id, db_path)
    if not instance:
        raise ValueError(f"Instance not found: {instance_id}")
    
    transitions_table = instance["transitions_table"]
    matrices_table = instance["matrices_table"]
    
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Count transitions
        cursor.execute(f"""
            SELECT from_state, to_state, COUNT(*) as count
            FROM {transitions_table}
            WHERE timeframe = ?
            GROUP BY from_state, to_state
            ORDER BY from_state, to_state
        """, (timeframe,))
        
        # Build 5x5 matrix (states -2 to +2, mapped to indices 0-4)
        counts = [[0] * 5 for _ in range(5)]
        total = 0
        
        for row in cursor.fetchall():
            from_idx = row["from_state"] + 2  # -2 -> 0, +2 -> 4
            to_idx = row["to_state"] + 2
            counts[from_idx][to_idx] = row["count"]
            total += row["count"]
        
        # Convert to probabilities
        matrix = []
        for row in counts:
            row_sum = sum(row)
            if row_sum > 0:
                matrix.append([c / row_sum for c in row])
            else:
                # No transitions from this state, use uniform
                matrix.append([0.2] * 5)
        
        # Calculate stats
        stability = sum(matrix[i][i] for i in range(5)) / 5  # Average diagonal
        
        # Trend bias: weighted average of next state
        trend_bias = 0.0
        for i in range(5):
            for j in range(5):
                trend_bias += matrix[i][j] * (j - 2)  # j-2 gives state value
        trend_bias /= 5
        
        # Cache the matrix
        cursor.execute(f"""
            INSERT INTO {matrices_table} (
                profile_id, timeframe, updated_at, matrix_data,
                total_transitions, stability_score, trend_bias, lookback_periods
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instance.get("profile_id"),
            timeframe,
            datetime.utcnow().isoformat(),
            json.dumps(matrix),
            total,
            stability,
            trend_bias,
            lookback
        ))
        
        return {
            "matrix": matrix,
            "total_transitions": total,
            "stability_score": stability,
            "trend_bias": trend_bias
        }


# ═══════════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════

def init_database(db_path: str = DB_PATH):
    """Initialize the complete database"""
    init_unified_tables(db_path)
    print(f"[DB] Database initialized: {db_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APEX Instance Database Manager")
    parser.add_argument("--init", action="store_true", help="Initialize database")
    parser.add_argument("--create-instance", type=str, help="Create instance for symbol")
    parser.add_argument("--list-instances", type=str, help="List instances for symbol")
    parser.add_argument("--db", default=DB_PATH, help="Database path")
    
    args = parser.parse_args()
    
    if args.init:
        init_database(args.db)
    
    if args.create_instance:
        result = create_instance(args.create_instance, db_path=args.db)
        print(f"Created instance: {json.dumps(result, indent=2)}")
    
    if args.list_instances:
        instances = get_instances(symbol=args.list_instances, db_path=args.db)
        for inst in instances:
            print(f"  {inst['id']} - {inst['display_name']} [{inst['status']}]")
