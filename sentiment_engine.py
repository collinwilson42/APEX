"""
APEX Sentiment Engine v2
========================
Scheduled sentiment analysis using Claude Vision API

Schedule:
- 15m analysis: X:01, X:16, X:31, X:46 (1 minute after candle close)
- 1m analysis: Every odd minute (X:01, X:03, X:05...)

Five Narrative Categories (text descriptions, no scores):
1. Price Action - What is price doing right now?
2. Key Levels - What's above and below?
3. Momentum - Is the move strengthening or weakening?
4. Volume Story - What's participation telling us?
5. Structure - What pattern or regime is forming?

Output: Stored to SQLite, exposed via Flask API for frontend/profiles
"""

import os
import json
import base64
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import threading
import time

# Optional imports - graceful degradation if not installed
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[WARN] anthropic package not installed - using mock mode")

try:
    import mss
    import mss.tools
    HAS_MSS = True
except ImportError:
    HAS_MSS = False
    print("[WARN] mss package not installed - screenshot capture disabled")

# Instance database for Phase 3 integration
try:
    from instance_database import get_instance_db
    HAS_INSTANCE_DB = True
except ImportError:
    HAS_INSTANCE_DB = False
    print("[WARN] instance_database not available - instance tables will not be populated")


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SentimentConfig:
    """Configuration for the sentiment engine"""
    # API
    api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1500
    
    # Database
    db_path: str = "sentiment_analysis.db"
    
    # Schedule - SEED 13: Migrated from 1m to 1h
    tf_15m_offsets: tuple = (1, 16, 31, 46)  # Minutes after hour for 15m analysis
    tf_1h_offsets: tuple = (2,)  # 2 minutes after hour for 1h analysis (catches closed hourly bar)
    
    # Screenshot region (None = full screen, or (x, y, width, height))
    screenshot_region: Optional[tuple] = None
    
    # Display duration before transitioning back to matrix
    display_duration_seconds: int = 30


# ═══════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SentimentReading:
    """
    Complete sentiment analysis for a timeframe.
    
    Five narrative categories (text descriptions, not scores):
    1. Price Action - What is price doing right now?
    2. Key Levels - What's above and below?
    3. Momentum - Is the move strengthening or weakening?
    4. Volume Story - What's participation telling us?
    5. Structure - What pattern or regime is forming?
    """
    id: Optional[int] = None
    timestamp: str = ""
    symbol: str = ""
    timeframe: str = ""  # "15m" or "1m"
    
    # Five narrative categories - text descriptions
    price_action: str = ""      # What is price doing right now?
    key_levels: str = ""        # What's above and below?
    momentum: str = ""          # Is the move strengthening or weakening?
    volume_story: str = ""      # What's participation telling us?
    structure: str = ""         # What pattern or regime is forming?
    
    # Summary
    summary: str = ""           # One-line overall read
    
    # Meta
    raw_response: str = ""
    processing_time_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/DB storage"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "price_action": self.price_action,
            "key_levels": self.key_levels,
            "momentum": self.momentum,
            "volume_story": self.volume_story,
            "structure": self.structure,
            "summary": self.summary,
            "raw_response": self.raw_response,
            "processing_time_ms": self.processing_time_ms
        }


# ═══════════════════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════════════════

SENTIMENT_ANALYSIS_PROMPT = """You are a professional trader analyzing a {timeframe} chart for {symbol}.

Describe what you see across these five categories. Write like a trader talking to another trader - be specific about prices, levels, and what the chart is telling you.

For each category, provide BOTH a text description AND a numeric score from -1.0 (extremely bearish) to +1.0 (extremely bullish).

Score guide:
- -1.0 to -0.6: Strongly bearish signal
- -0.6 to -0.2: Moderately bearish
- -0.2 to +0.2: Neutral/mixed
- +0.2 to +0.6: Moderately bullish
- +0.6 to +1.0: Strongly bullish signal

## 1. PRICE ACTION
What is price doing right now? Is it testing a level, trending, consolidating, breaking out, rejecting? Describe the recent candles and immediate price behavior.

## 2. KEY LEVELS  
What's above and below? Identify visible support/resistance, where EMAs are, Bollinger band positions, any obvious horizontal levels. Be specific with price numbers if visible.

## 3. MOMENTUM
Is the move strengthening or weakening? Look at candle sizes, are they getting bigger or smaller? Is there acceleration or deceleration? Any divergences forming?

## 4. VOLUME STORY
What's participation telling us? Is volume confirming the move, diverging from it, climactic, or drying up? Compare recent bars to the average.

## 5. STRUCTURE
What pattern or regime is forming? Range-bound, trending, compression before breakout, distribution, accumulation? What's the bigger picture setup?

Respond ONLY with valid JSON in this exact format:
{{
    "price_action": "2-3 sentences describing current price behavior",
    "price_action_score": 0.0,
    "key_levels": "2-3 sentences about support/resistance/indicators",
    "key_levels_score": 0.0,
    "momentum": "2-3 sentences about strength/weakness of move",
    "momentum_score": 0.0,
    "volume_story": "2-3 sentences about what volume is saying",
    "volume_score": 0.0,
    "structure": "2-3 sentences about the pattern/regime",
    "structure_score": 0.0,
    "summary": "One sentence overall read - what's the trade here?",
    "composite_score": 0.0
}}

The composite_score should be your overall bias considering all factors, weighted by importance.

Be specific. Use numbers when visible. Scores must be between -1.0 and 1.0."""


