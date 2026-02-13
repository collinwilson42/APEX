"""
INSTANCE RUNNER — Standalone Per-Symbol Process
================================================
This is the independent process that runs for each trading instance.
Spawned by ProcessManager via subprocess.Popen.

Each instance_runner.py process:
- Has its own Python runtime
- Has its own database connection
- Has its own event loop
- Writes to the shared SQLite database (WAL mode)
- Exits cleanly on SIGTERM/CTRL_BREAK

Usage:
    python instance_runner.py --symbol BTC --mode SIM
    python instance_runner.py --symbol GOLD --mode SIM --speed 0.01  # Fast test
    python instance_runner.py --symbol US100 --mode LIVE

Seed 16 — The Independent Instances
"""

import os
import sys
import json
import math
import random
import signal
import argparse
import time
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging(symbol: str, mode: str):
    prefix = f"[{symbol}-{mode}]"
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s {prefix} %(message)s',
        datefmt='%H:%M:%S',
    )
    return logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ASSET CLASS CONFIG
# ═══════════════════════════════════════════════════════════════════════════

ASSET_CLASSES = {
    'BTC': {'symbol': 'BTCF26', 'name': 'Bitcoin Futures', 'volatility': 0.12, 'trade_frequency': 0.25, 'pnl_scale': 500.0, 'trend_bias': 0.02},
    'OIL': {'symbol': 'USOILH26', 'name': 'Crude Oil Futures', 'volatility': 0.08, 'trade_frequency': 0.30, 'pnl_scale': 200.0, 'trend_bias': -0.01},
    'GOLD': {'symbol': 'XAUJ26', 'name': 'Gold Futures', 'volatility': 0.06, 'trade_frequency': 0.28, 'pnl_scale': 300.0, 'trend_bias': 0.015},
    'US100': {'symbol': 'US100H26', 'name': 'Nasdaq 100 Futures', 'volatility': 0.09, 'trade_frequency': 0.22, 'pnl_scale': 250.0, 'trend_bias': 0.025},
    'US30': {'symbol': 'US30H26', 'name': 'Dow 30 Futures', 'volatility': 0.07, 'trade_frequency': 0.24, 'pnl_scale': 220.0, 'trend_bias': 0.02},
    'US500': {'symbol': 'US500H26', 'name': 'S&P 500 Futures', 'volatility': 0.065, 'trade_frequency': 0.26, 'pnl_scale': 230.0, 'trend_bias': 0.018},
}


# ═══════════════════════════════════════════════════════════════════════════
# SENTIMENT WALKER
# ═══════════════════════════════════════════════════════════════════════════

class SentimentWalker:
    def __init__(self, volatility=0.08, trend_bias=0.0):
        self.volatility = volatility
        self.trend_bias = trend_bias
        self.mean_reversion = 0.15
        self.vectors = [random.uniform(-0.3, 0.3) for _ in range(6)]
        self._1h_score = 0.0
        self._bar_count = 0
    
    def step(self):
        self._bar_count += 1
        for i in range(6):
            noise = random.gauss(0, self.volatility)
            reversion = -self.vectors[i] * self.mean_reversion
            self.vectors[i] += noise + reversion + self.trend_bias
            self.vectors[i] = max(-1.0, min(1.0, self.vectors[i]))
        
        weighted_15m = sum(self.vectors) / 6.0
        if self._bar_count % 4 == 1:
            self._1h_score = weighted_15m + random.gauss(0, self.volatility * 0.5)
            self._1h_score = max(-1.0, min(1.0, self._1h_score))
        
        weighted_1h = self._1h_score
        weighted_final = (weighted_15m + weighted_1h) / 2.0
        agreement_score = max(0.0, min(1.0, 1.0 - abs(weighted_15m - weighted_1h)))
        
        return {
            'v1': round(self.vectors[0], 4), 'v2': round(self.vectors[1], 4),
            'v3': round(self.vectors[2], 4), 'v4': round(self.vectors[3], 4),
            'v5': round(self.vectors[4], 4), 'v6': round(self.vectors[5], 4),
            'weighted_15m': round(weighted_15m, 4), 'weighted_1h': round(weighted_1h, 4),
            'weighted_final': round(weighted_final, 4), 'agreement_score': round(agreement_score, 4),
            'is_hourly': self._bar_count % 4 == 1,
        }


# ═══════════════════════════════════════════════════════════════════════════
# TRADE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

