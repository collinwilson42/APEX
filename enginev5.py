"""
MT5 META AGENT V4 - SMART TOKEN OPTIMIZATION ENGINE
15m Full Analysis (any Δ) + 1m Lightweight Updates (±1 only)
~85% cost reduction vs V3
"""

import time
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import anthropic
import base64

# Import configuration
import config

# Import modules
from mt5_position_tracker import get_position_tracker

# Import database functions
from database_init_base44_unified import (
    insert_position_state_row,
    get_latest_position_state,
    get_execution_gate_config,
    get_trade_statistics,
    DB_PATH
)


# ============================================================================
# ANALYSIS SNAPSHOT STORAGE
# ============================================================================

class AnalysisSnapshot:
    """Stores Claude's 15m analysis for use in 1m updates"""
    def __init__(self):
        self.timestamp = None
        self.reasoning = ""
        self.market_bias = "NEUTRAL"
        self.key_support = 0.0
        self.key_resistance = 0.0
        self.confidence = 50
        self.target_position = 0.0
        
    def save(self, data: Dict[str, Any]):
        """Save 15m analysis snapshot"""
        self.timestamp = datetime.now()
        self.reasoning = data.get('reasoning', '')
        self.market_bias = data.get('market_bias', 'NEUTRAL')
        self.key_support = data.get('key_support', 0.0)
        self.key_resistance = data.get('key_resistance', 0.0)
        self.confidence = data.get('confidence', 50)
        self.target_position = data.get('target_position', 0.0)
        
    def is_fresh(self, max_age_minutes: int = 15) -> bool:
        """Check if snapshot is still fresh"""
        if self.timestamp is None:
            return False
        age = (datetime.now() - self.timestamp).total_seconds() / 60
        return age < max_age_minutes
    
    def get_age_minutes(self) -> float:
        """Get age of snapshot in minutes"""
        if self.timestamp is None:
            return 999.0
        return (datetime.now() - self.timestamp).total_seconds() / 60
    
    def get_summary(self) -> str:
        """Get summary for lightweight updates"""
        if not self.timestamp:
            return "No previous analysis available."
        
        age_min = int(self.get_age_minutes())
        
        return f"""PREVIOUS 15M ANALYSIS ({age_min} min ago):
Market Bias: {self.market_bias}
Target Position: {self.target_position:+.1f} lots
Key Support: ${self.key_support:.2f}
Key Resistance: ${self.key_resistance:.2f}
Confidence: {self.confidence}%
Reasoning: {self.reasoning}"""


# ============================================================================
# V4 API DECISION ENGINE
# ============================================================================