# ═══════════════════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════════════════

class SentimentDatabase:
    """SQLite storage for sentiment readings"""
    
    def __init__(self, db_path: str = "sentiment_analysis.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_readings_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                
                -- Five narrative categories (text)
                price_action TEXT,
                key_levels TEXT,
                momentum TEXT,
                volume_story TEXT,
                structure TEXT,
                
                -- Summary
                summary TEXT,
                
                -- Meta
                raw_response TEXT,
                processing_time_ms INTEGER,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Index for fast lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_v2_symbol_tf_ts 
            ON sentiment_readings_v2(symbol, timeframe, timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, reading: SentimentReading) -> int:
        """Save a sentiment reading, return the ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sentiment_readings_v2 (
                timestamp, symbol, timeframe,
                price_action, key_levels, momentum, volume_story, structure,
                summary, raw_response, processing_time_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            reading.timestamp,
            reading.symbol,
            reading.timeframe,
            reading.price_action,
            reading.key_levels,
            reading.momentum,
            reading.volume_story,
            reading.structure,
            reading.summary,
            reading.raw_response,
            reading.processing_time_ms
        ))
        
        reading_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return reading_id
    
    def get_latest(self, symbol: str, timeframe: str) -> Optional[SentimentReading]:
        """Get the most recent sentiment reading for a symbol/timeframe"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM sentiment_readings_v2 
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (symbol, timeframe))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_reading(row)
    
    def get_history(self, symbol: str, timeframe: str, 
                    limit: int = 100, 
                    from_ts: Optional[str] = None,
                    to_ts: Optional[str] = None) -> list:
        """Get historical sentiment readings"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM sentiment_readings_v2 WHERE symbol = ? AND timeframe = ?"
        params = [symbol, timeframe]
        
        if from_ts:
            query += " AND timestamp >= ?"
            params.append(from_ts)
        if to_ts:
            query += " AND timestamp <= ?"
            params.append(to_ts)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_reading(row) for row in rows]
    
    def _row_to_reading(self, row) -> SentimentReading:
        """Convert a database row to a SentimentReading"""
        return SentimentReading(
            id=row["id"],
            timestamp=row["timestamp"],
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            price_action=row["price_action"] or "",
            key_levels=row["key_levels"] or "",
            momentum=row["momentum"] or "",
            volume_story=row["volume_story"] or "",
            structure=row["structure"] or "",
            summary=row["summary"] or "",
            raw_response=row["raw_response"] or "",
            processing_time_ms=row["processing_time_ms"] or 0
        )


# ═══════════════════════════════════════════════════════════════════════════
# SCREENSHOT CAPTURE
# ═══════════════════════════════════════════════════════════════════════════

class ChartCapture:
    """Captures chart screenshots for analysis"""
    
    def __init__(self, region: Optional[tuple] = None):
        """
        Args:
            region: (x, y, width, height) or None for full screen
        """
        self.region = region
    
    def capture(self) -> Optional[str]:
        """
        Capture screenshot and return as base64 string
        Returns None if capture fails
        """
        if not HAS_MSS:
            logging.warning("mss not installed, cannot capture screenshot")
            return None
        
        try:
            with mss.mss() as sct:
                if self.region:
                    monitor = {
                        "left": self.region[0],
                        "top": self.region[1],
                        "width": self.region[2],
                        "height": self.region[3]
                    }
                else:
                    # Full primary monitor
                    monitor = sct.monitors[1]
                
                screenshot = sct.grab(monitor)
                
                # Convert to PNG bytes
                png_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)
                
                # Encode to base64
                return base64.standard_b64encode(png_bytes).decode("utf-8")
                
        except Exception as e:
            logging.error(f"Screenshot capture failed: {e}")
            return None
    
    def capture_to_file(self, filepath: str) -> bool:
        """Capture and save to file"""
        if not HAS_MSS:
            return False
        
        try:
            with mss.mss() as sct:
                if self.region:
                    monitor = {
                        "left": self.region[0],
                        "top": self.region[1],
                        "width": self.region[2],
                        "height": self.region[3]
                    }
                else:
                    monitor = sct.monitors[1]
                
                sct.shot(mon=monitor, output=filepath)
                return True
        except Exception as e:
            logging.error(f"Screenshot save failed: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════
# SENTIMENT ANALYZER
# ═══════════════════════════════════════════════════════════════════════════

class SentimentAnalyzer:
    """Core sentiment analysis using Claude Vision API"""
    
    def __init__(self, config: SentimentConfig):
        self.config = config
        self.client = None
        
        if HAS_ANTHROPIC and config.api_key:
            self.client = anthropic.Anthropic(api_key=config.api_key)
    
    def analyze(self, image_base64: str, symbol: str, timeframe: str) -> SentimentReading:
        """
        Analyze a chart image and return structured sentiment
        
        Args:
            image_base64: Base64 encoded PNG image
            symbol: Trading symbol (e.g., "XAUJ26")
            timeframe: "15m" or "1m"
        
        Returns:
            SentimentReading with all categories populated
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        reading = SentimentReading(
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe
        )
        
        if not self.client:
            # Mock mode - return sample narrative
            logging.warning("No API client, returning mock sentiment")
            return self._mock_reading(reading, start_time)
        
        try:
            prompt = SENTIMENT_ANALYSIS_PROMPT.format(
                timeframe=timeframe,
                symbol=symbol
            )
            
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=self.config.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            # Extract JSON from response
            raw_text = response.content[0].text
            reading.raw_response = raw_text
            
            # Parse JSON
            parsed = self._parse_response(raw_text)
            
            if parsed:
                reading.price_action = parsed.get("price_action", "")
                reading.key_levels = parsed.get("key_levels", "")
                reading.momentum = parsed.get("momentum", "")
                reading.volume_story = parsed.get("volume_story", "")
                reading.structure = parsed.get("structure", "")
                reading.summary = parsed.get("summary", "")
            
        except Exception as e:
            logging.error(f"Sentiment analysis failed: {e}")
            reading.raw_response = f"ERROR: {str(e)}"
        
        reading.processing_time_ms = int((time.time() - start_time) * 1000)
        return reading
    
    def _parse_response(self, text: str) -> Optional[dict]:
        """Extract and parse JSON from response text"""
        import re
        
        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logging.warning(f"Could not parse JSON from response: {text[:200]}...")
        return None
    
    def _mock_reading(self, reading: SentimentReading, start_time: float) -> SentimentReading:
        """Generate mock sentiment for testing without API"""
        reading.price_action = "Price testing upper resistance around 2785, showing hesitation with smaller bodied candles. Recent push was impulsive but now stalling at this level."
        reading.key_levels = "EMA 21 providing support at 2770, upper Bollinger band at 2788. Key horizontal resistance at 2785-2790 zone, support below at 2765."
        reading.momentum = "Candles getting smaller on the push up, suggesting momentum fading. Earlier acceleration has stalled - watching for continuation or rejection."
        reading.volume_story = "Volume declined on the last few bars despite price pushing higher. This divergence suggests the move may lack conviction to break through."
        reading.structure = "Range forming between 2765-2790 after the earlier impulse. Compression building - expect expansion soon, direction depends on which level breaks first."
        reading.summary = "Bullish structure but momentum fading at resistance. Watch for volume confirmation above 2790 or rejection back to 2770 support."
        reading.raw_response = "MOCK_MODE"
        reading.processing_time_ms = int((time.time() - start_time) * 1000)
        
        return reading


