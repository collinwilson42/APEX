"""
CYTO SIMULATOR — Mock Sentiment + Trade Generator
==================================================
Generates realistic random-walk sentiment vectors and trades
for all 6 asset classes at real 15-minute intervals.

Triggered by double-tapping ACTIVE on the Algorithm page.
Writes to cyto_v3.db via CytoIntegration.

Design:
- All asset classes share one radial view (stacked on same layer)
- Each INSTANCE gets its own z-layer in the database
- 1H sentiment persists (sticky) for 4 bars until next hourly eval
- Trades fire ~20-30% of bars with random-walk P/L
- Radius = percentile position (0.618=worst → 1.618=best)

Seed 15BE — Simulation Integration
"""

import os
import sys
import json
import math
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add Cyto directory to path (lazy — actual imports happen at runtime)
CYTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '#Cyto')
if CYTO_DIR not in sys.path:
    sys.path.insert(0, CYTO_DIR)

# Lazy imports — these modules have deep dependency chains that
# can fail at import time. We load them when actually needed.
_cyto_integration_module = None
_cyto_schema_module = None

def _load_cyto_modules():
    """Load Cyto modules lazily to avoid import-time failures."""
    global _cyto_integration_module, _cyto_schema_module
    if _cyto_integration_module is None:
        # Ensure path is set
        if CYTO_DIR not in sys.path:
            sys.path.insert(0, CYTO_DIR)
        import cyto_integration as ci
        import cyto_schema as cs
        _cyto_integration_module = ci
        _cyto_schema_module = cs
    return _cyto_integration_module, _cyto_schema_module


# ═══════════════════════════════════════════════════════════════════════════
# ASSET CLASS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

