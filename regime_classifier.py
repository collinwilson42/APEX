"""
REGIME CLASSIFIER & MATRIX ENGINE
===================================
Seed 26: Deterministic Regime Intelligence

Classifies every candle into one of 5 market regimes using ONLY
pre-computed indicators from the intelligence DB. No AI, no subjectivity.
Same data → same classification. Always.

States:
    STRONG_BULL  (2)  — Powerful uptrend, high conviction
    BULL         (1)  — Clear upward bias
    NEUTRAL      (0)  — No directional edge (ranging OR volatile)
    BEAR        (-1)  — Clear downward bias
    STRONG_BEAR (-2)  — Powerful downtrend, high conviction

Each symbol gets its own matrix. No mingling.

Usage:
    from regime_classifier import backfill_regime_data, get_regime_matrix
    backfill_regime_data("XAUJ26")           # classify all historical candles
    matrix = get_regime_matrix("XAUJ26", "15m")  # get transition probabilities
"""

import os
import sys
import json
import math
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import SYMBOL_DATABASES

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════
# STATE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

STATES = {
    "STRONG_BEAR": -2,
    "BEAR":        -1,
    "NEUTRAL":      0,
    "BULL":         1,
    "STRONG_BULL":  2,
}
STATE_NAMES = ["STRONG_BEAR", "BEAR", "NEUTRAL", "BULL", "STRONG_BULL"]
STATE_INDEX = {name: i for i, name in enumerate(STATE_NAMES)}  # 0-4 for matrix indexing
NUM_STATES = len(STATE_NAMES)

# Duration buckets for conditional matrices
DURATION_BUCKETS = {
    "early":    (1, 5),     # just entered regime
    "mature":   (6, 20),    # established regime
    "extended": (21, 9999), # regime getting long
}


# ═══════════════════════════════════════════════════════════════════════════
# REGIME CLASSIFICATION — PURE DETERMINISTIC
# ═══════════════════════════════════════════════════════════════════════════

def classify_regime(
    adx: float,
    rsi: float,
    macd_hist: float,
    stoch_k: float,
    cci: float,
    bb_width: float,
    atr: float,
    ema_short: float,
    ema_medium: float,
    close: float,
) -> str:
    """
    Classify a single candle into one of 5 regime states.
    
    Uses a scoring approach: each indicator contributes a directional vote
    weighted by conviction. The aggregate score maps to a state.
    
    This avoids brittle threshold trees — instead every indicator has a say,
    and the composite determines the regime.
    """
    score = 0.0
    trend_strength = 0.0
    
    # ── 1. ADX: Trend Strength (not direction) ──
    # ADX < 20 = weak/no trend, ADX > 30 = strong trend
    if adx > 0:
        trend_strength = min(adx / 40.0, 1.0)  # 0.0 to 1.0
    
    # ── 2. RSI: Momentum direction ──
    # Center at 50, normalize to [-1, +1]
    rsi_signal = (rsi - 50.0) / 50.0  # -1 to +1
    score += rsi_signal * 0.20
    
    # ── 3. MACD Histogram: Momentum confirmation ──
    # Normalize by ATR to make it comparable across price levels
    safe_atr = max(atr, 0.001)
    macd_norm = macd_hist / safe_atr
    macd_signal = max(-1.0, min(1.0, math.tanh(macd_norm * 3.0)))
    score += macd_signal * 0.25
    
    # ── 4. Stochastic: Overbought/Oversold context ──
    stoch_signal = (stoch_k - 50.0) / 50.0  # -1 to +1
    score += stoch_signal * 0.15
    
    # ── 5. CCI: Trend deviation ──
    cci_signal = max(-1.0, min(1.0, math.tanh(cci / 150.0)))
    score += cci_signal * 0.15
    
    # ── 6. EMA Alignment: Structural direction ──
    if ema_medium and ema_medium > 0:
        ema_diff = (ema_short - ema_medium) / ema_medium * 100.0
        ema_signal = max(-1.0, min(1.0, math.tanh(ema_diff * 3.0)))
    else:
        ema_signal = 0.0
    score += ema_signal * 0.25
    
    # ── Composite: score × trend_strength ──
    # In a weak trend (ADX < 20), even strong oscillator readings
    # get dampened → pushes toward NEUTRAL
    # In a strong trend (ADX > 30), the full directional score comes through
    
    # Base directional score is [-1, +1]
    # Trend multiplier amplifies conviction when ADX confirms
    if adx < 20:
        # Weak trend: dampen the signal significantly
        dampened = score * 0.4
    elif adx < 25:
        # Transitional: partial dampening
        dampened = score * 0.7
    else:
        # Trending: full signal, boosted by ADX strength
        boost = 1.0 + (trend_strength - 0.5) * 0.6  # 0.7 to 1.3
        dampened = score * boost
    
    # Clamp to [-1, +1]
    final_score = max(-1.0, min(1.0, dampened))
    
    # ── Map score to state ──
    if final_score >= 0.45:
        return "STRONG_BULL"
    elif final_score >= 0.15:
        return "BULL"
    elif final_score <= -0.45:
        return "STRONG_BEAR"
    elif final_score <= -0.15:
        return "BEAR"
    else:
        return "NEUTRAL"


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════