class APIDecisionEngineV4:
    """
    Two-tier API system:
    - Full Analysis (15m): Screenshot + data → Any Δ
    - Lightweight Update (1m): Data only → ±1 only
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("API key required")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.full_analyses = 0
        self.lightweight_updates = 0
        
    def full_analysis(
        self,
        screenshot_path: str,
        trade_score: float,
        current_position: float,
        current_sl: Optional[float],
        current_tp: Optional[float],
        current_price: float,
        risk_reward_level: int,
        chart_data_15m: Dict[str, Any],
        chart_data_1m: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        FULL 15M ANALYSIS - Can return ANY delta
        Uses screenshot + full context
        """
        try:
            # Read screenshot
            with open(screenshot_path, 'rb') as f:
                screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Build context
            context = self._build_full_context(
                trade_score, current_position, current_sl, current_tp,
                current_price, risk_reward_level, chart_data_15m,
                chart_data_1m, account_info
            )
            
            # Build prompt
            prompt = f"""{context}

FULL 15-MINUTE ANALYSIS

Analyze the chart screenshot and all data. Make a strategic position decision:

Δ = ANY NUMBER (e.g., -5, -2, 0, +3, +7, +10, etc.)
- Negative = Reduce position by that many lots
- Zero = Hold current position
- Positive = Increase position by that many lots

CONSTRAINTS:
- Max total position: {config.MAX_TOTAL_POSITION} lots
- Current position: {current_position:+.1f} lots
- Risk/Reward Level: {risk_reward_level} (higher = more aggressive)

RESPOND IN THIS EXACT FORMAT:
DECISION: [any integer, e.g., +5, -3, 0]
MARKET_BIAS: [BULLISH, BEARISH, or NEUTRAL]
TARGET_POSITION: [desired total position size in lots]
KEY_SUPPORT: [price level]
KEY_RESISTANCE: [price level]
CONFIDENCE: [0-100]
REASONING: [2-3 sentences explaining the strategic plan]
NEW_SL: [price or NONE]
NEW_TP: [price or NONE]

This analysis will guide the next 15 minutes of lightweight updates.
"""
            
            # Call API
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            
            # Parse response
            response_text = message.content[0].text
            result = self._parse_full_analysis(response_text)
            
            self.full_analyses += 1
            
            print(f"\n{'='*70}")
            print(f"FULL 15M ANALYSIS #{self.full_analyses}")
            print(f"{'='*70}")
            print(f"Decision: {result['decision']:+d} lots")
            print(f"Market Bias: {result['market_bias']}")
            print(f"Target Position: {result['target_position']:+.1f} lots")
            print(f"Key Support: ${result['key_support']:.2f}")
            print(f"Key Resistance: ${result['key_resistance']:.2f}")
            print(f"Confidence: {result['confidence']}%")
            print(f"Reasoning: {result['reasoning']}")
            if result['new_sl']:
                print(f"New SL: ${result['new_sl']:.2f}")
            if result['new_tp']:
                print(f"New TP: ${result['new_tp']:.2f}")
            print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            print(f"✗ Full analysis error: {e}")
            import traceback
            traceback.print_exc()
            return self._safe_default()
    
    def lightweight_update(
        self,
        snapshot: AnalysisSnapshot,
        trade_score: float,
        current_position: float,
        current_price: float,
        chart_data_15m: Dict[str, Any],
        chart_data_1m: Dict[str, Any],
        account_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        LIGHTWEIGHT 1M UPDATE - Limited to ±1
        Uses previous analysis + current data (NO screenshot)
        """
        try:
            # Build lightweight context
            context = f"""LIGHTWEIGHT UPDATE - 1 MINUTE CHECK

{snapshot.get_summary()}

CURRENT STATUS:
- Current Position: {current_position:+.1f} lots
- Current Price: ${current_price:.2f}
- Trade Score: {trade_score:.1f}/100
- Current P&L: ${account_info.get('profit', 0):.2f}

RECENT DATA:
- 15m Supertrend: {chart_data_15m.get('supertrend', 'N/A')}
- 15m ATR: {chart_data_15m.get('atr_14', 0):.2f}
- 1m Supertrend: {chart_data_1m.get('supertrend', 'N/A')}
- 1m Recent Close: ${chart_data_1m.get('price_close', 0):.2f}

TASK: Make a small adjustment based on the 15m plan and current data.

DECISION OPTIONS (±1 ONLY):
Δ = -1  (Reduce by 1 lot - defensive)
Δ = 0   (Hold current position)
Δ = +1  (Add 1 lot - following plan)

RESPOND IN THIS FORMAT:
DECISION: [-1, 0, or +1]
CONFIDENCE: [0-100]
REASONING: [One sentence explaining why]
NEW_SL: [price or NONE]
NEW_TP: [price or NONE]
"""
            
            # Call API (text only, no image)
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": context
                }]
            )
            
            # Parse response
            response_text = message.content[0].text
            result = self._parse_lightweight_update(response_text)
            
            self.lightweight_updates += 1
            
            print(f"\n[Lightweight Update #{self.lightweight_updates}]")
            print(f"Decision: {result['decision']:+d} | Confidence: {result['confidence']}%")
            print(f"Reasoning: {result['reasoning']}")
            
            return result
            
        except Exception as e:
            print(f"✗ Lightweight update error: {e}")
            return self._safe_default()
    
    def _build_full_context(
        self, trade_score, current_position, current_sl, current_tp,
        current_price, risk_reward_level, chart_data_15m, chart_data_1m, account_info
    ) -> str:
        """Build full context for 15m analysis"""
        
        position_str = f"+{current_position:.1f} lots (LONG)" if current_position > 0.1 else \
                       f"{current_position:.1f} lots (SHORT)" if current_position < -0.1 else "FLAT"
        
        sl_str = f"${current_sl:.2f}" if current_sl and current_sl > 0 else "Not set"
        tp_str = f"${current_tp:.2f}" if current_tp and current_tp > 0 else "Not set"
        
        risk_desc = "AGGRESSIVE" if risk_reward_level >= 80 else \
                    "MODERATE-HIGH" if risk_reward_level >= 60 else \
                    "BALANCED" if risk_reward_level >= 40 else \
                    "CONSERVATIVE" if risk_reward_level >= 20 else "VERY CONSERVATIVE"
        
        return f"""MARKET SNAPSHOT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CURRENT POSITION:
- Size: {position_str}
- SL: {sl_str}
- TP: {tp_str}
- P&L: ${account_info.get('profit', 0):.2f}

TRADE SCORE: {trade_score:.1f}/100
RISK/REWARD LEVEL: {risk_reward_level} ({risk_desc})
CURRENT PRICE: ${current_price:.2f}

15M CHART DATA:
- Supertrend: {chart_data_15m.get('supertrend', 'N/A')}
- ATR: {chart_data_15m.get('atr_14', 0):.2f}
- ATR Ratio: {chart_data_15m.get('atr_ratio', 0):.2f}
- EMA Distance: {chart_data_15m.get('ema_distance', 0):.2f}
- Fib Zone: {chart_data_15m.get('current_fib_zone', 'N/A')}

1M CHART DATA:
- Supertrend: {chart_data_1m.get('supertrend', 'N/A')}
- ATR: {chart_data_1m.get('atr_14', 0):.2f}
- Recent Close: ${chart_data_1m.get('price_close', 0):.2f}

ACCOUNT:
- Balance: ${account_info.get('balance', 0):.2f}
- Equity: ${account_info.get('equity', 0):.2f}
- Margin Level: {account_info.get('margin_level', 0):.1f}%
"""
    
    def _parse_full_analysis(self, response: str) -> Dict[str, Any]:
        """Parse full analysis response"""
        lines = response.strip().split('\n')
        
        result = {
            'decision': 0,
            'market_bias': 'NEUTRAL',
            'target_position': 0.0,
            'key_support': 0.0,
            'key_resistance': 0.0,
            'confidence': 50,
            'reasoning': 'Analysis incomplete',
            'new_sl': None,
            'new_tp': None
        }
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('DECISION:'):
                dec_str = line.split(':', 1)[1].strip()
                try:
                    result['decision'] = int(dec_str.replace('+', '').replace(' lots', ''))
                except:
                    result['decision'] = 0
            
            elif line.startswith('MARKET_BIAS:'):
                result['market_bias'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('TARGET_POSITION:'):
                try:
                    result['target_position'] = float(line.split(':', 1)[1].strip().replace(' lots', '').replace('+', ''))
                except:
                    result['target_position'] = 0.0
            
            elif line.startswith('KEY_SUPPORT:'):
                try:
                    result['key_support'] = float(line.split(':', 1)[1].strip().replace('$', '').replace(',', ''))
                except:
                    result['key_support'] = 0.0
            
            elif line.startswith('KEY_RESISTANCE:'):
                try:
                    result['key_resistance'] = float(line.split(':', 1)[1].strip().replace('$', '').replace(',', ''))
                except:
                    result['key_resistance'] = 0.0
            
            elif line.startswith('CONFIDENCE:'):
                try:
                    result['confidence'] = int(line.split(':', 1)[1].strip().replace('%', ''))
                except:
                    result['confidence'] = 50
            
            elif line.startswith('REASONING:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('NEW_SL:'):
                sl_str = line.split(':', 1)[1].strip()
                if 'NONE' not in sl_str.upper():
                    try:
                        result['new_sl'] = float(sl_str.replace('$', '').replace(',', ''))
                    except:
                        pass
            
            elif line.startswith('NEW_TP:'):
                tp_str = line.split(':', 1)[1].strip()
                if 'NONE' not in tp_str.upper():
                    try:
                        result['new_tp'] = float(tp_str.replace('$', '').replace(',', ''))
                    except:
                        pass
        
        return result
    
    def _parse_lightweight_update(self, response: str) -> Dict[str, Any]:
        """Parse lightweight update response"""
        lines = response.strip().split('\n')
        
        result = {
            'decision': 0,
            'confidence': 50,
            'reasoning': 'Update incomplete',
            'new_sl': None,
            'new_tp': None
        }
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('DECISION:'):
                dec_str = line.split(':', 1)[1].strip()
                try:
                    result['decision'] = int(dec_str.replace('+', ''))
                    # Enforce ±1 limit
                    result['decision'] = max(-1, min(1, result['decision']))
                except:
                    result['decision'] = 0
            
            elif line.startswith('CONFIDENCE:'):
                try:
                    result['confidence'] = int(line.split(':', 1)[1].strip().replace('%', ''))
                except:
                    result['confidence'] = 50
            
            elif line.startswith('REASONING:'):
                result['reasoning'] = line.split(':', 1)[1].strip()
            
            elif line.startswith('NEW_SL:'):
                sl_str = line.split(':', 1)[1].strip()
                if 'NONE' not in sl_str.upper():
                    try:
                        result['new_sl'] = float(sl_str.replace('$', '').replace(',', ''))
                    except:
                        pass
            
            elif line.startswith('NEW_TP:'):
                tp_str = line.split(':', 1)[1].strip()
                if 'NONE' not in tp_str.upper():
                    try:
                        result['new_tp'] = float(tp_str.replace('$', '').replace(',', ''))
                    except:
                        pass
        
        return result
    
    def _safe_default(self) -> Dict[str, Any]:
        """Return safe default decision"""
        return {
            'decision': 0,
            'confidence': 0,
            'reasoning': 'Error occurred - holding position',
            'new_sl': None,
            'new_tp': None
        }


# ============================================================================
# V4 WEBHOOK WRITER
# ============================================================================

class WebhookWriterV4:
    """Writes webhook signals with clean tp/sl format"""
    
    def __init__(self, file_path: str = "webhook_signals.txt"):
        self.file_path = file_path
        self.signals_sent = 0
        
    def send_trade(self, action: str, symbol: str, qty: float, tp: float, sl: float) -> bool:
        """Send BUY or SELL signal"""
        signal = {
            "action": action,
            "symbol": symbol,
            "qty": qty,
            "tp": tp,
            "sl": sl
        }
        return self._write_signal(signal)
    
    def send_close(self, symbol: str) -> bool:
        """Send CLOSE signal"""
        signal = {
            "action": "CLOSE",
            "symbol": symbol
        }
        return self._write_signal(signal)
    
    def _write_signal(self, signal: Dict[str, Any]) -> bool:
        """Write signal to webhook file"""
        try:
            json_str = json.dumps(signal, separators=(',', ':'))
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(json_str)
            
            self.signals_sent += 1
            
            print(f"✓ Webhook signal sent #{self.signals_sent}")
            print(f"  {json_str}")
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to write webhook signal: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get webhook writer statistics"""
        return {
            'signals_sent': self.signals_sent,
            'file_path': self.file_path,
            'file_exists': os.path.exists(self.file_path)
        }


# ============================================================================
# GLOBAL STATE
# ============================================================================

class EngineState:
    """Global engine state"""
    def __init__(self):
        self.current_score = 50.0
        self.peak_zone = 1
        self.peak_zone_timestamp = None
        self.countdown_sec = 60.0
        self.countdown_remaining_sec = 60.0
        self.last_score_calc = None
        self.last_full_analysis = None
        self.last_lightweight_update = None
        self.last_webhook_trigger = None
        self.cycle_count = 0
        
engine_state = EngineState()
analysis_snapshot = AnalysisSnapshot()


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def get_latest_15m_snapshot() -> Optional[Dict[str, Any]]:
    """Get latest 15m data from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                c.id,
                c.timestamp,
                c.close as price_close,
                b.atr_14,
                b.atr_ratio,
                b.ema_distance,
                b.supertrend,
                f.current_fib_zone,
                f.zone_multiplier,
                a.ath_distance_pct,
                a.ath_multiplier
            FROM core_15m c
            LEFT JOIN basic_15m b ON c.timestamp = b.timestamp AND c.timeframe = b.timeframe
            LEFT JOIN fibonacci_data f ON c.timestamp = f.timestamp AND c.timeframe = f.timeframe
            LEFT JOIN ath_tracking a ON c.timestamp = a.timestamp AND c.timeframe = a.timeframe
            WHERE c.timeframe = '15m' AND c.symbol = ?
            ORDER BY c.timestamp DESC
            LIMIT 1
        """, (config.SYMBOL,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    finally:
        cursor.close()
        conn.close()


def get_latest_1m_snapshot() -> Optional[Dict[str, Any]]:
    """Get latest 1m data from database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                c.timestamp,
                c.close as price_close,
                b.atr_14,
                b.supertrend
            FROM core_15m c
            LEFT JOIN basic_15m b ON c.timestamp = b.timestamp AND c.timeframe = b.timeframe
            WHERE c.timeframe = '1m' AND c.symbol = ?
            ORDER BY c.timestamp DESC
            LIMIT 1
        """, (config.SYMBOL,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
        
    finally:
        cursor.close()
        conn.close()


def calculate_trade_score(snapshot: Dict[str, Any]) -> float:
    """Calculate trade score (0-100) based on indicators"""
    score = 50.0
    
    atr_ratio = snapshot.get('atr_ratio', 1.0)
    if atr_ratio > 1.2:
        score += 20
    elif atr_ratio > 1.0:
        score += 10
    elif atr_ratio < 0.8:
        score -= 10
    
    supertrend = snapshot.get('supertrend', 'NEUTRAL')
    ema_distance = snapshot.get('ema_distance', 0)
    
    if supertrend == 'BULL':
        score += 15
        if ema_distance > 0:
            score += 15
    elif supertrend == 'BEAR':
        score += 15
        if ema_distance < 0:
            score += 15
    
    fib_zone = snapshot.get('current_fib_zone', 7)
    zone_multiplier = snapshot.get('zone_multiplier', 1.0)
    
    if 4 <= fib_zone <= 7:
        score += 15
    
    score += min(10, zone_multiplier * 5)
    
    ath_distance = snapshot.get('ath_distance_pct', 0)
    ath_multiplier = snapshot.get('ath_multiplier', 1.0)
    
    if ath_distance < 0.5:
        score += 20
    elif ath_distance < 1.0:
        score += 15
    elif ath_distance < 2.0:
        score += 10
    
    score += min(5, ath_multiplier * 2.5)
    
    return max(0, min(100, score))


def execute_decision(
    decision: Dict[str, Any],
    tracker: Any,
    writer: WebhookWriterV4,
    snapshot: Dict[str, Any]
) -> bool:
    """Execute API decision via webhook"""
    try:
        delta = decision['decision']
        new_sl = decision.get('new_sl')
        new_tp = decision.get('new_tp')
        
        if delta == 0:
            print("✓ Hold position - no action")
            return True
        
        # Get current position
        total_pos = tracker.get_total_position()
        current_volume = total_pos['total_volume']
        current_price = tracker.get_current_price()
        
        if current_price is None:
            print("✗ Cannot get current price")
            return False
        
        atr = snapshot.get('atr_14', 5.0)
        
        # Execute multiple trades if delta > 1
        abs_delta = abs(delta)
        
        for i in range(abs_delta):
            if delta > 0:
                # Increase position
                if current_volume >= config.MAX_TOTAL_POSITION:
                    print(f"⚠️  Cannot increase: at max position")
                    break
                
                # Determine direction
                if current_volume > 0.1:
                    action = "BUY"
                    tp = new_tp if new_tp else current_price + (atr * 2.0)
                    sl = new_sl if new_sl else current_price - (atr * 1.0)
                elif current_volume < -0.1:
                    action = "SELL"
                    tp = new_tp if new_tp else current_price - (atr * 2.0)
                    sl = new_sl if new_sl else current_price + (atr * 1.0)
                else:
                    # Flat, use market bias from analysis
                    bias = decision.get('market_bias', 'NEUTRAL')
                    if bias == 'BULLISH' or engine_state.current_score > 55:
                        action = "BUY"
                        tp = new_tp if new_tp else current_price + (atr * 2.0)
                        sl = new_sl if new_sl else current_price - (atr * 1.0)
                    else:
                        action = "SELL"
                        tp = new_tp if new_tp else current_price - (atr * 2.0)
                        sl = new_sl if new_sl else current_price + (atr * 1.0)
                
                writer.send_trade(action, config.SYMBOL, config.BASE_LOT_SIZE, tp, sl)
                current_volume += config.BASE_LOT_SIZE if action == "BUY" else -config.BASE_LOT_SIZE
                time.sleep(0.5)  # Small delay between orders
            
            else:
                # Decrease position
                if abs(current_volume) < 0.1:
                    print("⚠️  Cannot decrease: no position")
                    break
                
                writer.send_close(config.SYMBOL)
                break  # Close handles full close
        
        return True
        
    except Exception as e:
        print(f"✗ Error executing decision: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_latest_screenshot(screenshot_folder: str) -> Optional[str]:
    """
    Get the most recent screenshot from the screenshots folder
    
    Args:
        screenshot_folder: Path to screenshots folder
        
    Returns:
        Path to most recent screenshot, or None if no screenshots found
    """
    try:
        if not os.path.exists(screenshot_folder):
            print(f"⚠️  Screenshot folder not found: {screenshot_folder}")
            return None
        
        # Get all image files
        image_extensions = ('.png', '.jpg', '.jpeg', '.bmp')
        screenshots = [
            os.path.join(screenshot_folder, f) 
            for f in os.listdir(screenshot_folder) 
            if f.lower().endswith(image_extensions)
        ]
        
        if not screenshots:
            print(f"⚠️  No screenshots found in: {screenshot_folder}")
            return None
        
        # Get most recent by modification time
        latest = max(screenshots, key=os.path.getmtime)
        
        # Check age
        age_sec = (datetime.now() - datetime.fromtimestamp(os.path.getmtime(latest))).total_seconds()
        
        if config.VERBOSE_LOGGING:
            print(f"📸 Using screenshot: {os.path.basename(latest)} ({age_sec:.0f}s old)")
        
        return latest
        
    except Exception as e:
        print(f"✗ Error finding latest screenshot: {e}")
        return None


def query_api_and_execute(
    api_engine: APIDecisionEngineV4,
    tracker: Any,
    writer: WebhookWriterV4,
    snapshot_15m: Dict[str, Any],
    snapshot_1m: Dict[str, Any],
    force_full: bool = False
) -> bool:
    """Query API and execute decision"""
    
    global analysis_snapshot
    
    try:
        # Get position data
        total_pos = tracker.get_total_position()
        account_info = tracker.get_account_info()
        current_price = tracker.get_current_price()
        
        if current_price is None:
            print("✗ Cannot get current price")
            return False
        
        current_sl = total_pos['sl_prices'][0] if total_pos['sl_prices'] else None
        current_tp = total_pos['tp_prices'][0] if total_pos['tp_prices'] else None
        
        # Determine if full analysis or lightweight update
        need_full_analysis = force_full or \
                           engine_state.last_full_analysis is None or \
                           not analysis_snapshot.is_fresh()
        
        if need_full_analysis:
            # FULL 15M ANALYSIS - Get most recent screenshot
            screenshot_path = get_latest_screenshot(config.SCREENSHOT_FOLDER)
            
            if not screenshot_path:
                print(f"⚠️  No screenshots available in {config.SCREENSHOT_FOLDER}")
                print(f"⚠️  Skipping full analysis, will retry next interval")
                return False
            
            print(f"\n{'='*70}")
            print("FULL 15-MINUTE ANALYSIS (with screenshot)")
            print(f"{'='*70}")
            
            decision = api_engine.full_analysis(
                screenshot_path=screenshot_path,
                trade_score=engine_state.current_score,
                current_position=total_pos['total_volume'],
                current_sl=current_sl,
                current_tp=current_tp,
                current_price=current_price,
                risk_reward_level=config.RISK_REWARD_LEVEL,
                chart_data_15m=snapshot_15m,
                chart_data_1m=snapshot_1m,
                account_info=account_info
            )
            
            # Save analysis snapshot
            analysis_snapshot.save(decision)
            engine_state.last_full_analysis = datetime.now()
            
        else:
            # LIGHTWEIGHT 1M UPDATE
            print(f"\n[Lightweight Update - {analysis_snapshot.get_age_minutes():.1f} min since full analysis]")
            
            decision = api_engine.lightweight_update(
                snapshot=analysis_snapshot,
                trade_score=engine_state.current_score,
                current_position=total_pos['total_volume'],
                current_price=current_price,
                chart_data_15m=snapshot_15m,
                chart_data_1m=snapshot_1m,
                account_info=account_info
            )
            
            engine_state.last_lightweight_update = datetime.now()
        
        # Execute decision
        if decision['decision'] != 0:
            success = execute_decision(decision, tracker, writer, snapshot_15m)
            return success
        else:
            return True
        
    except Exception as e:
        print(f"✗ API query error: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_countdown_state(snapshot: Dict[str, Any], gate_config: Dict[str, Any]):
    """Update countdown state"""
    global engine_state
    
    now = datetime.now()
    
    if (engine_state.last_score_calc is None or 
        (now - engine_state.last_score_calc).total_seconds() >= 60):
        
        engine_state.current_score = calculate_trade_score(snapshot)
        engine_state.last_score_calc = now
        
        if config.VERBOSE_LOGGING:
            print(f"\n[{now.strftime('%H:%M:%S')}] Score: {engine_state.current_score:.1f}/100")
    
    num_gates = gate_config.get('num_gates', 10)
    base_interval = gate_config.get('base_interval_sec', 60)
    peak_duration = gate_config.get('peak_zone_duration_sec', 120)
    
    gate_size = 100.0 / num_gates
    current_gate = int(engine_state.current_score / gate_size) + 1
    current_gate = max(1, min(num_gates, current_gate))
    
    if current_gate > engine_state.peak_zone:
        engine_state.peak_zone = current_gate
        engine_state.peak_zone_timestamp = now
        if config.VERBOSE_LOGGING:
            print(f"  📈 Peak zone: {engine_state.peak_zone}")
    
    effective_gate = engine_state.peak_zone
    if engine_state.peak_zone_timestamp:
        time_in_peak = (now - engine_state.peak_zone_timestamp).total_seconds()
        if time_in_peak > peak_duration:
            effective_gate = current_gate
            engine_state.peak_zone = current_gate
            engine_state.peak_zone_timestamp = now
    
    engine_state.countdown_sec = base_interval / effective_gate
    
    return effective_gate


def run_engine_cycle(
    snapshot_15m: Dict[str, Any],
    snapshot_1m: Dict[str, Any],
    gate_config: Dict[str, Any],
    api_engine: Optional[APIDecisionEngineV4],
    tracker: Any,
    writer: WebhookWriterV4
) -> bool:
    """Single engine cycle"""
    global engine_state
    
    try:
        now = datetime.now()
        engine_state.cycle_count += 1
        
        engine_state.countdown_remaining_sec -= 1.0
        
        update_countdown_state(snapshot_15m, gate_config)
        
        if engine_state.countdown_remaining_sec <= 0:
            print(f"\n{'='*70}")
            print(f"⏰ COUNTDOWN HIT ZERO!")
            print(f"{'='*70}")
            print(f"  Gate: {engine_state.peak_zone} | Score: {engine_state.current_score:.1f}")
            print(f"  Reset to {engine_state.countdown_sec:.1f}s")
            print(f"{'='*70}\n")
            
            # WRITE TO BRIDGE - ALWAYS FIRES
            import json
            signal = {
                "action": "BUY",
                "symbol": config.SYMBOL,
                "qty": config.BASE_LOT_SIZE,
                "comment": f"Gate{engine_state.peak_zone}_Score{int(engine_state.current_score)}"
            }
            
            try:
                with open("bridge.txt", "w") as f:
                    f.write(json.dumps(signal))
                print(f"✓ TRADE EXECUTED → Bridge signal sent")
                print(f"  {json.dumps(signal)}")
            except Exception as e:
                print(f"✗ Bridge write failed: {e}")
            
            engine_state.countdown_remaining_sec = engine_state.countdown_sec
            engine_state.last_webhook_trigger = now
        
        # Check API timing
        if api_engine and config.API_ENABLED:
            # Check if need full analysis (every 15m)
            need_full = engine_state.last_full_analysis is None or \
                       (now - engine_state.last_full_analysis).total_seconds() >= config.API_FULL_ANALYSIS_INTERVAL_SEC
            
            # Check if need lightweight update (every 1m)
            need_lightweight = not need_full and \
                             (engine_state.last_lightweight_update is None or \
                              (now - engine_state.last_lightweight_update).total_seconds() >= config.API_LIGHTWEIGHT_UPDATE_INTERVAL_SEC)
            
            if need_full or need_lightweight:
                query_api_and_execute(api_engine, tracker, writer, snapshot_15m, snapshot_1m, force_full=need_full)
        
        # Show countdown
        if config.SHOW_COUNTDOWN and int(engine_state.countdown_remaining_sec) % 10 == 0:
            age_str = ""
            if analysis_snapshot.timestamp:
                age_str = f" | Last Analysis: {analysis_snapshot.get_age_minutes():.1f}m ago"
            print(f"[{now.strftime('%H:%M:%S')}] Countdown: {engine_state.countdown_remaining_sec:.0f}s | "
                  f"Gate: {engine_state.peak_zone} | Score: {engine_state.current_score:.1f}{age_str}")
        
        return True
        
    except Exception as e:
        print(f"✗ Engine cycle error: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main engine loop"""
    global engine_state
    
    print("="*70)
    print("MT5 META AGENT V4 - TOKEN-OPTIMIZED ENGINE")
    print("15m Full Analysis + 1m Lightweight Updates")
    print("="*70)
    
    # Print config
    if hasattr(config, 'print_config'):
        if not config.print_config():
            return
    else:
        print("\n[CONFIG]")
        print(f"Symbol: {config.SYMBOL}")
        print(f"Risk Level: {config.RISK_REWARD_LEVEL}")
        print(f"API Enabled: {config.API_ENABLED}")
        if config.API_ENABLED:
            print(f"Full Analysis: Every {config.API_FULL_ANALYSIS_INTERVAL_SEC}s (15m)")
            print(f"Lightweight Update: Every {config.API_LIGHTWEIGHT_UPDATE_INTERVAL_SEC}s (1m)")
    
    # Check database
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Database not found: {DB_PATH}")
        return
    
    print("\n✓ Database connected")
    
    # Initialize components
    print("\nInitializing components...")
    
    writer = WebhookWriterV4(config.WEBHOOK_FILE_PATH)
    print("✓ Webhook writer V4 initialized")
    
    tracker = get_position_tracker(config.SYMBOL)
    if not tracker.connect():
        print("✗ Failed to connect to MT5")
        return
    print("✓ MT5 position tracker connected")
    
    # API engine
    api_engine = None
    if config.API_ENABLED:
        try:
            # Pass None to let APIDecisionEngineV4 check environment variable
            api_key = config.ANTHROPIC_API_KEY if config.ANTHROPIC_API_KEY else None
            api_engine = APIDecisionEngineV4(api_key)
            print("✓ Claude API V4 engine initialized")
            print("  - Full analysis (any Δ): Every 15 minutes")
            print("  - Lightweight (±1): Every 1 minute")
        except Exception as e:
            print(f"⚠️  API disabled: {e}")
            if not os.getenv('ANTHROPIC_API_KEY'):
                print(f"⚠️  No API key found in config or environment")
    else:
        print("⚠️  API disabled via config (testing mode)")
    
    # Get initial data
    print("\n✓ Getting initial market data...")
    snapshot_15m = get_latest_15m_snapshot()
    snapshot_1m = get_latest_1m_snapshot()
    
    if not snapshot_15m:
        print("✗ No 15m data available")
        return
    
    print(f"✓ 15m: {snapshot_15m['timestamp']} | ${snapshot_15m['price_close']:.2f}")
    
    # Initialize state
    gate_config = get_execution_gate_config()
    engine_state.current_score = calculate_trade_score(snapshot_15m)
    engine_state.peak_zone = max(1, int(engine_state.current_score / 10) + 1)
    engine_state.peak_zone_timestamp = datetime.now()
    engine_state.countdown_sec = (gate_config['base_interval_sec'] if gate_config else 60) / engine_state.peak_zone
    engine_state.countdown_remaining_sec = engine_state.countdown_sec
    engine_state.last_score_calc = datetime.now()
    
    print(f"\n✓ Initial state:")
    print(f"  Score: {engine_state.current_score:.1f}/100")
    print(f"  Peak Zone: {engine_state.peak_zone}")
    print(f"  Countdown: {engine_state.countdown_sec:.1f}s")
    
    print("\n✓ Starting V4 engine...")
    print("\nPress Ctrl+C to stop\n")
    print("="*70 + "\n")
    
    last_snapshot_update = datetime.now()
    
    try:
        while True:
            # Update snapshots every 60s
            if (datetime.now() - last_snapshot_update).total_seconds() >= 60:
                snapshot_15m = get_latest_15m_snapshot()
                snapshot_1m = get_latest_1m_snapshot()
                last_snapshot_update = datetime.now()
            
            # Run cycle
            run_engine_cycle(
                snapshot_15m=snapshot_15m,
                snapshot_1m=snapshot_1m,
                gate_config=gate_config,
                api_engine=api_engine,
                tracker=tracker,
                writer=writer
            )
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("✓ ENGINE STOPPED")
        print("="*70)
        print(f"Total cycles: {engine_state.cycle_count}")
        print(f"Final score: {engine_state.current_score:.1f}")
        
        if api_engine:
            print(f"\nAPI Statistics:")
            print(f"  Full analyses: {api_engine.full_analyses}")
            print(f"  Lightweight updates: {api_engine.lightweight_updates}")
            print(f"  Total API calls: {api_engine.full_analyses + api_engine.lightweight_updates}")
        
        writer_stats = writer.get_stats()
        print(f"\nWebhook signals: {writer_stats['signals_sent']}")
        print("="*70)
        
        tracker.disconnect()


if __name__ == "__main__":
    main()