class TradeGenerator:
    def __init__(self, trade_frequency=0.25, pnl_scale=300.0):
        self.trade_frequency = trade_frequency
        self.pnl_scale = pnl_scale
        self._cumulative_pnl = 0.0
        self._trade_count = 0
        self._pnl_history = []
    
    def maybe_trade(self, sentiment):
        if random.random() > self.trade_frequency:
            return None
        
        self._trade_count += 1
        final = sentiment['weighted_final']
        direction = 'BUY' if final > 0 else 'SELL' if final < 0 else random.choice(['BUY', 'SELL'])
        raw_pnl = random.gauss(self.pnl_scale * 0.05, self.pnl_scale * 0.8)
        
        if (direction == 'BUY' and final > 0.3) or (direction == 'SELL' and final < -0.3):
            raw_pnl += abs(raw_pnl) * 0.2
        
        raw_pnl = round(raw_pnl, 2)
        self._cumulative_pnl += raw_pnl
        self._pnl_history.append(raw_pnl)
        
        radius = self._calc_radius(raw_pnl)
        return {
            'direction': direction, 'raw_pnl': raw_pnl,
            'cumulative_pnl': round(self._cumulative_pnl, 2),
            'radius': radius, 'trade_number': self._trade_count,
        }
    
    def _calc_radius(self, pnl):
        if len(self._pnl_history) < 2:
            return 1.0
        sorted_history = sorted(self._pnl_history)
        rank = sorted_history.index(pnl)
        percentile = rank / (len(sorted_history) - 1)
        return round(0.618 + percentile * (1.618 - 0.618), 4)


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE WRITER
# ═══════════════════════════════════════════════════════════════════════════