SCHEMA_REGIME_HISTORY = """
CREATE TABLE IF NOT EXISTS regime_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    close_price     REAL NOT NULL,
    
    -- Classification result
    regime_state    TEXT NOT NULL,
    regime_score    REAL NOT NULL,
    candles_in_state INTEGER NOT NULL DEFAULT 1,
    
    -- Indicator snapshot (the inputs that produced this classification)
    adx             REAL,
    rsi_14          REAL,
    macd_hist       REAL,
    stoch_k_14      REAL,
    cci_14          REAL,
    bb_width        REAL,
    atr_14          REAL,
    ema_short       REAL,
    ema_medium      REAL,
    
    -- Metadata
    classification_version INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    
    UNIQUE(timestamp, timeframe)
);
CREATE INDEX IF NOT EXISTS idx_regime_ts ON regime_history(timestamp, timeframe);
CREATE INDEX IF NOT EXISTS idx_regime_state ON regime_history(regime_state, timeframe);
"""

SCHEMA_REGIME_TRANSITIONS = """
CREATE TABLE IF NOT EXISTS regime_transitions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    
    from_state      TEXT NOT NULL,
    to_state        TEXT NOT NULL,
    duration_candles INTEGER NOT NULL,
    
    -- Price context during the regime that just ended
    price_at_entry  REAL,
    price_at_exit   REAL,
    price_change_pct REAL,
    
    -- Indicator snapshot at transition point
    adx_at_transition   REAL,
    rsi_at_transition   REAL,
    atr_at_transition   REAL,
    
    created_at      TEXT DEFAULT (datetime('now')),
    
    UNIQUE(timestamp, timeframe)
);
CREATE INDEX IF NOT EXISTS idx_trans_states ON regime_transitions(from_state, to_state, timeframe);
CREATE INDEX IF NOT EXISTS idx_trans_dur ON regime_transitions(duration_candles, timeframe);
"""

SCHEMA_REGIME_MATRIX = """
CREATE TABLE IF NOT EXISTS regime_matrix (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    timeframe       TEXT NOT NULL,
    
    -- Matrix data (5x5 JSON arrays)
    matrix_data     TEXT NOT NULL,
    frequency_data  TEXT NOT NULL,
    
    -- Duration-conditional matrices (JSON: {"early": 5x5, "mature": 5x5, "extended": 5x5})
    duration_matrices TEXT,
    
    -- Duration statistics (JSON: {"STRONG_BULL": {"mean": 12.3, "median": 8, ...}, ...})
    duration_stats  TEXT,
    
    -- Stationary distribution (JSON: {"STRONG_BULL": 0.08, "BULL": 0.22, ...})
    stationary_dist TEXT,
    
    -- Metadata
    sample_count    INTEGER NOT NULL,
    transition_count INTEGER NOT NULL,
    date_range_start TEXT,
    date_range_end  TEXT,
    classification_version INTEGER NOT NULL DEFAULT 1,
    computed_at     TEXT DEFAULT (datetime('now')),
    
    UNIQUE(symbol, timeframe, classification_version)
);
"""


