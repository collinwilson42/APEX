"""
TECHNICAL CALCULATOR — Layer 1: Deterministic Scoring Engine
=============================================================
Seed 21: Three-Layer Scoring

Reads pre-computed indicators from the intelligence DB and produces
DETERMINISTIC scores for 4 sentiment vectors:
  - Price Action (PA):  candle patterns + EMA position
  - Key Levels (KL):    Bollinger + Fibonacci + SAR + Ichimoku cloud
  - Momentum (MOM):     RSI + MACD + Stochastic + CCI + ADX
  - Structure (STR):    trend regime + Ichimoku TK + EMA alignment

Same data → same score. Always. No LLM involved.

Usage:
    from technical_calculator import calculate_technical_scores
    result = calculate_technical_scores("XAUJ26")
"""

import os
import sys
import math
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import SYMBOL_DATABASES

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# NORMALIZATION UTILITIES
# ═══════════════════════════════════════════════════════════════════════════

def _tanh(x: float, scale: float = 1.0) -> float:
    """Smooth normalization to [-1, +1]. Scale controls sensitivity."""
    return math.tanh(x * scale)


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _safe(val, default=0.0) -> float:
    """Safely convert DB value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADER
# ═══════════════════════════════════════════════════════════════════════════

def _load_latest(db_path: str, n_candles: int = 5) -> Optional[Dict]:
    """
    Load the latest N candles + indicators from the intelligence DB.
    Returns dict with 'candles', 'indicators', 'basic', 'fib', 'ath' keys.
    """
    if not os.path.exists(db_path):
        logger.warning(f"Intelligence DB not found: {db_path}")
        return None

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.execute(
            "SELECT * FROM core_15m ORDER BY timestamp DESC LIMIT ?",
            (n_candles,)
        )
        candles = [dict(r) for r in cur.fetchall()]

        cur = conn.execute(
            "SELECT * FROM advanced_indicators ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        indicators = dict(row) if row else {}

        cur = conn.execute(
            "SELECT * FROM basic_15m ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        basic = dict(row) if row else {}

        cur = conn.execute(
            "SELECT * FROM fibonacci_data ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        fib = dict(row) if row else {}

        cur = conn.execute(
            "SELECT * FROM ath_tracking ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        ath = dict(row) if row else {}

        if not candles or not indicators:
            logger.warning("Intelligence DB has no data")
            return None

        latest_ts = candles[0].get('timestamp', '')
        try:
            dt = datetime.fromisoformat(latest_ts.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds()
        except (ValueError, TypeError):
            age = 9999

        return {
            'candles': candles,
            'indicators': indicators,
            'basic': basic,
            'fib': fib,
            'ath': ath,
            'timestamp': latest_ts,
            'freshness_seconds': age,
        }

    except Exception as e:
        logger.error(f"Failed to load intelligence data: {e}")
        return None
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 SCORE: PRICE ACTION
# ═══════════════════════════════════════════════════════════════════════════

def _score_price_action(candles: list, basic: dict) -> Dict:
    """
    Deterministic Price Action score from candle data + EMA position.
    Components: candle direction, body dominance, EMA position, supertrend.
    """
    components = {}

    # 1. Candle direction: count bullish/bearish in last 3
    directions = []
    for c in candles[:3]:
        o, cl = _safe(c.get('open')), _safe(c.get('close'))
        if cl > o:
            directions.append(1)
        elif cl < o:
            directions.append(-1)
        else:
            directions.append(0)

    bullish_count = sum(1 for d in directions if d > 0)
    bearish_count = sum(1 for d in directions if d < 0)
    candle_score = (bullish_count - bearish_count) / max(len(directions), 1)
    components['candle_direction'] = round(candle_score, 3)

    # 2. Body dominance: avg body % of total range
    body_pcts = []
    for c in candles[:3]:
        o, h, l, cl = _safe(c.get('open')), _safe(c.get('high')), _safe(c.get('low')), _safe(c.get('close'))
        total_range = h - l
        if total_range > 0:
            body_pct = abs(cl - o) / total_range
            body_pcts.append(body_pct)

    avg_body = sum(body_pcts) / max(len(body_pcts), 1) if body_pcts else 0.5
    body_conviction = _tanh((avg_body - 0.4) * 3.0)
    body_with_direction = body_conviction * candle_score
    components['body_conviction'] = round(body_with_direction, 3)

    # 3. EMA position
    ema_dist = _safe(basic.get('ema_distance'))
    ema_score = _tanh(ema_dist, 8.0)
    components['ema_position'] = round(ema_score, 3)

    # 4. Supertrend
    st = basic.get('supertrend', '').upper()
    st_score = 0.3 if st == 'UP' else (-0.3 if st == 'DOWN' else 0.0)
    components['supertrend'] = round(st_score, 3)

    # Weighted blend
    score = (
        candle_score * 0.30 +
        body_with_direction * 0.25 +
        ema_score * 0.25 +
        st_score * 0.20
    )
    score = _clamp(score)

    direction_word = "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "neutral")
    note = (f"{direction_word.capitalize()} PA: {bullish_count}/3 green candles, "
            f"body conviction {avg_body:.0%}, "
            f"EMA dist {ema_dist:+.3f}%, "
            f"supertrend {st or 'N/A'}")

    return {'score': round(score, 4), 'components': components, 'note': note}


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 SCORE: KEY LEVELS
# ═══════════════════════════════════════════════════════════════════════════

def _score_key_levels(indicators: dict, basic: dict, fib: dict) -> Dict:
    """
    Deterministic Key Levels score from structural position indicators.
    Components: Bollinger %B, Fibonacci zone, SAR, Ichimoku cloud.
    """
    components = {}

    # 1. Bollinger %B
    bb_pct = _safe(indicators.get('bb_pct_20'), 0.5)
    bb_score = _tanh((0.5 - bb_pct) * 2.0)
    components['bollinger_pct'] = round(bb_score, 3)

    # 2. Fibonacci zone
    in_golden = int(_safe(fib.get('in_golden_zone'), 0))
    fib_zone = fib.get('current_fib_zone', '5')
    try:
        fib_zone_num = int(fib_zone)
    except (ValueError, TypeError):
        fib_zone_num = 5
    fib_score = _tanh((5 - fib_zone_num) * 0.15)
    if in_golden:
        fib_score *= 1.3
    fib_score = _clamp(fib_score)
    components['fib_zone'] = round(fib_score, 3)

    # 3. SAR trend
    sar_trend = indicators.get('sar_trend', '').upper()
    sar_score = 0.25 if sar_trend == 'UP' else (-0.25 if sar_trend == 'DOWN' else 0.0)
    components['sar'] = round(sar_score, 3)

    # 4. Ichimoku cloud position
    senkou_a = _safe(indicators.get('ichimoku_senkou_a'))
    senkou_b = _safe(indicators.get('ichimoku_senkou_b'))
    cloud_top = max(senkou_a, senkou_b) if senkou_a and senkou_b else 0
    cloud_bottom = min(senkou_a, senkou_b) if senkou_a and senkou_b else 0
    price = _safe(basic.get('ema_short'))
    if price and cloud_top and cloud_bottom:
        if price > cloud_top:
            ichi_score = 0.3
        elif price < cloud_bottom:
            ichi_score = -0.3
        else:
            ichi_score = 0.0
    else:
        ichi_score = 0.0
    components['ichimoku_cloud'] = round(ichi_score, 3)

    score = (
        bb_score * 0.30 +
        fib_score * 0.25 +
        sar_score * 0.20 +
        ichi_score * 0.25
    )
    score = _clamp(score)

    note = (f"BB%B={bb_pct:.2f}, fib zone {fib_zone_num}"
            f"{'(golden)' if in_golden else ''}, "
            f"SAR {sar_trend or 'N/A'}, "
            f"{'above' if ichi_score > 0 else 'below' if ichi_score < 0 else 'in'} Ichimoku cloud")

    return {'score': round(score, 4), 'components': components, 'note': note}


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 SCORE: MOMENTUM
# ═══════════════════════════════════════════════════════════════════════════

def _score_momentum(indicators: dict, basic: dict) -> Dict:
    """
    Deterministic Momentum score from oscillator indicators.
    Components: RSI, MACD histogram, Stochastic cross, CCI, ADX direction.
    """
    components = {}

    # 1. RSI(14)
    rsi = _safe(indicators.get('rsi_14'), 50)
    rsi_trend = (rsi - 50) / 50
    if rsi > 70:
        rsi_score = rsi_trend * 0.7
    elif rsi < 30:
        rsi_score = rsi_trend * 0.7
    else:
        rsi_score = rsi_trend
    rsi_score = _clamp(rsi_score)
    components['rsi_14'] = round(rsi_score, 3)

    # 2. MACD histogram normalized by ATR
    macd_hist = _safe(indicators.get('macd_histogram_12_26'))
    atr = _safe(basic.get('atr_14'), 1.0) or 1.0
    macd_normalized = macd_hist / atr
    macd_score = _tanh(macd_normalized, 3.0)
    components['macd_histogram'] = round(macd_score, 3)

    # 3. Stochastic K vs D
    stoch_k = _safe(indicators.get('stoch_k_14'), 50)
    stoch_d = _safe(indicators.get('stoch_d_14'), 50)
    stoch_diff = (stoch_k - stoch_d)
    stoch_score = _tanh(stoch_diff * 0.04)
    components['stochastic_cross'] = round(stoch_score, 3)

    # 4. CCI(14)
    cci = _safe(indicators.get('cci_14'))
    cci_score = _tanh(cci / 150)
    components['cci_14'] = round(cci_score, 3)

    # 5. ADX directional
    adx = _safe(indicators.get('adx_14'), 20)
    trend_strength = min(adx / 40, 1.0)
    direction = 1.0 if macd_hist > 0 else (-1.0 if macd_hist < 0 else 0.0)
    adx_score = direction * trend_strength * 0.5
    components['adx_direction'] = round(adx_score, 3)

    score = (
        rsi_score * 0.25 +
        macd_score * 0.30 +
        stoch_score * 0.15 +
        cci_score * 0.15 +
        adx_score * 0.15
    )
    score = _clamp(score)

    direction_word = "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "flat")
    note = (f"{direction_word.capitalize()} momentum: "
            f"RSI={rsi:.1f}, MACD hist={macd_hist:+.3f}, "
            f"Stoch K/D={stoch_k:.0f}/{stoch_d:.0f}, "
            f"CCI={cci:+.0f}, ADX={adx:.0f}")

    return {'score': round(score, 4), 'components': components, 'note': note}


# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 SCORE: STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════

def _score_structure(indicators: dict, basic: dict, candles: list) -> Dict:
    """
    Deterministic Structure score from regime/trend indicators.
    Components: ADX regime, Ichimoku TK cross, EMA alignment, price progression.
    """
    components = {}

    # 1. ADX regime
    adx = _safe(indicators.get('adx_14'), 20)
    macd_hist = _safe(indicators.get('macd_histogram_12_26'))
    if adx < 20:
        adx_regime = 0.0
    else:
        direction = 1.0 if macd_hist > 0 else -1.0
        strength = _tanh((adx - 20) * 0.08)
        adx_regime = direction * strength
    components['adx_regime'] = round(adx_regime, 3)

    # 2. Ichimoku TK cross
    tenkan = _safe(indicators.get('ichimoku_tenkan'))
    kijun = _safe(indicators.get('ichimoku_kijun'))
    if tenkan and kijun and kijun != 0:
        tk_diff = (tenkan - kijun) / kijun * 100
        tk_score = _tanh(tk_diff, 2.0)
    else:
        tk_score = 0.0
    components['ichimoku_tk'] = round(tk_score, 3)

    # 3. EMA alignment
    ema_short = _safe(basic.get('ema_short'))
    ema_medium = _safe(basic.get('ema_medium'))
    if ema_short and ema_medium and ema_medium != 0:
        ema_alignment = (ema_short - ema_medium) / ema_medium * 100
        ema_score = _tanh(ema_alignment, 3.0)
    else:
        ema_score = 0.0
    components['ema_alignment'] = round(ema_score, 3)

    # 4. Price progression (HH/HL or LH/LL)
    if len(candles) >= 4:
        highs = [_safe(c.get('high')) for c in candles[:4]][::-1]
        lows = [_safe(c.get('low')) for c in candles[:4]][::-1]
        higher_highs = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
        higher_lows = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i-1])
        lower_highs = sum(1 for i in range(1, len(highs)) if highs[i] < highs[i-1])
        lower_lows = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
        bull_structure = (higher_highs + higher_lows) / 6
        bear_structure = (lower_highs + lower_lows) / 6
        progression_score = _clamp(bull_structure - bear_structure)
    else:
        progression_score = 0.0
    components['price_progression'] = round(progression_score, 3)

    score = (
        adx_regime * 0.30 +
        tk_score * 0.25 +
        ema_score * 0.25 +
        progression_score * 0.20
    )
    score = _clamp(score)

    regime = ("trending up" if score > 0.2 else
              "trending down" if score < -0.2 else
              "range-bound/choppy")
    note = (f"Structure: {regime}, ADX={adx:.0f}, "
            f"TK {'bullish' if tk_score > 0 else 'bearish' if tk_score < 0 else 'flat'}, "
            f"EMA {'aligned up' if ema_score > 0 else 'aligned down' if ema_score < 0 else 'flat'}")

    return {'score': round(score, 4), 'components': components, 'note': note}


# ═══════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def calculate_technical_scores(symbol: str) -> Optional[Dict]:
    """
    Calculate deterministic technical scores for all 4 vectors.
    Returns dict with price_action, key_levels, momentum, structure,
    plus timestamp, freshness, stale flag, and indicator_snapshot for Layer 2.
    """
    symbol_upper = symbol.upper().replace('.SIM', '')
    sym_config = SYMBOL_DATABASES.get(symbol_upper, {})
    db_path = sym_config.get('db_path')

    if not db_path:
        logger.error(f"No intelligence DB configured for symbol: {symbol_upper}")
        return None

    data = _load_latest(db_path, n_candles=5)
    if not data:
        return None

    candles = data['candles']
    indicators = data['indicators']
    basic = data['basic']
    fib = data['fib']

    pa = _score_price_action(candles, basic)
    kl = _score_key_levels(indicators, basic, fib)
    mom = _score_momentum(indicators, basic)
    stru = _score_structure(indicators, basic, candles)

    freshness = data['freshness_seconds']
    stale = freshness > 1800

    result = {
        'price_action': pa,
        'key_levels': kl,
        'momentum': mom,
        'structure': stru,
        'timestamp': data['timestamp'],
        'freshness_seconds': round(freshness, 0),
        'stale': stale,
        'summary': (
            f"L1 Deterministic: PA={pa['score']:+.3f} KL={kl['score']:+.3f} "
            f"MOM={mom['score']:+.3f} STR={stru['score']:+.3f} "
            f"({'STALE' if stale else f'{freshness:.0f}s ago'})"
        ),
        'indicator_snapshot': {
            'rsi_14': _safe(indicators.get('rsi_14')),
            'macd_histogram': _safe(indicators.get('macd_histogram_12_26')),
            'macd_line': _safe(indicators.get('macd_line_12_26')),
            'macd_signal': _safe(indicators.get('macd_signal_12_26')),
            'bb_pct': _safe(indicators.get('bb_pct_20')),
            'bb_width': _safe(indicators.get('bb_width_20')),
            'stoch_k': _safe(indicators.get('stoch_k_14')),
            'stoch_d': _safe(indicators.get('stoch_d_14')),
            'adx': _safe(indicators.get('adx_14')),
            'cci': _safe(indicators.get('cci_14')),
            'williams_r': _safe(indicators.get('williams_r_14')),
            'sar_trend': indicators.get('sar_trend', ''),
            'ichimoku_tenkan': _safe(indicators.get('ichimoku_tenkan')),
            'ichimoku_kijun': _safe(indicators.get('ichimoku_kijun')),
            'ema_short': _safe(basic.get('ema_short')),
            'ema_medium': _safe(basic.get('ema_medium')),
            'ema_distance': _safe(basic.get('ema_distance')),
            'supertrend': basic.get('supertrend', ''),
            'atr_14': _safe(basic.get('atr_14')),
            'atr_ratio': _safe(basic.get('atr_ratio')),
            'volume_ratio': _safe(indicators.get('volume_ratio')),
            'fib_zone': fib.get('current_fib_zone', ''),
            'in_golden_zone': int(_safe(fib.get('in_golden_zone'), 0)),
            'last_close': _safe(candles[0].get('close')) if candles else 0,
            'last_open': _safe(candles[0].get('open')) if candles else 0,
            'last_high': _safe(candles[0].get('high')) if candles else 0,
            'last_low': _safe(candles[0].get('low')) if candles else 0,
        },
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════
# CLI TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json

    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUJ26"
    result = calculate_technical_scores(symbol)

    if result:
        print(f"\n{'=' * 60}")
        print(f"  LAYER 1 — TECHNICAL SCORES: {symbol}")
        print(f"  Data: {result['timestamp']} ({result['freshness_seconds']:.0f}s ago)")
        if result['stale']:
            print(f"  WARNING: DATA IS STALE (>1800s)")
        print(f"{'=' * 60}")

        for vec in ['price_action', 'key_levels', 'momentum', 'structure']:
            v = result[vec]
            emoji = '+' if v['score'] > 0.15 else ('-' if v['score'] < -0.15 else '~')
            print(f"\n  [{emoji}] {vec.upper()}: {v['score']:+.4f}")
            print(f"     {v['note']}")
            for comp_key, comp_val in v['components'].items():
                print(f"       {comp_key}: {comp_val:+.3f}")

        print(f"\n  {result['summary']}")
        print(f"{'=' * 60}")
    else:
        print(f"Failed to calculate scores for {symbol}")