class CytoDBWriter:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self._ensure_db()
    
    def _ensure_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=30)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.row_factory = sqlite3.Row
        
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                class_key TEXT,
                name TEXT,
                mode TEXT DEFAULT 'SIM',
                state TEXT DEFAULT 'running',
                z_layer INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                pid INTEGER,
                config TEXT
            );
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER NOT NULL,
                theta_slot INTEGER NOT NULL,
                epoch INTEGER DEFAULT 0,
                v1 REAL, v2 REAL, v3 REAL, v4 REAL, v5 REAL, v6 REAL,
                weighted_15m REAL, weighted_1h REAL, weighted_final REAL,
                agreement_score REAL, bar_timestamp TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (instance_id) REFERENCES instances(id)
            );
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instance_id INTEGER NOT NULL,
                node_id INTEGER,
                direction TEXT, raw_pnl REAL, cumulative_pnl REAL,
                radius REAL, trade_number INTEGER, bar_timestamp TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (instance_id) REFERENCES instances(id),
                FOREIGN KEY (node_id) REFERENCES nodes(id)
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_instance ON nodes(instance_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_slot ON nodes(instance_id, theta_slot);
            CREATE INDEX IF NOT EXISTS idx_trades_instance ON trades(instance_id);
        """)
        self.conn.commit()
    
    def create_instance(self, symbol, class_key, name, mode, pid, z_layer=0):
        cursor = self.conn.execute(
            "INSERT INTO instances (symbol, class_key, name, mode, state, z_layer, pid) VALUES (?, ?, ?, ?, 'running', ?, ?)",
            (symbol, class_key, name, mode, z_layer, pid))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_node(self, instance_id, theta_slot, sentiment, bar_timestamp, epoch=0):
        cursor = self.conn.execute("""
            INSERT INTO nodes (instance_id, theta_slot, epoch, v1, v2, v3, v4, v5, v6,
                weighted_15m, weighted_1h, weighted_final, agreement_score, bar_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (instance_id, theta_slot, epoch,
             sentiment['v1'], sentiment['v2'], sentiment['v3'],
             sentiment['v4'], sentiment['v5'], sentiment['v6'],
             sentiment['weighted_15m'], sentiment['weighted_1h'],
             sentiment['weighted_final'], sentiment['agreement_score'],
             bar_timestamp))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_trade(self, instance_id, node_id, trade, bar_timestamp):
        cursor = self.conn.execute("""
            INSERT INTO trades (instance_id, node_id, direction, raw_pnl,
                cumulative_pnl, radius, trade_number, bar_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (instance_id, node_id, trade['direction'], trade['raw_pnl'],
             trade['cumulative_pnl'], trade['radius'], trade['trade_number'],
             bar_timestamp))
        self.conn.commit()
        return cursor.lastrowid
    
    def update_instance_state(self, instance_id, state):
        self.conn.execute("UPDATE instances SET state = ?, updated_at = datetime('now') WHERE id = ?", (state, instance_id))
        self.conn.commit()
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None


# ═══════════════════════════════════════════════════════════════════════════
# INSTANCE RUNNER — Main event loop
# ═══════════════════════════════════════════════════════════════════════════

class InstanceRunner:
    def __init__(self, symbol, mode, base_dir, interval=900, speed=1.0):
        self.symbol = symbol.upper()
        self.mode = mode.upper()
        self.base_dir = base_dir
        self.interval = interval
        self.speed = speed
        
        if self.symbol not in ASSET_CLASSES:
            raise ValueError(f"Unknown symbol: {self.symbol}")
        
        self.config = ASSET_CLASSES[self.symbol]
        self.logger = setup_logging(self.symbol, self.mode)
        
        self.walker = SentimentWalker(volatility=self.config['volatility'], trend_bias=self.config['trend_bias'])
        self.trader = TradeGenerator(trade_frequency=self.config['trade_frequency'], pnl_scale=self.config['pnl_scale'])
        
        # Database path
        db_path = os.path.join(base_dir, '#Cyto', 'cyto_v3.db')
        if not os.path.exists(os.path.join(base_dir, '#Cyto')):
            os.makedirs(os.path.join(base_dir, '#Cyto'), exist_ok=True)
        self.db = CytoDBWriter(db_path)
        
        self.instance_id = None
        self.bars_generated = 0
        self.trades_generated = 0
        self._shutdown_requested = False
        
        self.logger.info(f"Initialized — {self.config['name']} ({self.mode})")
        self.logger.info(f"DB: {db_path}")
        self.logger.info(f"Interval: {interval}s × {speed} speed = {interval * speed}s real")
    
    def _register_signals(self):
        def handle_shutdown(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown_requested = True
        
        signal.signal(signal.SIGTERM, handle_shutdown)
        signal.signal(signal.SIGINT, handle_shutdown)
        if os.name == 'nt':
            try:
                signal.signal(signal.SIGBREAK, handle_shutdown)
            except (AttributeError, ValueError):
                pass
    
    def run(self):
        self._register_signals()
        
        self.instance_id = self.db.create_instance(
            symbol=self.config['symbol'], class_key=self.symbol,
            name=self.config['name'], mode=self.mode,
            pid=os.getpid(),
            z_layer=list(ASSET_CLASSES.keys()).index(self.symbol),
        )
        
        self.logger.info(f"✓ Instance created — ID: {self.instance_id}, PID: {os.getpid()}")
        self._tick()  # First bar immediately
        
        tick_interval = self.interval * self.speed
        
        try:
            while not self._shutdown_requested:
                sleep_remaining = tick_interval
                while sleep_remaining > 0 and not self._shutdown_requested:
                    chunk = min(sleep_remaining, 1.0)
                    time.sleep(chunk)
                    sleep_remaining -= chunk
                
                if not self._shutdown_requested:
                    self._tick()
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received")
        finally:
            self._shutdown()
    
    def _tick(self):
        now = datetime.now()
        bar_timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        minutes_since_midnight = now.hour * 60 + now.minute
        theta_slot = (minutes_since_midnight // 15) % 288
        
        sentiment = self.walker.step()
        node_id = self.db.add_node(
            instance_id=self.instance_id, theta_slot=theta_slot,
            sentiment=sentiment, bar_timestamp=bar_timestamp,
        )
        self.bars_generated += 1
        
        trade = self.trader.maybe_trade(sentiment)
        trade_str = ""
        if trade:
            self.db.add_trade(
                instance_id=self.instance_id, node_id=node_id,
                trade=trade, bar_timestamp=bar_timestamp,
            )
            self.trades_generated += 1
            trade_str = f" | TRADE: {trade['direction']} pnl={trade['raw_pnl']:+.2f} r={trade['radius']:.3f}"
        
        self.logger.info(
            f"Bar {self.bars_generated} | slot={theta_slot} | "
            f"15m={sentiment['weighted_15m']:+.4f} | "
            f"1h={sentiment['weighted_1h']:+.4f} | "
            f"final={sentiment['weighted_final']:+.4f}"
            f"{trade_str}"
        )
    
    def _shutdown(self):
        if self.instance_id and self.db:
            try:
                self.db.update_instance_state(self.instance_id, 'stopped')
            except Exception as e:
                self.logger.error(f"Failed to update instance state: {e}")
        if self.db:
            self.db.close()
        self.logger.info(f"✓ Shutdown complete — {self.bars_generated} bars, {self.trades_generated} trades")


# ═══════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Instance Runner — Independent Trading Process')
    parser.add_argument('--symbol', required=True, choices=list(ASSET_CLASSES.keys()))
    parser.add_argument('--mode', default='SIM', choices=['SIM', 'LIVE'])
    parser.add_argument('--interval', type=int, default=900)
    parser.add_argument('--speed', type=float, default=1.0)
    parser.add_argument('--base-dir', default=None)
    args = parser.parse_args()
    
    base_dir = args.base_dir or os.path.dirname(os.path.abspath(__file__))
    runner = InstanceRunner(symbol=args.symbol, mode=args.mode, base_dir=base_dir,
                            interval=args.interval, speed=args.speed)
    runner.run()

if __name__ == '__main__':
    main()