# ═══════════════════════════════════════════════════════════════════════════
# BACKFILL ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def backfill_regime_data(symbol: str, timeframes: List[str] = None) -> Dict:
    """
    Classify ALL historical candles for a symbol and build transition matrices.
    
    This is the main entry point. Run once per symbol to populate the regime
    tables, then call incrementally for new candles.
    
    Args:
        symbol: Symbol key from SYMBOL_DATABASES (e.g., "XAUJ26")
        timeframes: List of timeframes to process (default: all available)
    
    Returns:
        Dict with statistics about the backfill
    """
    sym_config = SYMBOL_DATABASES.get(symbol)
    if not sym_config:
        logger.error(f"Unknown symbol: {symbol}")
        return {"error": f"Unknown symbol: {symbol}"}
    
    db_path = sym_config["db_path"]
    if not os.path.exists(db_path):
        logger.error(f"Intelligence DB not found: {db_path}")
        return {"error": f"DB not found: {db_path}"}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Create schema
    conn.executescript(SCHEMA_REGIME_HISTORY)
    conn.executescript(SCHEMA_REGIME_TRANSITIONS)
    conn.executescript(SCHEMA_REGIME_MATRIX)
    
    # Discover available timeframes if not specified
    if not timeframes:
        cur = conn.execute("SELECT DISTINCT timeframe FROM core_15m ORDER BY timeframe")
        timeframes = [r[0] for r in cur.fetchall()]
    
    results = {}
    
    for tf in timeframes:
        print(f"\n{'='*60}")
        print(f"  BACKFILLING {symbol} / {tf}")
        print(f"{'='*60}")
        
        stats = _backfill_timeframe(conn, symbol, tf)
        results[tf] = stats
        
        print(f"  Candles classified: {stats['candles_classified']:,}")
        print(f"  Transitions found:  {stats['transitions_found']:,}")
        print(f"  State distribution: {stats['state_distribution']}")
    
    conn.close()
    return results


