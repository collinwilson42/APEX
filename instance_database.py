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
    
    -- MT5 Live Sync (SEED 10D)
    mt5_ticket INTEGER,           -- MT5 position ticket number
    mt5_magic INTEGER,            -- EA magic number
    mt5_profit REAL,              -- Real-time P&L from MT5
    mt5_swap REAL,                -- Swap from MT5
    mt5_commission REAL,          -- Commission from MT5
    current_price REAL,           -- Latest price from MT5
    sync_status TEXT DEFAULT 'PENDING',  -- PENDING | SYNCED | CLOSED_MT5 | ORPHAN
    last_sync_at TEXT,            -- Last sync timestamp
    
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
# BROKER TABLES (Seed 14B - Virtual Broker)
# ═══════════════════════════════════════════════════════════════════════════

BROKER_STATE_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_state (
    instance_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL DEFAULT 'SIM',  -- SIM | LIVE
    initial_balance REAL DEFAULT 10000.0,
    realized_pnl REAL DEFAULT 0.0,
    
    -- Last known state (for recovery)
    last_equity REAL,
    last_unrealized_pnl REAL,
    position_count INTEGER DEFAULT 0,
    
    -- Config
    auto_sl_tp INTEGER DEFAULT 1,  -- Enable SL/TP auto-close in SIM
    slippage_sim REAL DEFAULT 0.0,  -- Simulated slippage (future)
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (instance_id) REFERENCES algorithm_instances(id)
)
"""

BROKER_POSITIONS_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    ticket INTEGER NOT NULL,  -- VirtualBroker ticket number
    
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,  -- BUY | SELL
    volume REAL NOT NULL,
    
    open_price REAL NOT NULL,
    open_time TEXT NOT NULL,
    
    current_price REAL,
    unrealized_pnl REAL DEFAULT 0.0,
    
    sl REAL,  -- Stop loss
    tp REAL,  -- Take profit
    
    status TEXT DEFAULT 'OPEN',  -- OPEN | CLOSED
    close_price REAL,
    close_time TEXT,
    close_reason TEXT,  -- MANUAL | SL_HIT | TP_HIT | SIGNAL
    realized_pnl REAL,
    
    comment TEXT,
    
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (instance_id) REFERENCES algorithm_instances(id),
    UNIQUE(instance_id, ticket)
)
"""

