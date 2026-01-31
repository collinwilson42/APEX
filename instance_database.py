"""
APEX Instance Database Manager
==============================
Manages algorithm instances and their associated tables:
- positions_{instance_id}
- sentiment_{instance_id}
- state_transitions_{instance_id}
- markov_matrices_{instance_id}

Auto-creates tables on instance creation, archives on close.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class AlgorithmInstance:
    """Represents an algorithm instance"""
    id: str
    display_name: str
    symbol: str
    account_type: str  # SIM | LIVE
    profile_id: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE | PAUSED | ARCHIVED
    created_at: str = ""
    archived_at: Optional[str] = None
    last_activity_at: Optional[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"


@dataclass
class Profile:
    """Trading profile configuration"""
    id: str
    name: str
    symbol: str
    status: str = "ACTIVE"  # ACTIVE | PAUSED | ARCHIVED
    
    # Sentiment config
    sentiment_weights: str = '{"price_action": 0.20, "key_levels": 0.20, "momentum": 0.20, "volume": 0.20, "structure": 0.20}'
    sentiment_model: str = "claude-sonnet-4-20250514"
    sentiment_threshold: float = 0.3
    
    # Position config
    position_sizing: str = '{"base_lots": 0.1, "max_lots": 1.0}'
    risk_config: str = '{"max_drawdown_pct": 5.0, "daily_loss_limit": 500}'
    entry_rules: str = '{}'
    exit_rules: str = '{}'
    
    # Pyramid config
    pyramid_enabled: int = 1
    pyramid_max_levels: int = 3
    pyramid_config: str = '{"add_threshold": 0.7, "lot_scaling": [1, 2, 3]}'
    
    # Analytics
    total_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    
    created_at: str = ""
    updated_at: str = ""
    last_signal_at: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
        if not self.updated_at:
            self.updated_at = self.created_at


# ═══════════════════════════════════════════════════════════════════════════
# TABLE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

POSITIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions_{instance_id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,  -- LONG | SHORT | FLAT
    status TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING | OPEN | CLOSING | CLOSED
    
    -- Pyramiding
    pyramid_level INTEGER DEFAULT 1,
    parent_position_id INTEGER,
    trade_group_id TEXT,  -- Groups all pyramid entries together
    
    -- Entry
    entry_price REAL,
    entry_time TEXT,
    entry_ticket INTEGER,
    
    -- Exit
    exit_price REAL,
    exit_time TEXT,
    exit_reason TEXT,  -- TP_HIT | SL_HIT | MANUAL | SIGNAL | TIMEOUT | PYRAMID_CLOSE
    
    -- Sizing
    lots REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    
    -- P&L
    unrealized_pnl REAL DEFAULT 0,
    realized_pnl REAL,
    commission REAL DEFAULT 0,
    swap REAL DEFAULT 0,
    slippage REAL,
    fill_latency_ms INTEGER,
    
    -- Analytics
    max_favorable REAL,
    max_adverse REAL,
    market_conditions TEXT,  -- JSON snapshot
    
    -- Signal
    signal_source TEXT,  -- SENTIMENT | PROFILE | MANUAL
    signal_data TEXT,  -- JSON
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

SENTIMENT_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sentiment_{instance_id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,  -- 1m | 15m
    timestamp TEXT NOT NULL,
    
    -- Category 1: Price Action
    price_action_text TEXT,
    price_action_score REAL,  -- -1.0 to +1.0
    
    -- Category 2: Key Levels
    key_levels_text TEXT,
    key_levels_score REAL,  -- -1.0 to +1.0
    
    -- Category 3: Momentum
    momentum_text TEXT,
    momentum_score REAL,  -- -1.0 to +1.0
    
    -- Category 4: Volume
    volume_text TEXT,
    volume_score REAL,  -- -1.0 to +1.0
    
    -- Category 5: Structure
    structure_text TEXT,
    structure_score REAL,  -- -1.0 to +1.0
    
    -- Composite
    summary TEXT,
    composite_score REAL,
    matrix_bias INTEGER,  -- -2, -1, 0, +1, +2
    matrix_bias_label TEXT,  -- Strong Bearish, Bearish, Neutral, Bullish, Strong Bullish
    
    -- Source
    source_model TEXT,  -- claude-opus-4, claude-sonnet-4, gemini-2.0-flash
    source_type TEXT,  -- API | MOCK | MANUAL
    raw_response TEXT,
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

STATE_TRANSITIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS state_transitions_{instance_id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    
    -- State Change
    from_state INTEGER NOT NULL,  -- -2, -1, 0, +1, +2
    to_state INTEGER NOT NULL,
    from_state_label TEXT,
    to_state_label TEXT,
    
    -- Trigger
    trigger_source TEXT,  -- SENTIMENT | PRICE_ACTION | MANUAL
    trigger_id INTEGER,  -- FK to sentiment or position
    trigger_data TEXT,  -- JSON
    
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
    
    session TEXT,  -- ASIA | LONDON | NY | OVERLAP
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

MARKOV_MATRICES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS markov_matrices_{instance_id} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT,
    timeframe TEXT NOT NULL,
    
    -- Matrix Data (5x5 = 25 values)
    matrix_data TEXT NOT NULL,  -- JSON: [[p00, p01, ...], [p10, ...], ...]
    
    -- Transition Counts (for incremental updates)
    transition_counts TEXT,  -- JSON: [[n00, n01, ...], ...]
    
    -- Stats
    total_transitions INTEGER DEFAULT 0,
    stability_score REAL,  -- Diagonal dominance
    trend_bias REAL,  -- Overall directional tendency
    current_state INTEGER,  -- Last known state
    
    lookback_periods INTEGER,
    
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

PROFILES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    status TEXT DEFAULT 'ACTIVE',
    
    -- Sentiment Config
    sentiment_weights TEXT,
    sentiment_model TEXT,
    sentiment_threshold REAL DEFAULT 0.3,
    
    -- Position Config
    position_sizing TEXT,
    risk_config TEXT,
    entry_rules TEXT,
    exit_rules TEXT,
    
    -- Pyramid Config
    pyramid_enabled INTEGER DEFAULT 1,
    pyramid_max_levels INTEGER DEFAULT 3,
    pyramid_config TEXT,
    
    -- Analytics
    total_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0,
    win_rate REAL DEFAULT 0,
    profit_factor REAL DEFAULT 0,
    sharpe_ratio REAL DEFAULT 0,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_signal_at TEXT
)
"""

