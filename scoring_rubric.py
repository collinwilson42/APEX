"""
SCORING RUBRIC v2.0 — Layer 2: Interpretive Prompt
====================================================
Seed 21: Three-Layer Scoring

Claude is NO LONGER the primary scorer. Instead:
  Layer 1 (technical_calculator.py) produces deterministic scores.
  Layer 2 (this prompt) asks Claude to INTERPRET the indicators + chart
  and provide an ADJUSTMENT score (-0.3 to +0.3) plus text rationale.

The adjustment accounts for things indicators can't see:
  - Pattern recognition (head & shoulders, flags, wedges)
  - Candle cluster context (engulfing at key level vs. random)
  - Visual anomalies (gaps, volume spikes, wicks)
  - Multi-timeframe visual context the numbers don't capture

Final score = (0.80 × Layer1) + (0.20 × Layer2_adjustment)
"""


def build_interpretive_prompt(symbol: str, timeframe: str,
                               indicator_snapshot: dict,
                               layer1_scores: dict) -> str:
    """
    Build the Layer 2 prompt: Claude sees indicators + screenshot,
    provides adjustment scores and text reasoning.

    Args:
        symbol: Trading symbol (e.g., "XAUJ26")
        timeframe: "15-minute" or "1-hour"
        indicator_snapshot: Raw indicator values from technical_calculator
        layer1_scores: The 4 deterministic scores from Layer 1
    """

    # Format indicator data for prompt
    snap = indicator_snapshot or {}
    l1 = layer1_scores or {}

    pa_score = l1.get('price_action', {}).get('score', 0)
    kl_score = l1.get('key_levels', {}).get('score', 0)
    mom_score = l1.get('momentum', {}).get('score', 0)
    str_score = l1.get('structure', {}).get('score', 0)

    pa_note = l1.get('price_action', {}).get('note', '')
    kl_note = l1.get('key_levels', {}).get('note', '')
    mom_note = l1.get('momentum', {}).get('note', '')
    str_note = l1.get('structure', {}).get('note', '')

    return f"""You are a professional futures trader reviewing a {timeframe} chart for {symbol}.

You are NOT scoring from scratch. A deterministic technical engine has already calculated base scores from the indicator data below. Your job is to INTERPRET what you see in the chart and provide SMALL ADJUSTMENTS where the visual context adds information the indicators miss.

═══════════════════════════════════════════════
CURRENT INDICATOR DATA (from intelligence database)
═══════════════════════════════════════════════

Price:         Last close={snap.get('last_close', 'N/A')}, open={snap.get('last_open', 'N/A')}
EMA:           Short={snap.get('ema_short', 'N/A'):.2f}, Medium={snap.get('ema_medium', 'N/A'):.2f}, Distance={snap.get('ema_distance', 'N/A'):+.3f}%
Trend:         Supertrend={snap.get('supertrend', 'N/A')}, SAR={snap.get('sar_trend', 'N/A')}
RSI(14):       {snap.get('rsi_14', 'N/A'):.1f}
MACD:          Line={snap.get('macd_line', 'N/A'):+.3f}, Signal={snap.get('macd_signal', 'N/A'):+.3f}, Histogram={snap.get('macd_histogram', 'N/A'):+.3f}
Bollinger:     %B={snap.get('bb_pct', 'N/A'):.3f}, Width={snap.get('bb_width', 'N/A'):.3f}
Stochastic:    K={snap.get('stoch_k', 'N/A'):.1f}, D={snap.get('stoch_d', 'N/A'):.1f}
ADX:           {snap.get('adx', 'N/A'):.0f}
CCI:           {snap.get('cci', 'N/A'):+.1f}
Williams %R:   {snap.get('williams_r', 'N/A'):.1f}
Ichimoku:      Tenkan={snap.get('ichimoku_tenkan', 'N/A'):.2f}, Kijun={snap.get('ichimoku_kijun', 'N/A'):.2f}
ATR(14):       {snap.get('atr_14', 'N/A'):.3f} (ratio={snap.get('atr_ratio', 'N/A'):.3f})
Volume Ratio:  {snap.get('volume_ratio', 'N/A'):.4f}
Fibonacci:     Zone={snap.get('fib_zone', 'N/A')}, Golden Zone={'YES' if snap.get('in_golden_zone') else 'NO'}

═══════════════════════════════════════════════
LAYER 1 DETERMINISTIC SCORES (already calculated)
═══════════════════════════════════════════════

  Price Action: {pa_score:+.4f}  — {pa_note}
  Key Levels:   {kl_score:+.4f}  — {kl_note}
  Momentum:     {mom_score:+.4f}  — {mom_note}
  Structure:    {str_score:+.4f}  — {str_note}

═══════════════════════════════════════════════
YOUR TASK: Provide adjustment scores + rationale
═══════════════════════════════════════════════

Look at the chart screenshot. For each category, decide if the VISUAL context changes anything the indicators miss:

  - Chart patterns (H&S, flags, wedges, triangles)
  - Candle formations at key levels (engulfing, hammers, shooting stars)
  - Visual support/resistance the Fib/BB numbers don't capture
  - Volume context visible on chart
  - Gaps, wicks, or anomalies

For each category, provide:
  1. An ADJUSTMENT from -0.3 to +0.3 (NOT a full score)
     - 0.0 means the indicators are capturing reality well
     - +0.2 means you see something bullish the numbers miss
     - -0.2 means you see something bearish the numbers miss
  2. A RATIONALE: one sentence explaining what you see that justifies the adjustment
  3. A CONFIDENCE: "high", "medium", or "low" — how sure are you the visual adds info?

CRITICAL RULES:
  1. Adjustments MUST be between -0.3 and +0.3. You are fine-tuning, not rescoring.
  2. If the chart confirms what the indicators say, use 0.0 (no adjustment needed).
  3. If the market is closed or the chart is static, adjustments should be near 0.0.
  4. Your rationale must cite specific visual evidence (candle pattern, level, formation).
  5. Do NOT re-derive what RSI or MACD "should" score. That's done. Focus on what you SEE.

Respond with ONLY valid JSON. No markdown. No backticks. No explanation outside JSON.

{{
    "price_action": {{
        "adjustment": 0.0,
        "rationale": "What visual evidence modifies the PA score?",
        "confidence": "medium"
    }},
    "key_levels": {{
        "adjustment": 0.0,
        "rationale": "What visual evidence modifies the KL score?",
        "confidence": "medium"
    }},
    "momentum": {{
        "adjustment": 0.0,
        "rationale": "What visual evidence modifies the MOM score?",
        "confidence": "medium"
    }},
    "structure": {{
        "adjustment": 0.0,
        "rationale": "What visual evidence modifies the STR score?",
        "confidence": "medium"
    }},
    "overall_assessment": {{
        "bias": "bullish|bearish|neutral",
        "rationale": "One sentence: your overall visual read combining all categories",
        "market_open": true
    }}
}}"""