BROKER_TRADES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS broker_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instance_id TEXT NOT NULL,
    position_ticket INTEGER,  -- Links to broker_positions.ticket
    
    trade_type TEXT NOT NULL,  -- OPEN | CLOSE | MODIFY
    symbol TEXT NOT NULL,
    direction TEXT,  -- BUY | SELL (for OPEN/CLOSE)
    volume REAL,
    price REAL,
    
    sl REAL,
    tp REAL,
    
    pnl REAL,  -- Realized PnL (for CLOSE trades)
    
    success INTEGER DEFAULT 1,  -- 1=success, 0=failed
    message TEXT,
    
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (instance_id) REFERENCES algorithm_instances(id)
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
        
        # Create broker tables (Seed 14B)
        cursor.execute(BROKER_STATE_TABLE_SCHEMA)
        cursor.execute(BROKER_POSITIONS_TABLE_SCHEMA)
        cursor.execute(BROKER_TRADES_TABLE_SCHEMA)
        
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
        
        # Broker indexes (Seed 14B)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_broker_positions_instance 
            ON broker_positions(instance_id, status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_broker_trades_instance 
            ON broker_trades(instance_id, timestamp DESC)
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
            
            # Initialize empty Markov matrices for both timeframes (SEED 13: 15m/1h)
            empty_matrix = json.dumps([[0.2] * 5 for _ in range(5)])
            empty_counts = json.dumps([[0] * 5 for _ in range(5)])
            
            for tf in ['15m', '1h']:
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
    
    # ═══════════════════════════════════════════════════════════════════════
    # MT5 POSITION SYNC (SEED 10D)
    # ═══════════════════════════════════════════════════════════════════════
    
    def upsert_mt5_position(self, instance_id: str, mt5_position: dict) -> int:
        """
        Insert or update a position from MT5 live data.
        Uses mt5_ticket as the unique identifier for matching.
        
        Args:
            instance_id: Instance to sync to
            mt5_position: Position data from MT5 with keys:
                - ticket: MT5 position ticket
                - symbol: Trading symbol
                - type: 0=BUY, 1=SELL
                - volume: Lot size
                - price_open: Entry price
                - price_current: Current price
                - sl: Stop loss
                - tp: Take profit
                - profit: Current P&L
                - swap: Accumulated swap
                - commission: Commission paid
                - magic: EA magic number
                - time: Position open time (unix timestamp)
        
        Returns:
            Position ID (existing or new)
        """
        safe_id = self._sanitize_instance_id(instance_id)
        
        ticket = mt5_position.get('ticket')
        if not ticket:
            raise ValueError("MT5 position must have a ticket number")
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Check if position with this ticket exists
        cursor.execute(f"""
            SELECT id, status FROM positions_{safe_id}
            WHERE mt5_ticket = ?
        """, (ticket,))
        
        existing = cursor.fetchone()
        now = datetime.utcnow().isoformat() + "Z"
        
        # Map MT5 type to direction
        direction = "LONG" if mt5_position.get('type', 0) == 0 else "SHORT"
        
        # Convert MT5 timestamp to ISO format
        entry_time = datetime.fromtimestamp(mt5_position.get('time', 0)).isoformat() + "Z" if mt5_position.get('time') else now
        
        if existing:
            # Update existing position
            position_id = existing['id']
            cursor.execute(f"""
                UPDATE positions_{safe_id} SET
                    unrealized_pnl = ?,
                    mt5_profit = ?,
                    mt5_swap = ?,
                    mt5_commission = ?,
                    current_price = ?,
                    stop_loss = ?,
                    take_profit = ?,
                    sync_status = 'SYNCED',
                    last_sync_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                mt5_position.get('profit', 0),
                mt5_position.get('profit', 0),
                mt5_position.get('swap', 0),
                mt5_position.get('commission', 0),
                mt5_position.get('price_current'),
                mt5_position.get('sl'),
                mt5_position.get('tp'),
                now,
                now,
                position_id
            ))
        else:
            # Insert new position
            cursor.execute(f"""
                INSERT INTO positions_{safe_id} (
                    symbol, direction, status, lots,
                    entry_price, entry_time, entry_ticket,
                    stop_loss, take_profit,
                    unrealized_pnl, mt5_ticket, mt5_magic,
                    mt5_profit, mt5_swap, mt5_commission,
                    current_price, sync_status, last_sync_at,
                    signal_source
                ) VALUES (?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SYNCED', ?, 'MT5_SYNC')
            """, (
                mt5_position.get('symbol'),
                direction,
                mt5_position.get('volume', 0),
                mt5_position.get('price_open'),
                entry_time,
                ticket,
                mt5_position.get('sl'),
                mt5_position.get('tp'),
                mt5_position.get('profit', 0),
                ticket,
                mt5_position.get('magic'),
                mt5_position.get('profit', 0),
                mt5_position.get('swap', 0),
                mt5_position.get('commission', 0),
                mt5_position.get('price_current'),
                now
            ))
            position_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        return position_id
    
    def mark_positions_closed_by_mt5(self, instance_id: str, active_tickets: List[int]):
        """
        Mark positions as CLOSED_MT5 if they're no longer in the active MT5 positions.
        This handles positions that were closed externally in MT5.
        
        Args:
            instance_id: Instance to check
            active_tickets: List of currently open MT5 ticket numbers
        """
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat() + "Z"
        
        if active_tickets:
            # Mark positions not in active list as closed
            placeholders = ','.join(['?' for _ in active_tickets])
            cursor.execute(f"""
                UPDATE positions_{safe_id} SET
                    status = 'CLOSED',
                    sync_status = 'CLOSED_MT5',
                    exit_time = ?,
                    exit_reason = 'MT5_EXTERNAL_CLOSE',
                    realized_pnl = mt5_profit,
                    updated_at = ?
                WHERE status = 'OPEN' 
                AND sync_status = 'SYNCED'
                AND mt5_ticket IS NOT NULL
                AND mt5_ticket NOT IN ({placeholders})
            """, [now, now] + active_tickets)
        else:
            # No active positions - close all synced positions
            cursor.execute(f"""
                UPDATE positions_{safe_id} SET
                    status = 'CLOSED',
                    sync_status = 'CLOSED_MT5',
                    exit_time = ?,
                    exit_reason = 'MT5_EXTERNAL_CLOSE',
                    realized_pnl = mt5_profit,
                    updated_at = ?
                WHERE status = 'OPEN' 
                AND sync_status = 'SYNCED'
                AND mt5_ticket IS NOT NULL
            """, (now, now))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            print(f"[InstanceDB] Marked {affected} positions as closed by MT5")
        
        return affected
    
    def get_positions_with_sync_status(self, instance_id: str, limit: int = 100) -> List[dict]:
        """
        Get positions with their sync status for the live feed display.
        Includes all fields needed for the frontend table.
        """
        safe_id = self._sanitize_instance_id(instance_id)
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            SELECT * FROM positions_{safe_id}
            ORDER BY 
                CASE WHEN status IN ('PENDING', 'OPEN') THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    # ═══════════════════════════════════════════════════════════════════════
    # BROKER OPERATIONS (Seed 14B - Virtual Broker)
    # ═══════════════════════════════════════════════════════════════════════
    
    def init_broker_state(self, instance_id: str, mode: str = "SIM", 
                          initial_balance: float = 10000.0) -> dict:
        """
        Initialize broker state for an instance.
        Creates record if doesn't exist, returns existing if it does.
        
        Args:
            instance_id: Instance ID
            mode: "SIM" or "LIVE"
            initial_balance: Starting balance for SIM mode
            
        Returns:
            Broker state dict
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        # Check if exists
        cursor.execute("SELECT * FROM broker_state WHERE instance_id = ?", (instance_id,))
        existing = cursor.fetchone()
        
        if existing:
            conn.close()
            return dict(existing)
        
        # Create new
        cursor.execute("""
            INSERT INTO broker_state (instance_id, mode, initial_balance, last_equity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (instance_id, mode.upper(), initial_balance, initial_balance, now, now))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM broker_state WHERE instance_id = ?", (instance_id,))
        result = dict(cursor.fetchone())
        conn.close()
        
        print(f"[InstanceDB] Initialized broker state for {instance_id} ({mode})")
        return result
    
    def get_broker_state(self, instance_id: str) -> Optional[dict]:
        """Get broker state for an instance"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM broker_state WHERE instance_id = ?", (instance_id,))
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def update_broker_state(self, instance_id: str, **kwargs) -> bool:
        """
        Update broker state fields.
        
        Args:
            instance_id: Instance ID
            **kwargs: Fields to update (realized_pnl, last_equity, last_unrealized_pnl, position_count)
            
        Returns:
            True if updated
        """
        if not kwargs:
            return False
        
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        # Build SET clause
        allowed_fields = {'realized_pnl', 'last_equity', 'last_unrealized_pnl', 'position_count', 'mode'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            conn.close()
            return False
        
        updates['updated_at'] = now
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [instance_id]
        
        cursor.execute(f"""
            UPDATE broker_state SET {set_clause} WHERE instance_id = ?
        """, values)
        
        conn.commit()
        conn.close()
        return True
    
    def save_broker_position(self, instance_id: str, position: dict) -> int:
        """
        Save or update a broker position.
        Uses (instance_id, ticket) as unique key.
        
        Args:
            instance_id: Instance ID
            position: Position dict with keys:
                - ticket, symbol, direction, volume, open_price, open_time
                - sl, tp, current_price, unrealized_pnl, comment
                - status (OPEN/CLOSED), close_price, close_time, close_reason, realized_pnl
                
        Returns:
            Position ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        ticket = position.get('ticket')
        if not ticket:
            raise ValueError("Position must have a ticket number")
        
        # Check if exists
        cursor.execute("""
            SELECT id FROM broker_positions WHERE instance_id = ? AND ticket = ?
        """, (instance_id, ticket))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update
            cursor.execute("""
                UPDATE broker_positions SET
                    current_price = ?,
                    unrealized_pnl = ?,
                    sl = ?,
                    tp = ?,
                    status = ?,
                    close_price = ?,
                    close_time = ?,
                    close_reason = ?,
                    realized_pnl = ?,
                    updated_at = ?
                WHERE instance_id = ? AND ticket = ?
            """, (
                position.get('current_price'),
                position.get('unrealized_pnl', position.get('pnl', 0)),
                position.get('sl'),
                position.get('tp'),
                position.get('status', 'OPEN'),
                position.get('close_price'),
                position.get('close_time'),
                position.get('close_reason'),
                position.get('realized_pnl'),
                now,
                instance_id,
                ticket
            ))
            position_id = existing['id']
        else:
            # Insert
            open_time = position.get('open_time')
            if hasattr(open_time, 'isoformat'):
                open_time = open_time.isoformat() + "Z"
            
            cursor.execute("""
                INSERT INTO broker_positions (
                    instance_id, ticket, symbol, direction, volume,
                    open_price, open_time, current_price, unrealized_pnl,
                    sl, tp, status, comment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                instance_id,
                ticket,
                position.get('symbol'),
                position.get('direction'),
                position.get('volume'),
                position.get('open_price'),
                open_time,
                position.get('current_price', position.get('open_price')),
                position.get('unrealized_pnl', position.get('pnl', 0)),
                position.get('sl'),
                position.get('tp'),
                position.get('status', 'OPEN'),
                position.get('comment', ''),
                now,
                now
            ))
            position_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return position_id
    
    def get_broker_positions(self, instance_id: str, status: str = None) -> List[dict]:
        """
        Get broker positions for an instance.
        
        Args:
            instance_id: Instance ID
            status: Filter by status (OPEN, CLOSED, or None for all)
            
        Returns:
            List of position dicts
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT * FROM broker_positions 
                WHERE instance_id = ? AND status = ?
                ORDER BY open_time DESC
            """, (instance_id, status))
        else:
            cursor.execute("""
                SELECT * FROM broker_positions 
                WHERE instance_id = ?
                ORDER BY 
                    CASE WHEN status = 'OPEN' THEN 0 ELSE 1 END,
                    open_time DESC
            """, (instance_id,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def close_broker_position(self, instance_id: str, ticket: int,
                              close_price: float, close_reason: str,
                              realized_pnl: float) -> bool:
        """
        Close a broker position.
        
        Args:
            instance_id: Instance ID
            ticket: Position ticket
            close_price: Close price
            close_reason: Reason (MANUAL, SL_HIT, TP_HIT, SIGNAL)
            realized_pnl: Final PnL
            
        Returns:
            True if closed
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        cursor.execute("""
            UPDATE broker_positions SET
                status = 'CLOSED',
                close_price = ?,
                close_time = ?,
                close_reason = ?,
                realized_pnl = ?,
                updated_at = ?
            WHERE instance_id = ? AND ticket = ? AND status = 'OPEN'
        """, (close_price, now, close_reason, realized_pnl, now, instance_id, ticket))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
    
    def log_broker_trade(self, instance_id: str, trade: dict) -> int:
        """
        Log a broker trade event.
        
        Args:
            instance_id: Instance ID
            trade: Trade dict with keys:
                - trade_type: OPEN | CLOSE | MODIFY
                - symbol, direction, volume, price
                - sl, tp, pnl
                - position_ticket, success, message
                
        Returns:
            Trade log ID
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        now = datetime.utcnow().isoformat() + "Z"
        
        cursor.execute("""
            INSERT INTO broker_trades (
                instance_id, position_ticket, trade_type, symbol,
                direction, volume, price, sl, tp, pnl,
                success, message, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            instance_id,
            trade.get('position_ticket', trade.get('ticket')),
            trade.get('trade_type'),
            trade.get('symbol'),
            trade.get('direction'),
            trade.get('volume'),
            trade.get('price'),
            trade.get('sl'),
            trade.get('tp'),
            trade.get('pnl'),
            1 if trade.get('success', True) else 0,
            trade.get('message', ''),
            now
        ))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return trade_id
    
    def get_broker_trades(self, instance_id: str, limit: int = 100) -> List[dict]:
        """
        Get trade history for an instance.
        
        Args:
            instance_id: Instance ID
            limit: Max trades to return
            
        Returns:
            List of trade dicts
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM broker_trades 
            WHERE instance_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (instance_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_broker_stats(self, instance_id: str) -> dict:
        """
        Get aggregated broker statistics.
        
        Returns:
            Dict with total_trades, winning_trades, total_pnl, win_rate, etc.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Get closed positions stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                SUM(realized_pnl) as total_pnl,
                AVG(realized_pnl) as avg_pnl,
                MAX(realized_pnl) as best_trade,
                MIN(realized_pnl) as worst_trade,
                SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END) as gross_profit,
                SUM(CASE WHEN realized_pnl < 0 THEN ABS(realized_pnl) ELSE 0 END) as gross_loss
            FROM broker_positions
            WHERE instance_id = ? AND status = 'CLOSED'
        """, (instance_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        stats = dict(row) if row else {}
        
        # Calculate derived stats
        total = stats.get('total_trades', 0) or 0
        wins = stats.get('winning_trades', 0) or 0
        gross_profit = stats.get('gross_profit', 0) or 0
        gross_loss = stats.get('gross_loss', 0) or 0
        
        stats['win_rate'] = (wins / total * 100) if total > 0 else 0
        stats['profit_factor'] = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        return stats
    
    def restore_broker_positions(self, instance_id: str) -> List[dict]:
        """
        Restore open positions from database for VirtualBroker recovery.
        Called when broker is restarted to resume state.
        
        Returns:
            List of open position dicts
        """
        return self.get_broker_positions(instance_id, status='OPEN')
    
    def get_all_broker_states(self) -> List[dict]:
        """
        Get broker state for all instances.
        Used for API overview endpoint.
        """
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT bs.*, ai.display_name, ai.symbol, ai.status as instance_status
            FROM broker_state bs
            LEFT JOIN algorithm_instances ai ON bs.instance_id = ai.id
            ORDER BY bs.updated_at DESC
        """)
        
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