INSTANCES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS algorithm_instances (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    symbol TEXT NOT NULL,
    account_type TEXT NOT NULL,  -- SIM | LIVE
    profile_id TEXT,
    status TEXT DEFAULT 'ACTIVE',  -- ACTIVE | PAUSED | ARCHIVED
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    archived_at TEXT,
    last_activity_at TEXT,
    notes TEXT,
    
    FOREIGN KEY (profile_id) REFERENCES profiles(id)
)
"""


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE MANAGER
# ═══════════════════════════════════════════════════════════════════════════

class InstanceDatabaseManager:
    """Manages algorithm instances and their tables"""
    
    # Matrix bias mapping
    BIAS_LABELS = {
        -2: "Strong Bearish",
        -1: "Bearish",
        0: "Neutral",
        1: "Bullish",
        2: "Strong Bullish"
    }
    
    def __init__(self, db_path: str = "apex_instances.db"):
        self.db_path = db_path
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize core tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Create unified tables
        cursor.execute(PROFILES_TABLE_SCHEMA)
        cursor.execute(INSTANCES_TABLE_SCHEMA)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_instances_symbol 
            ON algorithm_instances(symbol, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_instances_status 
            ON algorithm_instances(status, archived_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_profiles_symbol 
            ON profiles(symbol, status)
        """)
        
        conn.commit()
        conn.close()
    
    def _sanitize_instance_id(self, instance_id: str) -> str:
        """Sanitize instance ID for use in table names"""
        return instance_id.replace("-", "_").replace(".", "_").lower()
    
    # ═══════════════════════════════════════════════════════════════════════
    # INSTANCE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def create_instance(self, symbol: str, account_type: str = "SIM", 
                       display_name: str = None, profile_id: str = None) -> AlgorithmInstance:
        """
        Create a new algorithm instance and all associated tables.
        
        Args:
            symbol: Trading symbol (e.g., "XAUJ26")
            account_type: "SIM" or "LIVE"
            display_name: Optional friendly name
            profile_id: Optional profile to link
        
        Returns:
            AlgorithmInstance object
        """
        # Generate unique instance ID
        short_uuid = str(uuid.uuid4())[:8]
        instance_id = f"{symbol.lower()}_{account_type.lower()}_{short_uuid}"
        safe_id = self._sanitize_instance_id(instance_id)
        
        if not display_name:
            display_name = f"{symbol} {account_type.upper()}"
        
        instance = AlgorithmInstance(
            id=instance_id,
            display_name=display_name,
            symbol=symbol.upper(),
            account_type=account_type.upper(),
            profile_id=profile_id,
            status="ACTIVE"
        )
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # Insert instance record
            cursor.execute("""
                INSERT INTO algorithm_instances 
                (id, display_name, symbol, account_type, profile_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                instance.id,
                instance.display_name,
                instance.symbol,
                instance.account_type,
                instance.profile_id,
                instance.status,
                instance.created_at
            ))
            
            # Create instance-specific tables
            cursor.execute(POSITIONS_TABLE_SCHEMA.format(instance_id=safe_id))
            cursor.execute(SENTIMENT_TABLE_SCHEMA.format(instance_id=safe_id))
            cursor.execute(STATE_TRANSITIONS_TABLE_SCHEMA.format(instance_id=safe_id))
            cursor.execute(MARKOV_MATRICES_TABLE_SCHEMA.format(instance_id=safe_id))
            
            # Create indexes for instance tables
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
                ON state_transitions_{safe_id}(timeframe, timestamp DESC)
            """)
            
            # Initialize empty Markov matrices for both timeframes
            empty_matrix = json.dumps([[0.2] * 5 for _ in range(5)])
            empty_counts = json.dumps([[0] * 5 for _ in range(5)])
            
            for tf in ['1m', '15m']:
                cursor.execute(f"""
                    INSERT INTO markov_matrices_{safe_id} 
                    (profile_id, timeframe, matrix_data, transition_counts, current_state)
                    VALUES (?, ?, ?, ?, ?)
                """, (profile_id, tf, empty_matrix, empty_counts, 0))
            
            conn.commit()
            print(f"[InstanceDB] Created instance: {instance_id}")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Failed to create instance: {e}")
        finally:
            conn.close()
        
        return instance
    
    def archive_instance(self, instance_id: str) -> bool:
        """
        Archive an instance (soft delete).
        Tables are preserved for historical analysis.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE algorithm_instances 
                SET status = 'ARCHIVED', 
                    archived_at = ?
                WHERE id = ?
            """, (datetime.utcnow().isoformat() + "Z", instance_id))
            
            conn.commit()
            print(f"[InstanceDB] Archived instance: {instance_id}")
            return True
            
        except Exception as e:
            print(f"[InstanceDB] Archive failed: {e}")
            return False
        finally:
            conn.close()
    
    def restore_instance(self, instance_id: str) -> bool:
        """Restore an archived instance to active status"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE algorithm_instances 
                SET status = 'ACTIVE', 
                    archived_at = NULL
                WHERE id = ?
            """, (instance_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[InstanceDB] Restore failed: {e}")
            return False
        finally:
            conn.close()
    
    def get_instance(self, instance_id: str) -> Optional[AlgorithmInstance]:
        """Get a single instance by ID"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM algorithm_instances WHERE id = ?", (instance_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return AlgorithmInstance(
            id=row["id"],
            display_name=row["display_name"],
            symbol=row["symbol"],
            account_type=row["account_type"],
            profile_id=row["profile_id"],
            status=row["status"],
            created_at=row["created_at"],
            archived_at=row["archived_at"],
            last_activity_at=row["last_activity_at"],
            notes=row["notes"] or ""
        )
    
    def get_instances_by_symbol(self, symbol: str) -> Dict[str, List[AlgorithmInstance]]:
        """
        Get all instances for a symbol, grouped by status.
        
        Returns:
            {"active": [...], "archived": [...]}
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM algorithm_instances 
            WHERE symbol = ?
            ORDER BY 
                CASE WHEN status = 'ACTIVE' THEN 0 
                     WHEN status = 'PAUSED' THEN 1 
                     ELSE 2 END,
                COALESCE(archived_at, created_at) DESC
        """, (symbol.upper(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {"active": [], "archived": []}
        
        for row in rows:
            instance = AlgorithmInstance(
                id=row["id"],
                display_name=row["display_name"],
                symbol=row["symbol"],
                account_type=row["account_type"],
                profile_id=row["profile_id"],
                status=row["status"],
                created_at=row["created_at"],
                archived_at=row["archived_at"],
                last_activity_at=row["last_activity_at"],
                notes=row["notes"] or ""
            )
            
            if row["status"] in ("ACTIVE", "PAUSED"):
                result["active"].append(instance)
            else:
                result["archived"].append(instance)
        
        return result
    
    def get_all_instances(self) -> Dict[str, List[AlgorithmInstance]]:
        """Get all instances grouped by status"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM algorithm_instances 
            ORDER BY 
                CASE WHEN status = 'ACTIVE' THEN 0 
                     WHEN status = 'PAUSED' THEN 1 
                     ELSE 2 END,
                COALESCE(archived_at, created_at) DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        result = {"active": [], "archived": []}
        
        for row in rows:
            instance = AlgorithmInstance(
                id=row["id"],
                display_name=row["display_name"],
                symbol=row["symbol"],
                account_type=row["account_type"],
                profile_id=row["profile_id"],
                status=row["status"],
                created_at=row["created_at"],
                archived_at=row["archived_at"],
                last_activity_at=row["last_activity_at"],
                notes=row["notes"] or ""
            )
            
            if row["status"] in ("ACTIVE", "PAUSED"):
                result["active"].append(instance)
            else:
                result["archived"].append(instance)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════
    # PROFILE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════
    
    def create_profile(self, name: str, symbol: str, **kwargs) -> Profile:
        """Create a new trading profile"""
        profile_id = str(uuid.uuid4())[:12]
        
        profile = Profile(
            id=profile_id,
            name=name,
            symbol=symbol.upper(),
            **kwargs
        )
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO profiles (
                id, name, symbol, status,
                sentiment_weights, sentiment_model, sentiment_threshold,
                position_sizing, risk_config, entry_rules, exit_rules,
                pyramid_enabled, pyramid_max_levels, pyramid_config,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile.id, profile.name, profile.symbol, profile.status,
            profile.sentiment_weights, profile.sentiment_model, profile.sentiment_threshold,
            profile.position_sizing, profile.risk_config, profile.entry_rules, profile.exit_rules,
            profile.pyramid_enabled, profile.pyramid_max_levels, profile.pyramid_config,
            profile.created_at, profile.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return profile
    
    def get_profiles_by_symbol(self, symbol: str) -> List[Profile]:
        """Get all profiles for a symbol"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM profiles 
            WHERE symbol = ? AND status != 'ARCHIVED'
            ORDER BY created_at DESC
        """, (symbol.upper(),))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_profile(row) for row in rows]
    
    def _row_to_profile(self, row) -> Profile:
        return Profile(
            id=row["id"],
            name=row["name"],
            symbol=row["symbol"],
            status=row["status"],
            sentiment_weights=row["sentiment_weights"],
            sentiment_model=row["sentiment_model"],
            sentiment_threshold=row["sentiment_threshold"],
            position_sizing=row["position_sizing"],
            risk_config=row["risk_config"],
            entry_rules=row["entry_rules"],
            exit_rules=row["exit_rules"],
            pyramid_enabled=row["pyramid_enabled"],
            pyramid_max_levels=row["pyramid_max_levels"],
            pyramid_config=row["pyramid_config"],
            total_trades=row["total_trades"],
            total_pnl=row["total_pnl"],
            win_rate=row["win_rate"],
            profit_factor=row["profit_factor"],
            sharpe_ratio=row["sharpe_ratio"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_signal_at=row["last_signal_at"]
        )
    
    # ═══════════════════════════════════════════════════════════════════════
    # SENTIMENT OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def save_sentiment(self, instance_id: str, sentiment_data: dict) -> int:
        """Save a sentiment reading to the instance's table"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        # Calculate matrix bias from composite score
        composite = sentiment_data.get("composite_score", 0)
        matrix_bias = self._score_to_bias(composite)
        bias_label = self.BIAS_LABELS.get(matrix_bias, "Neutral")
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            INSERT INTO sentiment_{safe_id} (
                profile_id, symbol, timeframe, timestamp,
                price_action_text, price_action_score,
                key_levels_text, key_levels_score,
                momentum_text, momentum_score,
                volume_text, volume_score,
                structure_text, structure_score,
                summary, composite_score, matrix_bias, matrix_bias_label,
                source_model, source_type, raw_response, processing_time_ms, tokens_used
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sentiment_data.get("profile_id"),
            sentiment_data.get("symbol"),
            sentiment_data.get("timeframe"),
            sentiment_data.get("timestamp"),
            sentiment_data.get("price_action_text"),
            sentiment_data.get("price_action_score"),
            sentiment_data.get("key_levels_text"),
            sentiment_data.get("key_levels_score"),
            sentiment_data.get("momentum_text"),
            sentiment_data.get("momentum_score"),
            sentiment_data.get("volume_text"),
            sentiment_data.get("volume_score"),
            sentiment_data.get("structure_text"),
            sentiment_data.get("structure_score"),
            sentiment_data.get("summary"),
            composite,
            matrix_bias,
            bias_label,
            sentiment_data.get("source_model"),
            sentiment_data.get("source_type"),
            sentiment_data.get("raw_response"),
            sentiment_data.get("processing_time_ms"),
            sentiment_data.get("tokens_used")
        ))
        
        reading_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Check for state transition
        self._check_state_transition(instance_id, sentiment_data, matrix_bias)
        
        return reading_id
    
    def get_latest_sentiment(self, instance_id: str, timeframe: str) -> Optional[dict]:
        """Get the most recent sentiment reading"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM sentiment_{safe_id}
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (timeframe,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return dict(row)
    
    def get_sentiment_history(self, instance_id: str, timeframe: str, 
                             limit: int = 100) -> List[dict]:
        """Get sentiment history"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM sentiment_{safe_id}
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def _score_to_bias(self, score: float) -> int:
        """Convert composite score to matrix bias state"""
        if score <= -0.6:
            return -2
        elif score <= -0.2:
            return -1
        elif score <= 0.2:
            return 0
        elif score <= 0.6:
            return 1
        else:
            return 2
    
    def _check_state_transition(self, instance_id: str, sentiment_data: dict, new_bias: int):
        """Check if state changed and record transition"""
        safe_id = self._sanitize_instance_id(instance_id)
        timeframe = sentiment_data.get("timeframe")
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get previous state from markov matrix table
        cursor.execute(f"""
            SELECT current_state FROM markov_matrices_{safe_id}
            WHERE timeframe = ?
        """, (timeframe,))
        
        row = cursor.fetchone()
        previous_state = row["current_state"] if row else 0
        
        if new_bias != previous_state:
            # State changed - record transition
            cursor.execute(f"""
                INSERT INTO state_transitions_{safe_id} (
                    profile_id, symbol, timeframe, timestamp,
                    from_state, to_state, from_state_label, to_state_label,
                    trigger_source, trigger_data, composite_score,
                    price_action_score, key_levels_score, momentum_score,
                    volume_score, structure_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                sentiment_data.get("profile_id"),
                sentiment_data.get("symbol"),
                timeframe,
                sentiment_data.get("timestamp"),
                previous_state,
                new_bias,
                self.BIAS_LABELS.get(previous_state),
                self.BIAS_LABELS.get(new_bias),
                "SENTIMENT",
                json.dumps({"sentiment_id": sentiment_data.get("id")}),
                sentiment_data.get("composite_score"),
                sentiment_data.get("price_action_score"),
                sentiment_data.get("key_levels_score"),
                sentiment_data.get("momentum_score"),
                sentiment_data.get("volume_score"),
                sentiment_data.get("structure_score")
            ))
            
            # Update current state in markov matrix
            cursor.execute(f"""
                UPDATE markov_matrices_{safe_id}
                SET current_state = ?, updated_at = ?
                WHERE timeframe = ?
            """, (new_bias, datetime.utcnow().isoformat() + "Z", timeframe))
            
            # Update transition counts
            self._update_transition_counts(cursor, safe_id, timeframe, previous_state, new_bias)
            
            conn.commit()
            print(f"[InstanceDB] State transition: {self.BIAS_LABELS[previous_state]} → {self.BIAS_LABELS[new_bias]}")
        
        conn.close()
    
    def _update_transition_counts(self, cursor, safe_id: str, timeframe: str, 
                                  from_state: int, to_state: int):
        """Update transition counts and recalculate matrix"""
        # Get current counts
        cursor.execute(f"""
            SELECT transition_counts, total_transitions FROM markov_matrices_{safe_id}
            WHERE timeframe = ?
        """, (timeframe,))
        
        row = cursor.fetchone()
        counts = json.loads(row["transition_counts"]) if row["transition_counts"] else [[0]*5 for _ in range(5)]
        total = row["total_transitions"] or 0
        
        # Map state (-2 to +2) to index (0 to 4)
        from_idx = from_state + 2
        to_idx = to_state + 2
        
        # Increment count
        counts[from_idx][to_idx] += 1
        total += 1
        
        # Recalculate probabilities
        matrix = []
        for row_counts in counts:
            row_sum = sum(row_counts)
            if row_sum > 0:
                matrix.append([c / row_sum for c in row_counts])
            else:
                matrix.append([0.2] * 5)  # Uniform if no data
        
        # Calculate stability (average of diagonal)
        stability = sum(matrix[i][i] for i in range(5)) / 5
        
        # Calculate trend bias (weighted average of states)
        trend_bias = 0
        for i, row_probs in enumerate(matrix):
            state_val = i - 2  # Convert back to -2 to +2
            for j, prob in enumerate(row_probs):
                dest_val = j - 2
                trend_bias += prob * dest_val
        trend_bias /= 5
        
        # Update database
        cursor.execute(f"""
            UPDATE markov_matrices_{safe_id}
            SET matrix_data = ?, transition_counts = ?, total_transitions = ?,
                stability_score = ?, trend_bias = ?, updated_at = ?
            WHERE timeframe = ?
        """, (
            json.dumps(matrix),
            json.dumps(counts),
            total,
            stability,
            trend_bias,
            datetime.utcnow().isoformat() + "Z",
            timeframe
        ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # POSITION OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def save_position(self, instance_id: str, position_data: dict) -> int:
        """Save a position record"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            INSERT INTO positions_{safe_id} (
                profile_id, symbol, direction, status,
                pyramid_level, parent_position_id, trade_group_id,
                entry_price, entry_time, entry_ticket,
                lots, stop_loss, take_profit,
                signal_source, signal_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            position_data.get("profile_id"),
            position_data.get("symbol"),
            position_data.get("direction"),
            position_data.get("status", "PENDING"),
            position_data.get("pyramid_level", 1),
            position_data.get("parent_position_id"),
            position_data.get("trade_group_id"),
            position_data.get("entry_price"),
            position_data.get("entry_time"),
            position_data.get("entry_ticket"),
            position_data.get("lots"),
            position_data.get("stop_loss"),
            position_data.get("take_profit"),
            position_data.get("signal_source"),
            json.dumps(position_data.get("signal_data")) if position_data.get("signal_data") else None
        ))
        
        position_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return position_id
    
    def get_open_positions(self, instance_id: str) -> List[dict]:
        """Get all open positions for an instance"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM positions_{safe_id}
            WHERE status IN ('PENDING', 'OPEN')
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_position_history(self, instance_id: str, limit: int = 100) -> List[dict]:
        """Get position history"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM positions_{safe_id}
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════════════════
    # MATRIX OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_markov_matrix(self, instance_id: str, timeframe: str) -> Optional[dict]:
        """Get the current Markov matrix for an instance"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM markov_matrices_{safe_id}
            WHERE timeframe = ?
        """, (timeframe,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "timeframe": row["timeframe"],
            "matrix_data": json.loads(row["matrix_data"]) if row["matrix_data"] else None,
            "transition_counts": json.loads(row["transition_counts"]) if row["transition_counts"] else None,
            "total_transitions": row["total_transitions"],
            "stability_score": row["stability_score"],
            "trend_bias": row["trend_bias"],
            "current_state": row["current_state"],
            "updated_at": row["updated_at"]
        }
    
    def get_state_transitions(self, instance_id: str, timeframe: str, 
                             limit: int = 100) -> List[dict]:
        """Get state transition history"""
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM state_transitions_{safe_id}
            WHERE timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (timeframe, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


# ═══════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════

_instance_db = None

def get_instance_db(db_path: str = "apex_instances.db") -> InstanceDatabaseManager:
    """Get singleton instance of the database manager"""
    global _instance_db
    if _instance_db is None:
        _instance_db = InstanceDatabaseManager(db_path)
    return _instance_db


# ═══════════════════════════════════════════════════════════════════════════
# CLI FOR TESTING
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="APEX Instance Database Manager")
    parser.add_argument('--create', metavar='SYMBOL', help='Create new instance for symbol')
    parser.add_argument('--type', default='SIM', choices=['SIM', 'LIVE'], help='Account type')
    parser.add_argument('--list', action='store_true', help='List all instances')
    parser.add_argument('--archive', metavar='ID', help='Archive an instance')
    
    args = parser.parse_args()
    
    db = get_instance_db()
    
    if args.create:
        instance = db.create_instance(args.create, args.type)
        print(f"Created: {instance.id}")
        print(f"  Display Name: {instance.display_name}")
        print(f"  Symbol: {instance.symbol}")
        print(f"  Type: {instance.account_type}")
    
    elif args.list:
        instances = db.get_all_instances()
        print("\n=== ACTIVE INSTANCES ===")
        for inst in instances["active"]:
            print(f"  [{inst.account_type}] {inst.id} - {inst.display_name}")
        print(f"\n=== ARCHIVED INSTANCES ===")
        for inst in instances["archived"]:
            print(f"  [{inst.account_type}] {inst.id} - {inst.display_name} (archived: {inst.archived_at})")
    
    elif args.archive:
        if db.archive_instance(args.archive):
            print(f"Archived: {args.archive}")
        else:
            print(f"Failed to archive: {args.archive}")
    
    else:
        parser.print_help()