def _backfill_timeframe(conn: sqlite3.Connection, symbol: str, timeframe: str) -> Dict:
    """
    Classify all candles for one symbol+timeframe and build the matrix.
    """
    # Clear existing data for this timeframe (full rebuild)
    conn.execute("DELETE FROM regime_history WHERE timeframe = ?", (timeframe,))
    conn.execute("DELETE FROM regime_transitions WHERE timeframe = ?", (timeframe,))
    conn.execute("DELETE FROM regime_matrix WHERE timeframe = ? AND symbol = ?", 
                 (timeframe, symbol))
    conn.commit()
    
    # ── Load all candles with indicators ──
    query = """
        SELECT 
            c.timestamp, c.open, c.high, c.low, c.close, c.volume,
            a.adx_14, a.rsi_14, a.macd_histogram_12_26,
            a.stoch_k_14, a.stoch_d_14, a.cci_14,
            a.bb_width_20, a.bb_pct_20,
            b.atr_14, b.ema_short, b.ema_medium
        FROM core_15m c
        JOIN advanced_indicators a 
            ON c.timestamp = a.timestamp AND c.timeframe = a.timeframe
        JOIN basic_15m b 
            ON c.timestamp = b.timestamp AND c.timeframe = b.timeframe
        WHERE c.timeframe = ?
        ORDER BY c.timestamp ASC
    """
    
    rows = conn.execute(query, (timeframe,)).fetchall()
    total_candles = len(rows)
    print(f"  Loaded {total_candles:,} candles")
    
    if total_candles == 0:
        return {"candles_classified": 0, "transitions_found": 0, 
                "state_distribution": {}}
    
    # ── Classify each candle ──
    history_rows = []
    prev_state = None
    candles_in_state = 0
    
    # For transitions
    transition_rows = []
    regime_entry_price = None
    regime_entry_ts = None
    
    # State distribution counter
    state_counts = defaultdict(int)
    
    for row in rows:
        ts = row["timestamp"]
        close = _safe(row["close"])
        adx = _safe(row["adx_14"], 20)
        rsi = _safe(row["rsi_14"], 50)
        macd_h = _safe(row["macd_histogram_12_26"])
        stoch_k = _safe(row["stoch_k_14"], 50)
        cci = _safe(row["cci_14"])
        bb_w = _safe(row["bb_width_20"])
        atr = _safe(row["atr_14"], 1.0)
        ema_s = _safe(row["ema_short"])
        ema_m = _safe(row["ema_medium"])
        
        state = classify_regime(
            adx=adx, rsi=rsi, macd_hist=macd_h, stoch_k=stoch_k,
            cci=cci, bb_width=bb_w, atr=atr,
            ema_short=ema_s, ema_medium=ema_m, close=close
        )
        
        # Track duration
        if state == prev_state:
            candles_in_state += 1
        else:
            # State change — record transition
            if prev_state is not None:
                price_change_pct = 0.0
                if regime_entry_price and regime_entry_price > 0:
                    price_change_pct = ((close - regime_entry_price) / regime_entry_price) * 100.0
                
                transition_rows.append((
                    ts, timeframe,
                    prev_state, state, candles_in_state,
                    regime_entry_price, close, round(price_change_pct, 4),
                    adx, rsi, atr
                ))
            
            # Reset for new regime
            candles_in_state = 1
            regime_entry_price = close
            regime_entry_ts = ts
        
        state_counts[state] += 1
        
        # Compute the raw score for storage (useful for analysis)
        raw_score = _compute_raw_score(adx, rsi, macd_h, stoch_k, cci, ema_s, ema_m, atr)
        
        history_rows.append((
            ts, timeframe, close,
            state, round(raw_score, 4), candles_in_state,
            adx, rsi, macd_h, stoch_k, cci, bb_w, atr, ema_s, ema_m,
            1  # classification_version
        ))
        
        prev_state = state
    
    # ── Bulk insert regime_history ──
    conn.executemany("""
        INSERT OR REPLACE INTO regime_history 
        (timestamp, timeframe, close_price,
         regime_state, regime_score, candles_in_state,
         adx, rsi_14, macd_hist, stoch_k_14, cci_14, bb_width, atr_14, ema_short, ema_medium,
         classification_version)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, history_rows)
    
    # ── Bulk insert regime_transitions ──
    conn.executemany("""
        INSERT OR REPLACE INTO regime_transitions
        (timestamp, timeframe,
         from_state, to_state, duration_candles,
         price_at_entry, price_at_exit, price_change_pct,
         adx_at_transition, rsi_at_transition, atr_at_transition)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, transition_rows)
    
    conn.commit()
    
    # ── Build matrices ──
    matrix_stats = _build_matrices(conn, symbol, timeframe, total_candles)
    
    # Format distribution as percentages
    dist = {}
    for state in STATE_NAMES:
        count = state_counts.get(state, 0)
        pct = (count / total_candles * 100) if total_candles > 0 else 0
        dist[state] = f"{count:,} ({pct:.1f}%)"
    
    return {
        "candles_classified": total_candles,
        "transitions_found": len(transition_rows),
        "state_distribution": dist,
        "matrix": matrix_stats,
    }