# ═══════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════

class SentimentScheduler:
    """Runs sentiment analysis on schedule"""
    
    def __init__(self, config: SentimentConfig, symbols: list):
        self.config = config
        self.symbols = symbols
        self.db = SentimentDatabase(config.db_path)
        self.analyzer = SentimentAnalyzer(config)
        self.capture = ChartCapture(config.screenshot_region)
        
        # Instance database for Phase 3
        self.instance_db = get_instance_db() if HAS_INSTANCE_DB else None
        
        self._running = False
        self._thread = None
        self._last_15m_run = {}
        self._last_1h_run = {}  # SEED 13: Changed from 1m to 1h
        
        # Callbacks for UI updates
        self.on_new_sentiment = None  # Called with (SentimentReading)
    
    def start(self):
        """Start the scheduler in background thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logging.info("Sentiment scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logging.info("Sentiment scheduler stopped")
    
    def _run_loop(self):
        """
        Main scheduler loop.
        SEED 13: Migrated from 1m to 1h timeframe.
        - 15m analysis: X:01, X:16, X:31, X:46
        - 1h analysis: X:02 (2 minutes after hour to catch closed bar)
        """
        while self._running:
            now = datetime.utcnow()
            minute = now.minute
            
            # Check 15m schedule (X:01, X:16, X:31, X:46)
            if minute in self.config.tf_15m_offsets:
                for symbol in self.symbols:
                    key = f"{symbol}_15m"
                    if key not in self._last_15m_run or \
                       (now - self._last_15m_run[key]).seconds >= 60:
                        self._run_analysis(symbol, "15m")
                        self._last_15m_run[key] = now
            
            # Check 1h schedule (X:02 - 2 minutes after hour)
            if minute in self.config.tf_1h_offsets:
                for symbol in self.symbols:
                    key = f"{symbol}_1h"
                    if key not in self._last_1h_run or \
                       (now - self._last_1h_run[key]).seconds >= 60:
                        self._run_analysis(symbol, "1h")
                        self._last_1h_run[key] = now
            
            # Sleep until next minute
            sleep_seconds = 60 - datetime.utcnow().second
            time.sleep(min(sleep_seconds, 5))  # Check at least every 5 seconds
    
    def _run_analysis(self, symbol: str, timeframe: str):
        """Run a single sentiment analysis"""
        logging.info(f"Running {timeframe} sentiment analysis for {symbol}")
        
        # Capture screenshot
        image_b64 = self.capture.capture()
        
        if not image_b64:
            logging.warning(f"No screenshot available for {symbol} {timeframe}")
            return
        
        # Analyze
        reading = self.analyzer.analyze(image_b64, symbol, timeframe)
        
        # Save to global database
        reading_id = self.db.save(reading)
        reading.id = reading_id
        
        logging.info(
            f"Sentiment saved: {symbol} {timeframe} - {reading.summary[:50]}..."
        )
        
        # Phase 3: Save to instance tables
        self._save_to_instance_tables(symbol, timeframe, reading)
        
        # Notify listeners
        if self.on_new_sentiment:
            self.on_new_sentiment(reading)
    
    def _save_to_instance_tables(self, symbol: str, timeframe: str, reading: SentimentReading):
        """
        Phase 3: Save sentiment to all active instances for this symbol.
        This triggers state detection and Markov matrix updates automatically.
        """
        if not self.instance_db:
            return
        
        try:
            # Get all active instances for this symbol
            instances = self.instance_db.get_instances_by_symbol(symbol)
            active_instances = instances.get("active", [])
            
            if not active_instances:
                logging.debug(f"No active instances for {symbol}")
                return
            
            # Map SentimentReading to instance database format
            # The instance db expects scores, but we have narratives
            # For now, we'll store the text and set scores to 0
            # A future enhancement can add score extraction from narratives
            sentiment_data = {
                "profile_id": None,
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": reading.timestamp,
                
                # Text narratives
                "price_action_text": reading.price_action,
                "price_action_score": 0.0,
                "key_levels_text": reading.key_levels,
                "key_levels_score": 0.0,
                "momentum_text": reading.momentum,
                "momentum_score": 0.0,
                "volume_text": reading.volume_story,
                "volume_score": 0.0,
                "structure_text": reading.structure,
                "structure_score": 0.0,
                
                # Summary and composite
                "summary": reading.summary,
                "composite_score": 0.0,  # Will be calculated from scores later
                
                # Source info
                "source_model": self.config.model,
                "source_type": "API" if reading.raw_response != "MOCK_MODE" else "MOCK",
                "raw_response": reading.raw_response,
                "processing_time_ms": reading.processing_time_ms,
                "tokens_used": 0
            }
            
            # Save to each active instance
            for instance in active_instances:
                try:
                    self.instance_db.save_sentiment(instance.id, sentiment_data)
                    logging.info(f"[Phase3] Sentiment saved to instance: {instance.id}")
                except Exception as e:
                    logging.error(f"[Phase3] Failed to save to instance {instance.id}: {e}")
        
        except Exception as e:
            logging.error(f"[Phase3] Instance table save failed: {e}")
    
    def run_now(self, symbol: str, timeframe: str) -> SentimentReading:
        """Run analysis immediately (for manual triggers)"""
        image_b64 = self.capture.capture()
        
        if not image_b64:
            # Return empty reading
            return SentimentReading(
                timestamp=datetime.utcnow().isoformat() + "Z",
                symbol=symbol,
                timeframe=timeframe,
                raw_response="ERROR: Screenshot capture failed"
            )
        
        reading = self.analyzer.analyze(image_b64, symbol, timeframe)
        reading.id = self.db.save(reading)
        
        # Phase 3: Save to instance tables
        self._save_to_instance_tables(symbol, timeframe, reading)
        
        if self.on_new_sentiment:
            self.on_new_sentiment(reading)
        
        return reading


# ═══════════════════════════════════════════════════════════════════════════
# FLASK API INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════

def register_sentiment_routes(app, scheduler: SentimentScheduler):
    """Register Flask routes for sentiment API"""
    from flask import jsonify, request
    
    @app.route('/api/sentiment/latest', methods=['GET'])
    def get_latest_sentiment():
        symbol = request.args.get('symbol', 'XAUJ26')
        timeframe = request.args.get('timeframe', '15m')
        
        reading = scheduler.db.get_latest(symbol, timeframe)
        
        if not reading:
            return jsonify({"success": False, "error": "No sentiment data found"})
        
        return jsonify({
            "success": True,
            "data": reading.to_dict()
        })
    
    @app.route('/api/sentiment/history', methods=['GET'])
    def get_sentiment_history():
        symbol = request.args.get('symbol', 'XAUJ26')
        timeframe = request.args.get('timeframe', '15m')
        limit = int(request.args.get('limit', 100))
        from_ts = request.args.get('from')
        to_ts = request.args.get('to')
        
        readings = scheduler.db.get_history(symbol, timeframe, limit, from_ts, to_ts)
        
        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in readings],
            "count": len(readings)
        })
    
    @app.route('/api/sentiment/analyze', methods=['POST'])
    def trigger_analysis():
        """Manually trigger sentiment analysis"""
        data = request.get_json() or {}
        symbol = data.get('symbol', 'XAUJ26')
        timeframe = data.get('timeframe', '15m')
        
        reading = scheduler.run_now(symbol, timeframe)
        
        return jsonify({
            "success": True,
            "data": reading.to_dict()
        })
    
    @app.route('/api/sentiment/status', methods=['GET'])
    def get_scheduler_status():
        """Get scheduler status. SEED 13: Shows 15m and 1h offsets."""
        return jsonify({
            "success": True,
            "running": scheduler._running,
            "symbols": scheduler.symbols,
            "config": {
                "tf_15m_offsets": scheduler.config.tf_15m_offsets,
                "tf_1h_offsets": scheduler.config.tf_1h_offsets,
                "display_duration": scheduler.config.display_duration_seconds
            }
        })


# ═══════════════════════════════════════════════════════════════════════════
# MAIN / CLI
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="APEX Sentiment Engine")
    parser.add_argument('--symbols', nargs='+', default=['XAUJ26'], 
                        help='Symbols to analyze')
    parser.add_argument('--api-key', default=os.getenv('ANTHROPIC_API_KEY'),
                        help='Anthropic API key')
    parser.add_argument('--db', default='sentiment_analysis.db',
                        help='Database path')
    parser.add_argument('--test', action='store_true',
                        help='Run single test analysis')
    parser.add_argument('--mock', action='store_true',
                        help='Use mock mode (no API calls)')
    
    args = parser.parse_args()
    
    config = SentimentConfig(
        api_key="" if args.mock else (args.api_key or ""),
        db_path=args.db
    )
    
    if args.test:
        # Single test run
        print(f"Running test analysis for {args.symbols}...")
        analyzer = SentimentAnalyzer(config)
        capture = ChartCapture()
        db = SentimentDatabase(config.db_path)
        
        image = capture.capture()
        if image:
            for symbol in args.symbols:
                reading = analyzer.analyze(image, symbol, "15m")
                db.save(reading)
                print(f"\n{'='*60}")
                print(f"{symbol} 15m Sentiment")
                print(f"{'='*60}")
                print(f"\nPRICE ACTION:\n{reading.price_action}")
                print(f"\nKEY LEVELS:\n{reading.key_levels}")
                print(f"\nMOMENTUM:\n{reading.momentum}")
                print(f"\nVOLUME STORY:\n{reading.volume_story}")
                print(f"\nSTRUCTURE:\n{reading.structure}")
                print(f"\nSUMMARY:\n{reading.summary}")
                print(f"\n[Processing time: {reading.processing_time_ms}ms]")
        else:
            print("Screenshot capture failed")
    else:
        # Run scheduler
        print(f"Starting sentiment scheduler for {args.symbols}")
        scheduler = SentimentScheduler(config, args.symbols)
        scheduler.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            scheduler.stop()