def build_scoring_prompt(symbol: str, timeframe: str) -> str:
    """
    BACKWARD COMPATIBLE: If called without indicator data,
    falls back to the original pure-vision prompt (Layer 1 disabled).

    This ensures torra_trader.py works even before the full three-layer
    integration is complete.
    """
    return _build_legacy_prompt(symbol, timeframe)


def _build_legacy_prompt(symbol: str, timeframe: str) -> str:
    """Original pure-vision prompt — kept as fallback only."""
    return f"""You are a professional futures trader scoring a {timeframe} chart for {symbol}.

Analyze the chart image and score EXACTLY 4 categories. Each score is a float from -1.0 (extremely bearish) to +1.0 (extremely bullish).

Your scores will be fed into a weighted algorithm that places real trades. Be precise. Be calibrated. Do not default to neutral — commit to what the chart is showing you.

CATEGORY 1: PRICE ACTION — What is price doing RIGHT NOW?
  +0.8 to +1.0: Strong bullish engulfing / breakout above resistance
  +0.4 to +0.7: Higher lows forming / bullish candles dominating
  -0.1 to +0.1: Doji / indecision / no clear direction
  -0.7 to -0.4: Lower highs forming / bearish candles dominating
  -1.0 to -0.8: Strong bearish engulfing / breakdown below support

CATEGORY 2: KEY LEVELS — Where is price relative to structure?
  +0.8 to +1.0: Bouncing off major support / holding above breakout level
  -0.1 to +0.1: Trapped mid-range / equidistant from support and resistance
  -1.0 to -0.8: Rejected from major resistance / free-falling through levels

CATEGORY 3: MOMENTUM — Is the move accelerating or fading?
  +0.8 to +1.0: Accelerating bullish / candles growing / RSI rising toward 70+
  -0.1 to +0.1: Flat / exhaustion / tiny candles / indicators flat-lined
  -1.0 to -0.8: Accelerating bearish / candles growing down / RSI falling toward 30-

CATEGORY 4: STRUCTURE — What regime or pattern is forming?
  +0.8 to +1.0: Clear uptrend / HH+HL / bull flag / ascending triangle
  -0.1 to +0.1: Range-bound / no clear structure / choppy
  -1.0 to -0.8: Clear downtrend / LH+LL / bear flag / descending triangle

NOTE: ATH (All Time High) is calculated automatically by the system.

Respond with ONLY valid JSON:
{{
    "price_action": {{"score": 0.0, "note": "one sentence"}},
    "key_levels": {{"score": 0.0, "note": "one sentence"}},
    "momentum": {{"score": 0.0, "note": "one sentence"}},
    "structure": {{"score": 0.0, "note": "one sentence"}},
    "composite_bias": {{"score": 0.0, "note": "overall read"}}
}}

RULES:
1. Scores MUST be between -1.0 and +1.0
2. Do NOT default to 0.0 — take a position
3. If market is closed and chart is static, be specific about that
4. Be specific in notes — mention visible patterns, levels, candle shapes"""