def _compute_raw_score(adx, rsi, macd_h, stoch_k, cci, ema_s, ema_m, atr) -> float:
    """Compute the raw directional score (same logic as classify_regime, returns float)."""
    score = 0.0
    
    rsi_signal = (rsi - 50.0) / 50.0
    score += rsi_signal * 0.20
    
    safe_atr = max(atr, 0.001)
    macd_norm = macd_h / safe_atr
    macd_signal = max(-1.0, min(1.0, math.tanh(macd_norm * 3.0)))
    score += macd_signal * 0.25
    
    stoch_signal = (stoch_k - 50.0) / 50.0
    score += stoch_signal * 0.15
    
    cci_signal = max(-1.0, min(1.0, math.tanh(cci / 150.0)))
    score += cci_signal * 0.15
    
    if ema_m and ema_m > 0:
        ema_diff = (ema_s - ema_m) / ema_m * 100.0
        ema_signal = max(-1.0, min(1.0, math.tanh(ema_diff * 3.0)))
    else:
        ema_signal = 0.0
    score += ema_signal * 0.25
    
    trend_strength = min(adx / 40.0, 1.0) if adx > 0 else 0.0
    
    if adx < 20:
        dampened = score * 0.4
    elif adx < 25:
        dampened = score * 0.7
    else:
        boost = 1.0 + (trend_strength - 0.5) * 0.6
        dampened = score * boost
    
    return max(-1.0, min(1.0, dampened))