ASSET_CLASSES = {
    'BTC': {
        'symbol': 'BTCF26',
        'name': 'Bitcoin Futures',
        'volatility': 0.12,       # Higher volatility → bigger score swings
        'trade_frequency': 0.25,  # 25% chance of trade per bar
        'pnl_scale': 500.0,      # Base P/L magnitude
        'trend_bias': 0.02,      # Slight bullish bias
    },
    'OIL': {
        'symbol': 'USOILH26',
        'name': 'Crude Oil Futures',
        'volatility': 0.08,
        'trade_frequency': 0.30,
        'pnl_scale': 200.0,
        'trend_bias': -0.01,     # Slight bearish
    },
    'GOLD': {
        'symbol': 'XAUJ26',
        'name': 'Gold Futures',
        'volatility': 0.06,
        'trade_frequency': 0.28,
        'pnl_scale': 300.0,
        'trend_bias': 0.015,
    },
    'US100': {
        'symbol': 'US100H26',
        'name': 'Nasdaq 100 Futures',
        'volatility': 0.09,
        'trade_frequency': 0.22,
        'pnl_scale': 250.0,
        'trend_bias': 0.025,
    },
    'US30': {
        'symbol': 'US30H26',
        'name': 'Dow 30 Futures',
        'volatility': 0.07,
        'trade_frequency': 0.24,
        'pnl_scale': 220.0,
        'trend_bias': 0.02,
    },
    'US500': {
        'symbol': 'US500H26',
        'name': 'S&P 500 Futures',
        'volatility': 0.065,
        'trade_frequency': 0.26,
        'pnl_scale': 230.0,
        'trend_bias': 0.018,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# RANDOM WALK GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

class SentimentWalker:
    """
    Generates random-walk sentiment vectors for one asset class.
    
    Each of the 6 vectors drifts independently with mean-reversion.
    The 1H score updates only every 4 bars (sticky).
    """
    
    VECTOR_NAMES = ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']
    
    def __init__(self, volatility: float = 0.08, trend_bias: float = 0.0):
        self.volatility = volatility
        self.trend_bias = trend_bias
        
        # Current state for each vector (-1 to +1)
        self.vectors_15m = {v: random.uniform(-0.3, 0.3) for v in self.VECTOR_NAMES}
        self.vectors_1h = {v: random.uniform(-0.2, 0.2) for v in self.VECTOR_NAMES}
        
        # Weighted scores
        self.weighted_15m = 0.0
        self.weighted_1h = 0.0
        
        # Bar counter for 1H updates
        self.bar_count = 0
    
    def step(self) -> Dict:
        """
        Advance one 15m bar. Returns the full sentiment snapshot.
        
        1H scores only update every 4 bars — they persist in between.
        """
        self.bar_count += 1
        
        # === 15M vectors: update every bar ===
        for v in self.VECTOR_NAMES:
            # Random walk with mean-reversion toward 0
            noise = random.gauss(0, self.volatility)
            reversion = -self.vectors_15m[v] * 0.08  # Pull toward zero
            drift = self.trend_bias * 0.5
            
            self.vectors_15m[v] += noise + reversion + drift
            # Clamp to [-1, 1]
            self.vectors_15m[v] = max(-1.0, min(1.0, self.vectors_15m[v]))
        
        # Calculate 15m weighted average
        weights = [0.20, 0.15, 0.20, 0.15, 0.15, 0.15]
        self.weighted_15m = sum(
            self.vectors_15m[v] * w 
            for v, w in zip(self.VECTOR_NAMES, weights)
        )
        
        # === 1H vectors: update only every 4 bars ===
        if self.bar_count % 4 == 0:
            for v in self.VECTOR_NAMES:
                noise = random.gauss(0, self.volatility * 0.6)  # Less volatile
                reversion = -self.vectors_1h[v] * 0.05
                drift = self.trend_bias
                
                self.vectors_1h[v] += noise + reversion + drift
                self.vectors_1h[v] = max(-1.0, min(1.0, self.vectors_1h[v]))
            
            self.weighted_1h = sum(
                self.vectors_1h[v] * w 
                for v, w in zip(self.VECTOR_NAMES, weights)
            )
        
        # 1H persists between updates (sticky) — no else needed
        
        # Final blend: 70% 15m + 30% 1h
        weighted_final = (self.weighted_15m * 0.7) + (self.weighted_1h * 0.3)
        
        return {
            'vectors_15m': dict(self.vectors_15m),
            'weighted_15m': round(self.weighted_15m, 4),
            'weighted_1h': round(self.weighted_1h, 4),
            'weighted_final': round(weighted_final, 4),
            'bar_number': self.bar_count,
            '1h_updated': self.bar_count % 4 == 0,
        }


class TradeGenerator:
    """
    Generates random trades with realistic P/L distribution.
    
    - Trades fire with configurable probability per bar
    - P/L follows a skewed distribution (many small losses, fewer big wins)
    - Direction aligns with sentiment ~60% of the time
    """
    
    def __init__(self, trade_frequency: float = 0.25, pnl_scale: float = 300.0):
        self.trade_frequency = trade_frequency
        self.pnl_scale = pnl_scale
        self.trade_count = 0
    
    def maybe_trade(self, weighted_final: float) -> Optional[Dict]:
        """
        Possibly generate a trade for this bar.
        
        Returns trade dict or None if no trade.
        """
        if random.random() > self.trade_frequency:
            return None
        
        self.trade_count += 1
        
        # Direction: 60% aligned with sentiment, 40% counter
        if random.random() < 0.6:
            direction = 'long' if weighted_final >= 0 else 'short'
        else:
            direction = 'short' if weighted_final >= 0 else 'long'
        
        # P/L distribution: slightly negative skew (realistic)
        # Use a mix: 55% chance of loss, 45% win, but wins can be bigger
        is_winner = random.random() < 0.45
        
        if is_winner:
            # Winners: 0.5x to 3x scale
            magnitude = random.uniform(0.5, 3.0)
        else:
            # Losers: 0.3x to 1.5x scale
            magnitude = random.uniform(0.3, 1.5)
        
        raw_pnl = magnitude * self.pnl_scale * (1 if is_winner else -1)
        
        # Stronger sentiment alignment → slightly better outcomes
        alignment_bonus = abs(weighted_final) * self.pnl_scale * 0.1
        if (direction == 'long' and weighted_final > 0) or \
           (direction == 'short' and weighted_final < 0):
            raw_pnl += alignment_bonus
        
        return {
            'pnl_raw': round(raw_pnl, 2),
            'pnl_normalized': round(raw_pnl, 2),
            'direction': direction,
            'entry_price': round(random.uniform(1000, 5000), 2),
            'exit_price': round(random.uniform(1000, 5000), 2),
            'volume': round(random.uniform(0.01, 0.5), 2),
        }


# ═══════════════════════════════════════════════════════════════════════════
# CYTO SIMULATOR — Main Orchestrator
# ═══════════════════════════════════════════════════════════════════════════

class CytoSimulator:
    """
    Orchestrates mock sentiment + trade generation for all asset classes.
    
    Runs at real 15-minute intervals.
    Each asset class gets its own walker + trade generator.
    All share one radial view, each instance on its own z-layer.
    
    Start/stop via Flask API (triggered by ACTIVE double-tap).
    """
    
    def __init__(self):
        self.cyto = None  # CytoIntegration instance (loaded lazily)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Per-asset-class state
        self._walkers: Dict[str, SentimentWalker] = {}
        self._traders: Dict[str, TradeGenerator] = {}
        self._instance_ids: Dict[str, str] = {}  # class_key -> instance_id
        
        # Session tracking
        self.session_id: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.bars_generated = 0
        self.trades_generated = 0
        
        # Timing
        self.interval_seconds = 15 * 60  # 15 minutes (real speed)
        
        print("[CytoSim] Simulator initialized")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def start(self) -> Dict:
        """
        Start the simulation. Creates instances for all asset classes.
        
        Returns status dict.
        """
        if self._running:
            return {'success': False, 'error': 'Simulator already running'}
        
        with self._lock:
            # Initialize Cyto integration (lazy load)
            ci_module, cs_module = _load_cyto_modules()
            cs_module.init_db()
            self.cyto = ci_module.get_cyto_integration()
            
            # Generate session ID
            self.session_id = f"SIM_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.started_at = datetime.now()
            self.bars_generated = 0
            self.trades_generated = 0
            
            # Create walkers, traders, and instances for each asset class
            for class_key, config in ASSET_CLASSES.items():
                instance_id = f"{config['symbol']}_{self.session_id}"
                
                # Register instance in CytoBase
                self.cyto.register_instance(
                    instance_id=instance_id,
                    symbol=config['symbol'],
                    profile_name=f"SIM_{class_key}",
                    config={
                        'session': self.session_id,
                        'class': class_key,
                        'volatility': config['volatility'],
                        'trade_frequency': config['trade_frequency'],
                        'pnl_scale': config['pnl_scale'],
                    }
                )
                
                self._instance_ids[class_key] = instance_id
                self._walkers[class_key] = SentimentWalker(
                    volatility=config['volatility'],
                    trend_bias=config['trend_bias']
                )
                self._traders[class_key] = TradeGenerator(
                    trade_frequency=config['trade_frequency'],
                    pnl_scale=config['pnl_scale']
                )
                
                print(f"[CytoSim] Instance created: {instance_id}")
            
            # Start the loop thread
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            
            print(f"[CytoSim] ✓ Simulation STARTED — Session: {self.session_id}")
            print(f"[CytoSim]   Assets: {', '.join(ASSET_CLASSES.keys())}")
            print(f"[CytoSim]   Interval: {self.interval_seconds}s (real 15m)")
            
            return {
                'success': True,
                'session_id': self.session_id,
                'instances': dict(self._instance_ids),
                'interval_seconds': self.interval_seconds,
                'asset_classes': list(ASSET_CLASSES.keys()),
            }
    
    def stop(self) -> Dict:
        """Stop the simulation gracefully."""
        if not self._running:
            return {'success': False, 'error': 'Simulator not running'}
        
        with self._lock:
            self._running = False
        
        if self._thread:
            self._thread.join(timeout=10)
        
        # Flush any pending bars
        if self.cyto:
            self.cyto.flush_pending_bars()
            
            # Mark instances as completed
            for class_key, instance_id in self._instance_ids.items():
                self.cyto.complete_instance(instance_id)
        
        elapsed = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        
        result = {
            'success': True,
            'session_id': self.session_id,
            'bars_generated': self.bars_generated,
            'trades_generated': self.trades_generated,
            'runtime_seconds': round(elapsed, 1),
        }
        
        print(f"[CytoSim] ✓ Simulation STOPPED — {self.bars_generated} bars, {self.trades_generated} trades")
        
        # Reset state
        self._walkers.clear()
        self._traders.clear()
        self._instance_ids.clear()
        self.session_id = None
        
        return result
    
    def _run_loop(self):
        """Main simulation loop — runs at real 15m intervals."""
        
        # Run first bar immediately
        self._tick()
        
        while self._running:
            # Sleep in small increments so we can stop quickly
            for _ in range(self.interval_seconds):
                if not self._running:
                    return
                time.sleep(1)
            
            if self._running:
                self._tick()
    
    def _tick(self):
        """Generate one bar of data for all asset classes."""
        now = datetime.now()
        
        with self._lock:
            for class_key, config in ASSET_CLASSES.items():
                instance_id = self._instance_ids.get(class_key)
                if not instance_id:
                    continue
                
                walker = self._walkers[class_key]
                trader = self._traders[class_key]
                
                # Step sentiment forward
                sentiment = walker.step()
                
                # Maybe generate a trade
                trade_data = trader.maybe_trade(sentiment['weighted_final'])
                
                if trade_data:
                    # Add timestamps to trade
                    trade_data['entry_time'] = (now - timedelta(minutes=random.randint(1, 14))).isoformat()
                    trade_data['exit_time'] = now.isoformat()
                    self.trades_generated += 1
                
                # Feed 1H sentiment (sticky — only on hourly bars)
                if sentiment['1h_updated']:
                    self.cyto.on_sentiment_reading(
                        instance_id=instance_id,
                        reading={
                            'timestamp': now.isoformat(),
                            'price_action_score': walker.vectors_1h['v1'],
                            'key_levels_score': walker.vectors_1h['v2'],
                            'momentum_score': walker.vectors_1h['v3'],
                            'volume_score': walker.vectors_1h['v4'],
                            'structure_score': walker.vectors_1h['v5'],
                            'composite_score': walker.vectors_1h['v6'],
                        },
                        timeframe='1h'
                    )
                
                # Feed 15m sentiment (every bar)
                self.cyto.on_sentiment_reading(
                    instance_id=instance_id,
                    reading={
                        'timestamp': now.isoformat(),
                        'price_action_score': sentiment['vectors_15m']['v1'],
                        'key_levels_score': sentiment['vectors_15m']['v2'],
                        'momentum_score': sentiment['vectors_15m']['v3'],
                        'volume_score': sentiment['vectors_15m']['v4'],
                        'structure_score': sentiment['vectors_15m']['v5'],
                        'composite_score': sentiment['vectors_15m']['v6'],
                    },
                    timeframe='15m'
                )
                
                # Feed trade if one occurred
                if trade_data:
                    self.cyto.on_trade_close(
                        instance_id=instance_id,
                        trade_data=trade_data
                    )
                else:
                    # No trade — flush the pending bar as a node anyway
                    self.cyto.flush_pending_bars()
            
            self.bars_generated += 1
            
            # Log progress
            if self.bars_generated % 1 == 0:  # Every bar
                print(f"[CytoSim] Bar {self.bars_generated} @ {now.strftime('%H:%M:%S')} "
                      f"— {self.trades_generated} total trades")
    
    def get_status(self) -> Dict:
        """Get current simulator status."""
        elapsed = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0
        
        # Get instance stats
        instance_stats = {}
        if self.cyto and self._instance_ids:
            for class_key, instance_id in self._instance_ids.items():
                try:
                    stats = self.cyto.get_instance_stats(instance_id)
                    instance_stats[class_key] = {
                        'instance_id': instance_id,
                        'nodes': stats.get('total_nodes', 0),
                        'trades': stats.get('total_trades', 0),
                        'pnl': round(stats.get('total_pnl', 0) or 0, 2),
                        'avg_sentiment': round(stats.get('avg_sentiment', 0) or 0, 4),
                        'win_rate': round((stats.get('win_rate', 0) or 0) * 100, 1),
                    }
                except Exception:
                    instance_stats[class_key] = {'instance_id': instance_id, 'error': True}
        
        return {
            'running': self._running,
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'runtime_seconds': round(elapsed, 1),
            'bars_generated': self.bars_generated,
            'trades_generated': self.trades_generated,
            'interval_seconds': self.interval_seconds,
            'instances': instance_stats,
        }


# ═══════════════════════════════════════════════════════════════════════════
# FLASK API ROUTES
# ═══════════════════════════════════════════════════════════════════════════

# Global simulator instance
_simulator: Optional[CytoSimulator] = None


def get_simulator() -> CytoSimulator:
    """Get or create the global simulator."""
    global _simulator
    if _simulator is None:
        _simulator = CytoSimulator()
    return _simulator


def register_simulator_routes(app):
    """Register Flask routes for the CytoBase simulator."""
    from flask import jsonify, request
    
    @app.route('/api/cyto/sim/start', methods=['POST'])
    def cyto_sim_start():
        """Start the CytoBase simulator."""
        sim = get_simulator()
        result = sim.start()
        return jsonify(result)
    
    @app.route('/api/cyto/sim/stop', methods=['POST'])
    def cyto_sim_stop():
        """Stop the CytoBase simulator."""
        sim = get_simulator()
        result = sim.stop()
        return jsonify(result)
    
    @app.route('/api/cyto/sim/status', methods=['GET'])
    def cyto_sim_status():
        """Get simulator status."""
        sim = get_simulator()
        return jsonify(sim.get_status())
    
    @app.route('/api/cyto/sim/toggle', methods=['POST'])
    def cyto_sim_toggle():
        """Toggle simulator on/off (used by ACTIVE button)."""
        sim = get_simulator()
        if sim.is_running:
            result = sim.stop()
        else:
            result = sim.start()
        return jsonify(result)
    
    print("✓ CytoBase simulator routes registered")