# ═══════════════════════════════════════════════════════════════════════════
# MATRIX BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def _build_matrices(conn: sqlite3.Connection, symbol: str, timeframe: str,
                    sample_count: int) -> Dict:
    """
    Build all transition matrices from regime_transitions table.
    
    Produces:
      - Main 5x5 probability matrix
      - Duration-conditional matrices (early/mature/extended)
      - Duration statistics per state
      - Stationary distribution
    """
    
    # ── 1. Build frequency matrix from transitions ──
    freq = [[0] * NUM_STATES for _ in range(NUM_STATES)]
    
    # Also build duration-bucketed frequency matrices
    dur_freq = {
        bucket: [[0] * NUM_STATES for _ in range(NUM_STATES)]
        for bucket in DURATION_BUCKETS
    }
    
    # Duration tracking per state
    durations_by_state = defaultdict(list)
    
    transitions = conn.execute("""
        SELECT from_state, to_state, duration_candles
        FROM regime_transitions
        WHERE timeframe = ?
        ORDER BY timestamp ASC
    """, (timeframe,)).fetchall()
    
    for row in transitions:
        from_s = row["from_state"]
        to_s = row["to_state"]
        dur = row["duration_candles"]
        
        fi = STATE_INDEX.get(from_s)
        ti = STATE_INDEX.get(to_s)
        
        if fi is None or ti is None:
            continue
        
        # Main frequency matrix
        freq[fi][ti] += 1
        
        # Duration-bucketed
        for bucket_name, (lo, hi) in DURATION_BUCKETS.items():
            if lo <= dur <= hi:
                dur_freq[bucket_name][fi][ti] += 1
                break
        
        # Track durations
        durations_by_state[from_s].append(dur)
    
    # Also count self-transitions (persistence) from regime_history
    # A candle that stays in the same state as the previous candle is a self-transition
    history = conn.execute("""
        SELECT regime_state, candles_in_state
        FROM regime_history
        WHERE timeframe = ?
        ORDER BY timestamp ASC
    """, (timeframe,)).fetchall()
    
    prev_state = None
    for row in history:
        state = row["regime_state"]
        si = STATE_INDEX.get(state)
        if si is not None and prev_state is not None:
            pi = STATE_INDEX.get(prev_state)
            if pi is not None:
                # This is a candle-to-candle transition (including self)
                freq[pi][si] += 1
        prev_state = state
    
    # Wait — the above double-counts. The transitions table only has STATE CHANGES.
    # For the full matrix including persistence, I need candle-to-candle data.
    # Let me redo this properly.
    
    # ── REBUILD: Candle-to-candle frequency matrix ──
    freq = [[0] * NUM_STATES for _ in range(NUM_STATES)]
    dur_freq = {
        bucket: [[0] * NUM_STATES for _ in range(NUM_STATES)]
        for bucket in DURATION_BUCKETS
    }
    
    prev_state_name = None
    prev_candles_in = 0
    for row in history:
        state = row["regime_state"]
        candles_in = row["candles_in_state"]
        
        si = STATE_INDEX.get(state)
        if si is not None and prev_state_name is not None:
            pi = STATE_INDEX.get(prev_state_name)
            if pi is not None:
                freq[pi][si] += 1
                
                # Duration bucket based on how long we've been in the FROM state
                for bucket_name, (lo, hi) in DURATION_BUCKETS.items():
                    if lo <= prev_candles_in <= hi:
                        dur_freq[bucket_name][pi][si] += 1
                        break
        
        prev_state_name = state
        prev_candles_in = candles_in
    
    # ── 2. Normalize to probability matrices ──
    prob_matrix = _normalize_matrix(freq)
    
    dur_prob_matrices = {}
    for bucket_name, f_matrix in dur_freq.items():
        dur_prob_matrices[bucket_name] = _normalize_matrix(f_matrix)
    
    # ── 3. Duration statistics ──
    duration_stats = {}
    for state in STATE_NAMES:
        durs = durations_by_state.get(state, [])
        if durs:
            sorted_durs = sorted(durs)
            n = len(sorted_durs)
            duration_stats[state] = {
                "count": n,
                "mean": round(sum(durs) / n, 1),
                "median": sorted_durs[n // 2],
                "min": sorted_durs[0],
                "max": sorted_durs[-1],
                "p25": sorted_durs[n // 4] if n >= 4 else sorted_durs[0],
                "p75": sorted_durs[3 * n // 4] if n >= 4 else sorted_durs[-1],
            }
        else:
            duration_stats[state] = {
                "count": 0, "mean": 0, "median": 0,
                "min": 0, "max": 0, "p25": 0, "p75": 0
            }
    
    # ── 4. Stationary distribution ──
    stationary = _compute_stationary(prob_matrix)
    
    # ── 5. Get date range ──
    range_row = conn.execute("""
        SELECT MIN(timestamp), MAX(timestamp) FROM regime_history WHERE timeframe = ?
    """, (timeframe,)).fetchone()
    
    transition_count = sum(sum(row) for row in freq) - sum(freq[i][i] for i in range(NUM_STATES))
    
    # ── 6. Save to regime_matrix table ──
    conn.execute("""
        INSERT OR REPLACE INTO regime_matrix
        (symbol, timeframe, matrix_data, frequency_data, duration_matrices,
         duration_stats, stationary_dist, sample_count, transition_count,
         date_range_start, date_range_end, classification_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        symbol, timeframe,
        json.dumps(_round_matrix(prob_matrix, 6)),
        json.dumps(freq),
        json.dumps({k: _round_matrix(v, 6) for k, v in dur_prob_matrices.items()}),
        json.dumps(duration_stats),
        json.dumps({k: round(v, 6) for k, v in stationary.items()}),
        sample_count,
        transition_count,
        range_row[0] if range_row else None,
        range_row[1] if range_row else None,
        1
    ))
    conn.commit()
    
    # ── Print summary ──
    print(f"\n  ── TRANSITION MATRIX ({timeframe}) ──")
    print(f"  {'':15s}", end="")
    for name in STATE_NAMES:
        print(f"{name:>13s}", end="")
    print()
    
    for i, from_name in enumerate(STATE_NAMES):
        print(f"  {from_name:15s}", end="")
        for j in range(NUM_STATES):
            val = prob_matrix[i][j]
            print(f"{val:13.3f}", end="")
        row_sum = sum(prob_matrix[i])
        print(f"  | Σ={row_sum:.3f}")
    
    print(f"\n  ── STATIONARY DISTRIBUTION ──")
    for name in STATE_NAMES:
        val = stationary.get(name, 0)
        bar = "█" * int(val * 50)
        print(f"  {name:15s} {val:.3f}  {bar}")
    
    print(f"\n  ── DURATION STATS (candles in state before transitioning) ──")
    for name in STATE_NAMES:
        s = duration_stats[name]
        if s["count"] > 0:
            print(f"  {name:15s} mean={s['mean']:5.1f}  median={s['median']:3d}  "
                  f"range=[{s['min']}-{s['max']}]  n={s['count']}")
    
    return {
        "prob_matrix": prob_matrix,
        "frequency_matrix": freq,
        "stationary": stationary,
        "duration_stats": duration_stats,
        "transition_count": transition_count,
    }


def _normalize_matrix(freq: List[List[int]]) -> List[List[float]]:
    """Convert frequency matrix to probability matrix. Each row sums to 1.0."""
    prob = []
    for row in freq:
        row_sum = sum(row)
        if row_sum > 0:
            prob.append([c / row_sum for c in row])
        else:
            # Uniform if no data
            prob.append([1.0 / NUM_STATES] * NUM_STATES)
    return prob


def _round_matrix(matrix: List[List[float]], decimals: int = 4) -> List[List[float]]:
    return [[round(v, decimals) for v in row] for row in matrix]


def _compute_stationary(prob_matrix: List[List[float]]) -> Dict[str, float]:
    """
    Compute stationary distribution via power iteration.
    This is the long-run equilibrium: if the market runs forever,
    what fraction of time does it spend in each state?
    """
    n = NUM_STATES
    # Start uniform
    dist = [1.0 / n] * n
    
    # Power iteration (matrix × vector)
    for _ in range(200):
        new_dist = [0.0] * n
        for j in range(n):
            for i in range(n):
                new_dist[j] += dist[i] * prob_matrix[i][j]
        
        # Check convergence
        diff = sum(abs(new_dist[i] - dist[i]) for i in range(n))
        dist = new_dist
        if diff < 1e-10:
            break
    
    # Normalize (in case of floating point drift)
    total = sum(dist)
    if total > 0:
        dist = [d / total for d in dist]
    
    return {STATE_NAMES[i]: dist[i] for i in range(n)}


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def get_regime_matrix(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Get the computed regime matrix for a symbol+timeframe.
    Returns None if not yet computed (run backfill_regime_data first).
    """
    sym_config = SYMBOL_DATABASES.get(symbol)
    if not sym_config:
        return None
    
    db_path = sym_config["db_path"]
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    row = conn.execute("""
        SELECT * FROM regime_matrix 
        WHERE symbol = ? AND timeframe = ?
        ORDER BY computed_at DESC LIMIT 1
    """, (symbol, timeframe)).fetchone()
    
    conn.close()
    
    if not row:
        return None
    
    return {
        "symbol": row["symbol"],
        "timeframe": row["timeframe"],
        "matrix": json.loads(row["matrix_data"]),
        "frequencies": json.loads(row["frequency_data"]),
        "duration_matrices": json.loads(row["duration_matrices"]) if row["duration_matrices"] else {},
        "duration_stats": json.loads(row["duration_stats"]) if row["duration_stats"] else {},
        "stationary": json.loads(row["stationary_dist"]) if row["stationary_dist"] else {},
        "sample_count": row["sample_count"],
        "transition_count": row["transition_count"],
        "date_range": (row["date_range_start"], row["date_range_end"]),
        "computed_at": row["computed_at"],
    }


def get_current_regime(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Get the current (most recent) regime state for a symbol+timeframe.
    """
    sym_config = SYMBOL_DATABASES.get(symbol)
    if not sym_config:
        return None
    
    db_path = sym_config["db_path"]
    if not os.path.exists(db_path):
        return None
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    row = conn.execute("""
        SELECT regime_state, regime_score, candles_in_state, close_price, timestamp
        FROM regime_history
        WHERE timeframe = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (timeframe,)).fetchone()
    
    conn.close()
    
    if not row:
        return None
    
    return {
        "state": row["regime_state"],
        "score": row["regime_score"],
        "candles_in_state": row["candles_in_state"],
        "close": row["close_price"],
        "timestamp": row["timestamp"],
    }


def get_next_state_probabilities(symbol: str, timeframe: str) -> Optional[Dict]:
    """
    Get probability distribution for the NEXT state, considering
    both the current state AND how long we've been in it (duration-conditional).
    
    This is the key predictive output of the matrix system.
    """
    current = get_current_regime(symbol, timeframe)
    if not current:
        return None
    
    matrix_data = get_regime_matrix(symbol, timeframe)
    if not matrix_data:
        return None
    
    state = current["state"]
    duration = current["candles_in_state"]
    si = STATE_INDEX.get(state)
    
    if si is None:
        return None
    
    # Get the base probability row
    base_probs = matrix_data["matrix"][si]
    
    # Get duration-conditional probabilities
    dur_probs = None
    dur_bucket = None
    for bucket_name, (lo, hi) in DURATION_BUCKETS.items():
        if lo <= duration <= hi:
            dur_bucket = bucket_name
            dur_matrices = matrix_data.get("duration_matrices", {})
            if bucket_name in dur_matrices:
                dur_probs = dur_matrices[bucket_name][si]
            break
    
    # Build result
    result = {
        "current_state": state,
        "candles_in_state": duration,
        "duration_bucket": dur_bucket,
        "base_probabilities": {STATE_NAMES[i]: round(base_probs[i], 4) for i in range(NUM_STATES)},
    }
    
    if dur_probs:
        result["duration_adjusted"] = {STATE_NAMES[i]: round(dur_probs[i], 4) for i in range(NUM_STATES)}
    
    # Persistence probability (staying in same state)
    result["persistence"] = round(base_probs[si], 4)
    if dur_probs:
        result["persistence_adjusted"] = round(dur_probs[si], 4)
    
    # Most likely next state (excluding self)
    candidates = [(STATE_NAMES[i], base_probs[i]) for i in range(NUM_STATES) if i != si]
    candidates.sort(key=lambda x: x[1], reverse=True)
    result["most_likely_transition"] = candidates[0] if candidates else None
    
    # Duration stats for current state
    dur_stats = matrix_data.get("duration_stats", {}).get(state)
    if dur_stats:
        result["avg_regime_duration"] = dur_stats["mean"]
        result["median_regime_duration"] = dur_stats["median"]
        result["duration_percentile"] = _duration_percentile(duration, dur_stats)
    
    return result


def _duration_percentile(current_duration: int, stats: Dict) -> float:
    """Estimate what percentile the current duration is at."""
    if stats["count"] == 0 or stats["max"] == 0:
        return 0.0
    # Simple linear interpolation between min and max
    # (Would be more accurate with the full distribution, but this is a good estimate)
    if current_duration <= stats["min"]:
        return 0.0
    if current_duration >= stats["max"]:
        return 100.0
    return min(100.0, (current_duration - stats["min"]) / (stats["max"] - stats["min"]) * 100.0)


# ═══════════════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _safe(val, default=0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import time
    
    symbols = sys.argv[1:] if len(sys.argv) > 1 else list(SYMBOL_DATABASES.keys())
    
    print(f"\n{'═'*60}")
    print(f"  REGIME CLASSIFIER — FULL BACKFILL")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"{'═'*60}")
    
    for symbol in symbols:
        start = time.time()
        results = backfill_regime_data(symbol)
        elapsed = time.time() - start
        
        print(f"\n  {symbol} completed in {elapsed:.1f}s")
        for tf, stats in results.items():
            if isinstance(stats, dict) and "candles_classified" in stats:
                print(f"    {tf}: {stats['candles_classified']:,} candles, "
                      f"{stats['transitions_found']:,} transitions")
    
    print(f"\n{'═'*60}")
    print(f"  BACKFILL COMPLETE")
    print(f"{'═'*60}\n")
